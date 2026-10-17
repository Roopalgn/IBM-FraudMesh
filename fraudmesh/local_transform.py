"""Bank-local transformation from synthetic ledger rows to shared signals.

This module belongs on the bank side of the prototype boundary. The central
graph service receives only its output, never these local ledger rows or the
linkage secret.
"""

from __future__ import annotations

from typing import Any

from fraudmesh.privacy import PrivacyContractError, create_shared_signal


LOCAL_REQUIRED_FIELDS = frozenset(
    {
        "signal_ref",
        "institution_id",
        "source_entity_id",
        "destination_entity_id",
        "timestamp",
        "amount",
        "risk_score",
        "channel",
    }
)


def transform_bank_local_ledger(
    local_rows: list[dict[str, Any]], *, linkage_secret: str | bytes
) -> list[dict[str, Any]]:
    """Create permitted signals from local synthetic rows and ML risk scores.

    ``risk_score`` is the ML component's local score. Labels and scenario
    ground-truth fields may remain in the local fixture for evaluation, but are
    deliberately never copied into the returned collaborative signal.
    """
    if not isinstance(local_rows, (list, tuple)) or not local_rows:
        raise PrivacyContractError("local ledger must be a non-empty list or tuple")

    signals: list[dict[str, Any]] = []
    for row in local_rows:
        if not isinstance(row, dict):
            raise PrivacyContractError("local ledger row must be an object")
        if LOCAL_REQUIRED_FIELDS - set(row):
            raise PrivacyContractError("local ledger row is missing transformation fields")
        signals.append(
            create_shared_signal(
                signal_id=row["signal_ref"],
                institution_id=row["institution_id"],
                source_entity_id=row["source_entity_id"],
                destination_entity_id=row["destination_entity_id"],
                timestamp=row["timestamp"],
                amount=row["amount"],
                local_risk_score=row["risk_score"],
                secret=linkage_secret,
                channel=row["channel"],
            )
        )
    return signals
