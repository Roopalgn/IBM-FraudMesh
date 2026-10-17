"""Adapt computed graph output to the investigator display contract."""
from __future__ import annotations

from collections import defaultdict

from fraudmesh.integration import build_analysis_response
from fraudmesh.privacy import SHARED_SIGNAL_FIELDS

BANK_NAMES = {"bank_a": "Bank A", "bank_b": "Bank B", "bank_c": "Bank C"}
REASONS = {
    "cycle": ("Directed cycle", "The supporting permitted transfers form a closed directed path."),
    "cross_institution_cycle": ("Cross-bank cycle", "A detected directed cycle includes signals contributed by multiple banks."),
    "fan_in": ("Multiple senders", "At least one entity has three or more distinct source neighbours."),
    "fan_out": ("Multiple recipients", "At least one entity has three or more distinct destination neighbours."),
    "rapid_propagation": ("Nearby time buckets", "Supporting UTC hour buckets span at most two hours; exact transfer timing remains local."),
    "cross_institution_structure": ("Multi-bank pattern", "Multiple banks contributed the relationships supporting this pattern."),
}


def analyze_for_dashboard(signals: list[dict], scenario_id: str = "synthetic-custom") -> dict:
    # A valid empty API snapshot is distinct from the component's nonempty-batch contract.
    computed = build_analysis_response(signals) if signals else {
        "collaborative_alerts": [], "summary": {"signals_processed": 0, "pseudonymous_entities": 0, "structural_findings": 0},
        "comparison": {"comparison_unit": "structural pattern findings",
                       "local_only": {"finding_count": 0, "findings_by_institution": {}},
                       "collaborative": {"finding_count": 0, "findings": []}}}
    memberships = defaultdict(set)
    scores = defaultdict(list)
    by_bank = defaultdict(list)
    for signal in signals:
        bank = signal["institution_id"]
        by_bank[bank].append(signal)
        for token in (signal["source_entity_token"], signal["destination_entity_token"]):
            memberships[token].add(bank)
            scores[token].append(signal["local_risk_score"])
    node_ids = sorted(memberships)
    nodes = [{"id": token, "label": f"Entity {index+1:02d}",
              "bank_id": sorted(memberships[token])[0],
              "bank_ids": sorted(memberships[token]),
              "local_risk": max(scores[token])} for index, token in enumerate(node_ids)]
    ordered = sorted(signals, key=lambda signal: (signal["timestamp_bucket"], signal["signal_id"]))
    edges = [{"id": signal["signal_id"], "source": signal["source_entity_token"],
              "target": signal["destination_entity_token"], "institution_id": signal["institution_id"],
              "local_risk_score": signal["local_risk_score"],
              "kind": "permitted_transfer", "step": index+1,
              "time_bucket": signal["timestamp_bucket"],
              "risk_band": "high" if signal["local_risk_score"] >= .55 else "medium" if signal["local_risk_score"] >= .275 else "low"}
             for index, signal in enumerate(ordered)]
    comparison = computed["comparison"]
    alerts = [{"id": alert["alert_id"], "title": f"Suspicious multi-bank {alert['structural_pattern']}",
               "severity": alert["risk_level"], "detected_at_step": max(edge["step"] for edge in edges if edge["id"] in alert["supporting_signal_ids"]),
               "node_ids": alert["linked_entities"], "edge_ids": alert["supporting_signal_ids"],
               "reasons": [{"code": evidence["code"], "title": REASONS[evidence["code"]][0],
                            "detail": REASONS[evidence["code"]][1]}
                           for evidence in alert["evidence"]]}
              for alert in computed["collaborative_alerts"] if alert["cross_institution"]]
    banks = []
    for bank in BANK_NAMES:
        local_rings = comparison["local_only"]["findings_by_institution"].get(bank, [])
        high_scores = sum(signal["local_risk_score"] >= .55 for signal in by_bank[bank])
        banks.append({"id": bank, "name": BANK_NAMES[bank],
                      "entity_count": sum(bank in values for values in memberships.values()),
                      "local_alerts": high_scores, "local_ring_count": len(local_rings),
                      "local_findings": [{"title": "Local graph analysis", "detail": f"{len(local_rings)} structural pattern findings from this bank's own signals; {high_scores} high transaction risk scores."}]})
    return {"schema_version": "1.0", "scenario_id": scenario_id, "synthetic": True,
            "banks": banks, "graph": {"nodes": nodes, "edges": edges},
            "collaborative_alerts": alerts, "comparison": comparison,
            "sharing_summary": {"raw_rows_shared": None, "shared_fields": sorted(SHARED_SIGNAL_FIELDS),
                                "retained_local": ["Raw entity and transaction references", "Exact amounts and timestamps", "Evaluation labels"],
                                "execution_verified": False,
                                "validation_scope": "Accepted signal schema and value formats only; not a network audit or sender attestation."},
            "score_semantics": "Node risk is the maximum incident transaction ML score, not an entity fraud probability.",
            "summary": computed["summary"]}
