"""API-ready response assembly for the shared FraudMesh analysis service."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fraudmesh.graph_engine import compare_local_and_collaborative, detect_fraud_rings
from fraudmesh.privacy import validate_shared_signals


def build_analysis_response(shared_signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the stable payload consumed by the API and dashboard.

    This adapter deliberately accepts only allowlisted shared signals. Raw
    bank transaction rows should be transformed locally before this function
    is called.
    """
    validate_shared_signals(shared_signals)
    detection = detect_fraud_rings(shared_signals)
    comparison = compare_local_and_collaborative(shared_signals)

    bank_signals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in shared_signals:
        bank_signals[signal["institution_id"]].append(signal)

    return {
        "bank_results": [
            {
                "institution_id": institution_id,
                "signals_processed": len(signals),
                "local_alerts": comparison["local_only"]["alerts_by_institution"].get(
                    institution_id, []
                ),
            }
            for institution_id, signals in sorted(bank_signals.items())
        ],
        "collaborative_alerts": detection["alerts"],
        "graph": detection["graph"],
        "comparison": comparison,
        "privacy": {
            "raw_transaction_rows_received": 0,
            "shared_fields": detection["summary"]["shared_fields"],
            "raw_fields_transmitted": [],
            "pseudonymization": "HMAC tokens are pseudonymous, not a formal privacy guarantee",
            "validation_scope": "Schema and value validation of accepted signals; not a network audit or proof of sender behaviour",
        },
        "summary": detection["summary"],
    }

