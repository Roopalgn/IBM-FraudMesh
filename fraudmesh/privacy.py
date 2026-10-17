"""Restricted shared-signal contract for the FraudMesh prototype.

Banks transform their synthetic local records before the collaborative graph
service sees them. The service validates schema and representation; it cannot
prove a token was created by an authorized bank or establish how a participant
handled data before submission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import math
import re
from typing import Any


TOKEN_VERSION = "fm1"
SHARED_SCHEMA_VERSION = "fraudmesh-shared-signal/v1"
ALLOWED_INSTITUTIONS = frozenset({"bank_a", "bank_b", "bank_c"})
ALLOWED_AMOUNT_BUCKETS = frozenset({"lt_1k", "1k_10k", "10k_50k", "gte_50k"})
ALLOWED_CHANNELS = frozenset({"transfer", "online", "card", "ach", "wire", "upi", "mobile", "atm"})
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
        "scenario_ground_truth",
    }
)
SIGNAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
TOKEN_PATTERN = re.compile(r"^fm1:[0-9a-f]{64}$")
TIMESTAMP_BUCKET_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:00Z$")


class PrivacyContractError(ValueError):
    """Raised when data fails the restricted collaborative-signal contract."""


def _is_finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def pseudonymize_identifier(identifier: str, secret: str | bytes) -> str:
    """Return a deterministic, versioned HMAC token for a synthetic entity ID.

    Call this only at the bank-local transformation boundary. The shared secret
    remains outside collaborative requests. Deterministic tokens are linkable
    pseudonyms, not anonymous identifiers or authenticated assertions.
    """
    if not isinstance(identifier, str) or not identifier.strip():
        raise PrivacyContractError("entity identifier must be a non-empty string")
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not isinstance(secret, bytes) or not secret:
        raise PrivacyContractError("linkage secret must be a non-empty string or bytes")

    normalized = identifier.strip().casefold().encode("utf-8")
    digest = hmac.new(secret, normalized, hashlib.sha256).hexdigest()
    return f"{TOKEN_VERSION}:{digest}"


def coarse_timestamp_bucket(value: datetime | str) -> str:
    """Reduce a local timestamp to one canonical UTC hour bucket."""
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


def parse_timestamp_bucket(value: str) -> datetime:
    """Validate and parse the canonical UTC hour representation."""
    if not isinstance(value, str) or not TIMESTAMP_BUCKET_PATTERN.fullmatch(value):
        raise PrivacyContractError("timestamp_bucket must be a canonical UTC hour bucket")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:00Z").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PrivacyContractError("timestamp_bucket must be a valid UTC hour") from exc


def coarse_amount_bucket(amount: float | int) -> str:
    """Return a non-exact amount band; exact transaction values stay local."""
    if not _is_finite_number(amount):
        raise PrivacyContractError("amount must be a finite number")
    if amount < 0:
        raise PrivacyContractError("amount must not be negative")
    if amount < 1_000:
        return "lt_1k"
    if amount < 10_000:
        return "1k_10k"
    if amount < 50_000:
        return "10k_50k"
    return "gte_50k"


@dataclass(frozen=True)
class SharedSignal:
    """The only transaction-derived record accepted by collaborative analysis."""

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
    """Transform one bank-local synthetic transaction into a restricted signal."""
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


def validate_shared_signal(signal: Any) -> None:
    """Require exactly one valid, scalar-only shared-signal record.

    Validation enforces allowed representations, not provenance. A token with
    valid HMAC syntax may still be fabricated by an unauthorized sender.
    """
    if not isinstance(signal, dict):
        raise PrivacyContractError("shared signal must be a JSON object")

    fields = set(signal)
    if fields & RAW_OR_DISALLOWED_FIELDS:
        raise PrivacyContractError("shared signal contains prohibited raw-data fields")
    if fields - SHARED_SIGNAL_FIELDS:
        raise PrivacyContractError("shared signal contains fields outside the approved schema")
    if SHARED_SIGNAL_FIELDS - fields:
        raise PrivacyContractError("shared signal is missing required approved fields")

    signal_id = signal["signal_id"]
    if not isinstance(signal_id, str) or not SIGNAL_ID_PATTERN.fullmatch(signal_id):
        raise PrivacyContractError("signal_id must be a bounded opaque reference")

    institution_id = signal["institution_id"]
    if not isinstance(institution_id, str) or institution_id not in ALLOWED_INSTITUTIONS:
        raise PrivacyContractError("institution_id is not in the simulated-bank allowlist")

    for token_field in ("source_entity_token", "destination_entity_token"):
        token = signal[token_field]
        if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
            raise PrivacyContractError(f"{token_field} must be a canonical versioned HMAC token")

    parse_timestamp_bucket(signal["timestamp_bucket"])

    amount_bucket = signal["amount_bucket"]
    if not isinstance(amount_bucket, str) or amount_bucket not in ALLOWED_AMOUNT_BUCKETS:
        raise PrivacyContractError("amount_bucket must be one of the approved coarse categories")

    score = signal["local_risk_score"]
    if not _is_finite_number(score) or not 0.0 <= float(score) <= 1.0:
        raise PrivacyContractError("local_risk_score must be a finite number in [0, 1]")

    channel = signal["channel"]
    if channel is not None and (
        not isinstance(channel, str) or channel not in ALLOWED_CHANNELS
    ):
        raise PrivacyContractError("channel must be null or an approved coarse channel")


def validate_shared_signals(signals: Any) -> None:
    """Validate a non-empty batch before any graph construction occurs."""
    if not isinstance(signals, (list, tuple)):
        raise PrivacyContractError("shared_signals must be a list or tuple of signal objects")
    if not signals:
        raise PrivacyContractError("shared_signals must not be empty")

    seen_signal_ids: set[str] = set()
    for signal in signals:
        validate_shared_signal(signal)
        signal_id = signal["signal_id"]
        if signal_id in seen_signal_ids:
            raise PrivacyContractError("shared signal IDs must be unique within a batch")
        seen_signal_ids.add(signal_id)
