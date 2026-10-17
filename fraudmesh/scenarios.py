"""Deterministic synthetic scenarios for privacy/graph integration tests."""

from __future__ import annotations

from typing import Any

from fraudmesh.local_transform import transform_bank_local_ledger


DEMO_SECRET = "demo-only-secret-not-for-production"


def three_bank_demo_ledger() -> list[dict[str, Any]]:
    """Return local-only fixture rows for the deterministic three-bank demo.

    The fixture's ``risk_score`` values represent Person 2's ML output shape.
    ``label`` and ``scenario_ground_truth`` remain local evaluation metadata.
    """
    return [
        {
            "signal_ref": "demo-a-001",
            "institution_id": "bank_a",
            "source_entity_id": "A-101",
            "destination_entity_id": "MULE-201",
            "timestamp": "2026-10-17T10:05:00Z",
            "amount": 18_500,
            "risk_score": 0.42,
            "channel": "transfer",
            "label": 1,
            "scenario_ground_truth": "split_cross_bank_cycle",
        },
        {
            "signal_ref": "demo-b-001",
            "institution_id": "bank_b",
            "source_entity_id": "MULE-201",
            "destination_entity_id": "MULE-301",
            "timestamp": "2026-10-17T10:19:00Z",
            "amount": 18_200,
            "risk_score": 0.48,
            "channel": "transfer",
            "label": 1,
            "scenario_ground_truth": "split_cross_bank_cycle",
        },
        {
            "signal_ref": "demo-c-001",
            "institution_id": "bank_c",
            "source_entity_id": "MULE-301",
            "destination_entity_id": "A-101",
            "timestamp": "2026-10-17T10:42:00Z",
            "amount": 17_900,
            "risk_score": 0.45,
            "channel": "transfer",
            "label": 1,
            "scenario_ground_truth": "split_cross_bank_cycle",
        },
    ]


def three_bank_fraud_ring() -> list[dict[str, Any]]:
    """Transform the local demo ledger before it crosses the graph boundary."""
    return transform_bank_local_ledger(
        three_bank_demo_ledger(), linkage_secret=DEMO_SECRET
    )

