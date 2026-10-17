"""Privacy-boundary helpers for the FraudMesh prototype.

The collaborative service receives deterministic HMAC tokens and coarse
features only.  This is pseudonymization, not anonymization: a stable token
can still reveal relationships, and anyone with the secret and source ID can
recreate a token.  Production key custody, access control, rotation, and
participant agreements are outside this prototype.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import math
import re
from typing import Any, Iterable, Mapping


TOKEN_VERSION = "fm1"
INSTITUTIONS = frozenset({"bank_a", "bank_b", "bank_c"})
AMOUNT_BUCKETS = frozenset({"lt_1k", "1k_10k", "10k_50k", "gte_50k"})
CHANNELS = frozenset({"transfer", "online", "card", "wire", "mobile", "atm"})
SHARED_SIGNAL_FIELDS = frozenset(
    {
        "signal_id",
        "institution_id",
        "source_entity_token",
        "destination_entity_token",
        "timestamp_bucket",
        "amount_bucket",
        "local_risk_score",
        "channel",
    }
)
RAW_OR_DISALLOWED_FIELDS = frozenset(
    {
        "transaction_id",
        "customer_id",
        "account_id",
        "source_entity_id",
        "destination_entity_id",
        "source_account_id",
        "destination_account_id",
        "amount",
        "timestamp",
        "label",
        "fraud_label",
    }
)


class PrivacyContractError(ValueError):
    """Raised when a signal does not meet the collaborative allowlist."""


def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def pseudonymize_identifier(identifier: str, secret: str | bytes) -> str:
    """Return a deterministic, versioned HMAC token for a synthetic ID.

    The same normalized identifier and shared secret produce the same token
    across banks.  A real deployment would source ``secret`` from a managed
    key service; callers must never log, commit, or send it to the analysis
    service.
    """
    if not isinstance(identifier, str) or not identifier.strip():
        raise PrivacyContractError("identifier must be a non-empty string")
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not isinstance(secret, bytes) or not secret:
        raise PrivacyContractError("secret must be a non-empty string or bytes")

    normalized = identifier.strip().casefold().encode("utf-8")
    digest = hmac.new(secret, normalized, hashlib.sha256).hexdigest()
    return f"{TOKEN_VERSION}:{digest}"


def coarse_timestamp_bucket(value: datetime | str) -> str:
    """Reduce a timestamp to an ISO UTC hour bucket for velocity analysis."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise PrivacyContractError("timestamp must be ISO-8601") from exc
    if not isinstance(value, datetime):
        raise PrivacyContractError("timestamp must be a datetime or ISO-8601 string")
    if value.utcoffset() is None:
        raise PrivacyContractError("timestamp must include a timezone")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00Z")


def coarse_amount_bucket(amount: float | int) -> str:
    """Return a non-exact amount band; exact transaction values stay local."""
    if not _finite_number(amount) or amount < 0:
        raise PrivacyContractError("amount must be a finite non-negative number")
    if amount < 1_000:
        return "lt_1k"
    if amount < 10_000:
        return "1k_10k"
    if amount < 50_000:
        return "10k_50k"
    return "gte_50k"


@dataclass(frozen=True)
class SharedSignal:
    """The only transaction-derived record allowed into collaborative analysis."""

    signal_id: str
    institution_id: str
    source_entity_token: str
    destination_entity_token: str
    timestamp_bucket: str
    amount_bucket: str
    local_risk_score: float
    channel: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "institution_id": self.institution_id,
            "source_entity_token": self.source_entity_token,
            "destination_entity_token": self.destination_entity_token,
            "timestamp_bucket": self.timestamp_bucket,
            "amount_bucket": self.amount_bucket,
            "local_risk_score": self.local_risk_score,
            "channel": self.channel,
        }


def create_shared_signal(
    *,
    signal_id: str,
    institution_id: str,
    source_entity_id: str,
    destination_entity_id: str,
    timestamp: datetime | str,
    amount: float | int,
    local_risk_score: float,
    secret: str | bytes,
    channel: str | None = None,
) -> dict[str, Any]:
    """Transform a local synthetic transaction into an allowlisted signal."""
    signal = SharedSignal(
        signal_id=signal_id,
        institution_id=institution_id,
        source_entity_token=pseudonymize_identifier(source_entity_id, secret),
        destination_entity_token=pseudonymize_identifier(destination_entity_id, secret),
        timestamp_bucket=coarse_timestamp_bucket(timestamp),
        amount_bucket=coarse_amount_bucket(amount),
        local_risk_score=local_risk_score,
        channel=channel,
    ).as_dict()
    validate_shared_signal(signal)
    return signal


def validate_shared_signal(signal: Mapping[str, Any]) -> None:
    """Enforce the field allowlist before graph construction.

    The validator intentionally rejects undeclared fields rather than silently
    dropping them, making accidental raw-data expansion visible in tests and
    integration logs.
    """
    if not isinstance(signal, Mapping):
        raise PrivacyContractError("each signal must be an object")
    fields = set(signal)
    disallowed = fields & RAW_OR_DISALLOWED_FIELDS
    if disallowed:
        raise PrivacyContractError("disallowed raw fields")
    unexpected = fields - SHARED_SIGNAL_FIELDS
    if unexpected:
        raise PrivacyContractError("fields outside shared schema")
    missing = SHARED_SIGNAL_FIELDS - fields
    if missing:
        raise PrivacyContractError(f"required shared fields missing: {sorted(missing)}")
    if not isinstance(signal["signal_id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", signal["signal_id"]):
        raise PrivacyContractError("signal_id must be a bounded opaque reference")
    if not isinstance(signal["institution_id"], str) or signal["institution_id"] not in INSTITUTIONS:
        raise PrivacyContractError("institution_id must identify an agreed simulated bank")
    for field in ("source_entity_token", "destination_entity_token"):
        if not isinstance(signal[field], str) or not re.fullmatch(r"fm1:[0-9a-f]{64}", signal[field]):
            raise PrivacyContractError(f"{field} must use canonical HMAC token syntax")
    bucket = signal["timestamp_bucket"]
    try:
        if not isinstance(bucket, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:00Z", bucket):
            raise ValueError
        datetime.strptime(bucket, "%Y-%m-%dT%H:00Z")
    except ValueError as exc:
        raise PrivacyContractError("timestamp_bucket must be a valid UTC hour bucket") from exc
    if not isinstance(signal["amount_bucket"], str) or signal["amount_bucket"] not in AMOUNT_BUCKETS:
        raise PrivacyContractError("amount_bucket must use an agreed coarse category")
    if signal["channel"] is not None and (not isinstance(signal["channel"], str) or signal["channel"] not in CHANNELS):
        raise PrivacyContractError("channel must be an agreed category or null")
    score = signal["local_risk_score"]
    if not _finite_number(score) or not 0.0 <= score <= 1.0:
        raise PrivacyContractError("local_risk_score must be in [0, 1]")


def validate_shared_signals(signals: Iterable[Mapping[str, Any]]) -> None:
    """Validate all signals without retaining local records."""
    if not isinstance(signals, list):
        raise PrivacyContractError("shared_signals must be a list")
    seen_signal_ids: set[str] = set()
    for signal in signals:
        validate_shared_signal(signal)
        signal_id = signal["signal_id"]
        if signal_id in seen_signal_ids:
            raise PrivacyContractError(f"duplicate signal_id: {signal_id}")
        seen_signal_ids.add(signal_id)

