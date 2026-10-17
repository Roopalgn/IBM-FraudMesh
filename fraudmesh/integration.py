"""Component response assembly for the FraudMesh graph-side integration."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fraudmesh.graph_engine import compare_local_and_collaborative, detect_fraud_rings
from fraudmesh.privacy import SHARED_SCHEMA_VERSION, validate_shared_signals


def build_analysis_response(shared_signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a graph-component response from already permitted shared signals.

    Person 1 owns the final API contract. The documented mapping in
    ``docs/graph_api_proposal.md`` describes how this component response can
    be adapted without passing raw bank ledger rows to the graph service.
    """
    validate_shared_signals(shared_signals)
    detection = detect_fraud_rings(shared_signals)
    comparison = compare_local_and_collaborative(shared_signals)

    bank_signals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in shared_signals:
        bank_signals[signal["institution_id"]].append(signal)

    return {
        "component_metadata": {
            "shared_signal_schema": SHARED_SCHEMA_VERSION,
            "validation": "restricted schema and scalar representations validated",
            "scenario": "synthetic_only",
        },
        "bank_results": [
            {
                "institution_id": institution_id,
                "signals_processed": len(signals),
                "local_structural_findings": comparison["local_only"][
                    "findings_by_institution"
                ].get(institution_id, []),
            }
            for institution_id, signals in sorted(bank_signals.items())
        ],
        "collaborative_alerts": detection["alerts"],
        "graph": detection["graph"],
        "comparison": comparison,
        "privacy": {
            "service_verifies": [
                "the request matches the restricted shared-signal schema",
                "approved scalar representations are used for tokens, buckets, scores, and channels",
                "the intended graph interface accepts shared signals rather than raw ledger rows",
            ],
            "service_cannot_verify": [
                "the complete upstream behavior of a submitting bank",
                "the authenticity or authorization of a syntactically valid token",
                "the absence of all inference risk from shared relationships and timing",
            ],
            "limitations": [
                "HMAC pseudonyms remain linkable",
                "shared-key custody and rotation are outside this prototype",
                "three banks are simulated rather than organizationally isolated",
                "Secure Execution, secure aggregation, differential privacy, and remote attestation are not established",
            ],
        },
        "summary": detection["summary"],
    }
