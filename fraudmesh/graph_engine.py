"""Explainable cross-institution fraud-ring detection for shared signals."""

from __future__ import annotations

from hashlib import sha256
from collections import defaultdict
from typing import Any, Iterable, Mapping

import networkx as nx

from fraudmesh.privacy import validate_shared_signals


def build_collaboration_graph(shared_signals: Iterable[Mapping[str, Any]]) -> nx.MultiDiGraph:
    """Build a directed graph using only already-validated shared fields."""
    signals = list(shared_signals)
    validate_shared_signals(signals)
    graph = nx.MultiDiGraph()
    for signal in signals:
        source = signal["source_entity_token"]
        target = signal["destination_entity_token"]
        graph.add_edge(
            source,
            target,
            key=signal["signal_id"],
            signal_id=signal["signal_id"],
            institution_id=signal["institution_id"],
            timestamp_bucket=signal["timestamp_bucket"],
            amount_bucket=signal["amount_bucket"],
            local_risk_score=float(signal["local_risk_score"]),
            channel=signal["channel"],
        )
    return graph


def _component_evidence(graph: nx.MultiDiGraph, nodes: set[str]) -> tuple[list[str], list[str], list[str], float]:
    subgraph = graph.subgraph(nodes)
    institutions = sorted(
        {data["institution_id"] for _, _, data in subgraph.edges(data=True)}
    )
    buckets = sorted({data["timestamp_bucket"] for _, _, data in subgraph.edges(data=True)})
    reasons: list[str] = []
    simple = nx.DiGraph(subgraph)
    cycles = list(nx.simple_cycles(simple, length_bound=6))
    if cycles:
        reasons.append("cross_institution_cycle")
    if any(subgraph.out_degree(node) >= 2 for node in subgraph.nodes):
        reasons.append("fan_out")
    if any(subgraph.in_degree(node) >= 2 for node in subgraph.nodes):
        reasons.append("fan_in")
    if len(buckets) <= 2 and subgraph.number_of_edges() >= 3:
        reasons.append("rapid_propagation")
    if len(institutions) >= 2:
        reasons.append("cross_institution_relationships")
    max_risk = max(
        data["local_risk_score"] for _, _, data in subgraph.edges(data=True)
    )
    return institutions, buckets, reasons, max_risk


def _is_alert_worthy(
    graph: nx.MultiDiGraph, institutions: list[str], reasons: list[str]
) -> bool:
    """Use transparent evidence thresholds, not scenario-specific IDs."""
    structural = {"cross_institution_cycle", "fan_in", "fan_out"}
    return (
        len(institutions) >= 2
        and graph.number_of_edges() >= 3
        and bool(structural.intersection(reasons))
    )


def detect_fraud_rings(shared_signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect suspicious multi-bank components and return traceable evidence.

    Alerts are produced only when the allowlisted graph contains a multi-bank
    structural pattern.  This deliberately simple detector is deterministic
    and inspectable; it is a prototype rule engine rather than a trained fraud
    classifier.
    """
    graph = build_collaboration_graph(shared_signals)
    alerts: list[dict[str, Any]] = []

    for component in nx.weakly_connected_components(graph):
        subgraph = graph.subgraph(component).copy()
        institutions, buckets, reasons, max_risk = _component_evidence(subgraph, set(component))
        if not _is_alert_worthy(subgraph, institutions, reasons):
            continue
        signal_ids = sorted(data["signal_id"] for _, _, data in subgraph.edges(data=True))
        fingerprint = sha256("|".join(signal_ids).encode("utf-8")).hexdigest()[:12]
        alerts.append(
            {
                "alert_id": f"FM-RING-{fingerprint}",
                "risk_level": "high" if len(institutions) >= 3 else "medium",
                "institutions_involved": institutions,
                "linked_entities": sorted(component),
                "evidence": reasons,
                "signal_ids": signal_ids,
                "timestamp_buckets": buckets,
                "max_local_risk_score": max_risk,
                "edge_count": subgraph.number_of_edges(),
            }
        )

    alerts.sort(key=lambda item: (item["risk_level"] != "high", item["alert_id"]))
    return {
        "alerts": alerts,
        "summary": {
            "signals_processed": graph.number_of_edges(),
            "pseudonymous_entities": graph.number_of_nodes(),
            "alerts_generated": len(alerts),
            "shared_fields": [
                "pseudonymous entity tokens",
                "institution id",
                "coarse timestamp and amount buckets",
                "local risk score",
                "optional channel",
            ],
            "raw_transaction_rows_received": 0,
        },
        "graph": {
            "nodes": [{"id": node} for node in sorted(graph.nodes)],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "signal_id": data["signal_id"],
                    "institution_id": data["institution_id"],
                }
                for source, target, data in graph.edges(data=True)
            ],
        },
    }


def compare_local_and_collaborative(
    shared_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare each bank's isolated result with the combined graph result.

    This is deliberately a controlled-scenario comparison, not a claim about
    production fraud performance. Each bank runs the same detector on only
    its own permitted signals; the collaborative run then sees all signals.
    """
    validate_shared_signals(shared_signals)
    by_institution: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in shared_signals:
        by_institution[signal["institution_id"]].append(signal)

    local_results = {
        institution_id: detect_fraud_rings(signals)
        for institution_id, signals in sorted(by_institution.items())
    }
    collaborative_result = detect_fraud_rings(shared_signals)
    local_alert_count = sum(
        len(result["alerts"]) for result in local_results.values()
    )
    return {
        "local_only": {
            "institutions": list(local_results),
            "signals_processed": len(shared_signals),
            "alerts_generated": local_alert_count,
            "alerts_by_institution": {
                institution_id: result["alerts"]
                for institution_id, result in local_results.items()
            },
        },
        "collaborative": {
            "institutions": list(by_institution),
            "signals_processed": len(shared_signals),
            "alerts_generated": len(collaborative_result["alerts"]),
            "alerts": collaborative_result["alerts"],
        },
        "interpretation": (
            "Controlled synthetic comparison: the collaborative graph has "
            "cross-institution visibility that isolated bank views do not."
        ),
    }

