"""Deterministic synthetic scenarios for privacy/graph integration tests."""

from __future__ import annotations

from typing import Any

from fraudmesh.privacy import create_shared_signal


DEMO_SECRET = "demo-only-secret-not-for-production"


def three_bank_fraud_ring() -> list[dict[str, Any]]:
    """Return a synthetic three-bank mule loop using allowed shared signals.

    Each institution observes one leg of the cycle, so no bank independently
    has the complete ring.  The collaborative graph sees all three permitted
    relationship signals in the same coarse hour.
    """
    transfers = [
        ("bank_a", "A-101", "MULE-201", "2026-10-17T10:05:00Z", 18_500, 0.42),
        ("bank_b", "MULE-201", "MULE-301", "2026-10-17T10:19:00Z", 18_200, 0.48),
        ("bank_c", "MULE-301", "A-101", "2026-10-17T10:42:00Z", 17_900, 0.45),
    ]
    return [
        create_shared_signal(
            signal_id=f"ring-{index}",
            institution_id=bank,
            source_entity_id=source,
            destination_entity_id=destination,
            timestamp=timestamp,
            amount=amount,
            local_risk_score=risk,
            secret=DEMO_SECRET,
            channel="transfer",
        )
        for index, (bank, source, destination, timestamp, amount, risk) in enumerate(transfers, 1)
    ]

