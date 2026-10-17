"""Versioned, transparent ML-informed prioritization of structural findings.

This is a policy layered over a trained transaction model, not a second trained
classifier or calibrated fraud probability. Labels and scenario IDs are absent.
"""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict

POLICY_VERSION = "ml-graph-triage/v1"
REVIEW_THRESHOLD = 0.75


def prioritize(finding: dict, signals: list[dict]) -> dict:
    refs = set(finding["supporting_signal_ids"])
    supporting = [row for row in signals if row["signal_id"] in refs]
    if not supporting or len(supporting) != len(refs):
        raise ValueError("Triage requires complete supporting signals")
    incoming, outgoing = defaultdict(set), defaultdict(set)
    for row in supporting:
        if row["source_entity_token"] != row["destination_entity_token"]:
            outgoing[row["source_entity_token"]].add(row["destination_entity_token"])
            incoming[row["destination_entity_token"]].add(row["source_entity_token"])
    two_sided_hub = any(len(incoming[node]) >= 3 and len(outgoing[node]) >= 3
                        for node in finding["linked_entities"])
    structure = 1.0 if finding["structural_pattern"] == "cycle" or two_sided_hub else .25
    mean_risk = sum(row["local_risk_score"] for row in supporting) / len(supporting)
    temporal = 1.0 if finding["time_window_minutes"] <= 120 else 0.0
    bands = [row["amount_bucket"] for row in supporting]
    consistency = max(bands.count(band) for band in set(bands)) / len(bands)
    priority = .35 * structure + .35 * mean_risk + .20 * temporal + .10 * consistency
    return {"policy_version": POLICY_VERSION, "priority_score": round(priority, 8),
            "review_recommended": priority >= REVIEW_THRESHOLD,
            "threshold": REVIEW_THRESHOLD,
            "features": {"structure_strength": structure, "mean_local_model_score": mean_risk,
                         "nearby_hour_buckets": temporal, "amount_band_consistency": consistency},
            "score_meaning": "Transparent review priority, not a fraud probability"}


def annotate_analysis(component: dict, signals: list[dict]) -> dict:
    result = deepcopy(component)
    all_findings = [result["collaborative_alerts"], result["comparison"]["collaborative"]["findings"]]
    all_findings += [bank["local_structural_findings"] for bank in result["bank_results"]]
    all_findings += list(result["comparison"]["local_only"]["findings_by_institution"].values())
    by_bank = defaultdict(list)
    for row in signals:
        by_bank[row["institution_id"]].append(row)
    seen = set()
    for findings in all_findings:
        for finding in findings:
            if id(finding) in seen:
                continue
            seen.add(id(finding))
            # Local findings must use only that bank's visible graph context.
            context = signals if finding["cross_institution"] else by_bank[finding["institutions_involved"][0]]
            triage = prioritize(finding, context)
            finding["triage"] = triage
            finding["structural_risk_level"] = finding["risk_level"]
            finding["risk_level"] = "high" if triage["review_recommended"] else "medium"
            finding["evidence"].append({"code": "ml_informed_priority", "priority_score": triage["priority_score"],
                                        "review_recommended": triage["review_recommended"],
                                        "mean_local_model_score": triage["features"]["mean_local_model_score"],
                                        "policy_version": POLICY_VERSION})
    result["review_queue"] = {"policy_version": POLICY_VERSION, "threshold": REVIEW_THRESHOLD,
        "local_recommended": sum(finding["triage"]["review_recommended"]
            for bank in result["bank_results"] for finding in bank["local_structural_findings"]),
        "combined_recommended": sum(finding["triage"]["review_recommended"] for finding in result["collaborative_alerts"]),
        "cross_bank_recommended": sum(finding["triage"]["review_recommended"] and finding["cross_institution"]
                                      for finding in result["collaborative_alerts"]),
        "note": "All structural candidates remain visible. Prioritization does not establish fraud."}
    return result
