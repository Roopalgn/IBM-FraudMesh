"""Conservative, explainable structural detection over permitted signals."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from typing import Any

import networkx as nx

from fraudmesh.privacy import parse_timestamp_bucket, validate_shared_signals


MAX_CYCLE_NODES = 6
MIN_DISTINCT_COUNTERPARTIES = 3
RAPID_PROPAGATION_WINDOW = timedelta(hours=2)


@dataclass(frozen=True)
class StructuralCandidate:
    """A pattern and the exact directed pairs that support it."""

    pattern: str
    nodes: tuple[str, ...]
    pairs: tuple[tuple[str, str], ...]


def build_collaboration_graph(shared_signals: list[dict[str, Any]]) -> nx.MultiDiGraph:
    """Build a directed graph only after strict shared-schema validation."""
    validate_shared_signals(shared_signals)
    graph = nx.MultiDiGraph()
    for signal in shared_signals:
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


def _simple_graph(graph: nx.MultiDiGraph) -> nx.DiGraph:
    simple = nx.DiGraph()
    simple.add_nodes_from(graph.nodes)
    simple.add_edges_from((source, target) for source, target in graph.edges())
    return simple


def _canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    rotations = [tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle))]
    return min(rotations)


def _find_structural_candidates(graph: nx.MultiDiGraph) -> list[StructuralCandidate]:
    """Find cycles and distinct-counterparty fans without counting parallel edges."""
    simple = _simple_graph(graph)
    candidates: list[StructuralCandidate] = []
    seen_cycles: set[tuple[str, ...]] = set()

    for cycle in nx.simple_cycles(simple, length_bound=MAX_CYCLE_NODES):
        if len(cycle) < 3:
            continue
        normalized = _canonical_cycle(cycle)
        if normalized in seen_cycles:
            continue
        seen_cycles.add(normalized)
        pairs = tuple(
            (normalized[index], normalized[(index + 1) % len(normalized)])
            for index in range(len(normalized))
        )
        candidates.append(StructuralCandidate("cycle", normalized, pairs))

    for node in sorted(simple.nodes):
        targets = tuple(sorted(simple.successors(node)))
        if len(targets) >= MIN_DISTINCT_COUNTERPARTIES:
            candidates.append(
                StructuralCandidate(
                    "fan_out",
                    tuple(sorted((node, *targets))),
                    tuple((node, target) for target in targets),
                )
            )
        sources = tuple(sorted(simple.predecessors(node)))
        if len(sources) >= MIN_DISTINCT_COUNTERPARTIES:
            candidates.append(
                StructuralCandidate(
                    "fan_in",
                    tuple(sorted((*sources, node))),
                    tuple((source, node) for source in sources),
                )
            )
    return candidates


def _supporting_edges(
    graph: nx.MultiDiGraph, pairs: tuple[tuple[str, str], ...]
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for source, target in pairs:
        for signal_id, data in (graph.get_edge_data(source, target) or {}).items():
            edges.append(
                {
                    "id": signal_id,
                    "source": source,
                    "target": target,
                    **data,
                }
            )
    return sorted(edges, key=lambda edge: edge["signal_id"])


def _candidate_alert(
    graph: nx.MultiDiGraph, candidate: StructuralCandidate
) -> dict[str, Any]:
    edges = _supporting_edges(graph, candidate.pairs)
    institutions = sorted({edge["institution_id"] for edge in edges})
    buckets = sorted({edge["timestamp_bucket"] for edge in edges})
    bucket_times = [parse_timestamp_bucket(bucket) for bucket in buckets]
    elapsed = max(bucket_times) - min(bucket_times)
    supporting_signal_ids = [edge["signal_id"] for edge in edges]
    cross_institution = len(institutions) >= 2
    evidence: list[dict[str, Any]] = [
        {
            "code": candidate.pattern,
            "supporting_signal_ids": supporting_signal_ids,
            "linked_entities": list(candidate.nodes),
        }
    ]
    if candidate.pattern == "cycle" and cross_institution:
        evidence.append(
            {
                "code": "cross_institution_cycle",
                "supporting_signal_ids": supporting_signal_ids,
                "institutions": institutions,
            }
        )
    elif cross_institution:
        evidence.append(
            {
                "code": "cross_institution_structure",
                "supporting_signal_ids": supporting_signal_ids,
                "institutions": institutions,
            }
        )
    if len(edges) >= 3 and elapsed <= RAPID_PROPAGATION_WINDOW:
        evidence.append(
            {
                "code": "rapid_propagation",
                "elapsed_minutes": int(elapsed.total_seconds() // 60),
                "resolution": "UTC hour buckets",
            }
        )

    fingerprint_material = "|".join(
        [candidate.pattern, *supporting_signal_ids]
    ).encode("utf-8")
    fingerprint = sha256(fingerprint_material).hexdigest()[:12]
    return {
        "alert_id": f"FM-RING-{fingerprint}",
        "risk_level": "high" if cross_institution else "medium",
        "structural_pattern": candidate.pattern,
        "cross_institution": cross_institution,
        "institutions_involved": institutions,
        "linked_entities": list(candidate.nodes),
        "evidence": evidence,
        "supporting_signal_ids": supporting_signal_ids,
        "timestamp_buckets": buckets,
        "time_window_minutes": int(elapsed.total_seconds() // 60),
        "max_local_risk_score": max(edge["local_risk_score"] for edge in edges),
        "edge_count": len(edges),
    }


def _graph_payload(graph: nx.MultiDiGraph) -> dict[str, list[dict[str, Any]]]:
    memberships: dict[str, set[str]] = defaultdict(set)
    for source, target, data in graph.edges(data=True):
        memberships[source].add(data["institution_id"])
        memberships[target].add(data["institution_id"])

    nodes = [
        {"id": node, "institution_ids": sorted(memberships[node])}
        for node in sorted(graph.nodes)
    ]
    edges = [
        {
            "id": data["signal_id"],
            "signal_id": data["signal_id"],
            "source": source,
            "target": target,
            "institution_id": data["institution_id"],
            "timestamp_bucket": data["timestamp_bucket"],
            "amount_bucket": data["amount_bucket"],
            "local_risk_score": data["local_risk_score"],
            "channel": data["channel"],
        }
        for source, target, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": sorted(edges, key=lambda edge: edge["id"])}


def detect_fraud_rings(shared_signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Return conservative structural findings over one visible signal set.

    Local ML scores are shown as evidence only. They neither trigger structural
    findings nor change their severity in this prototype.
    """
    graph = build_collaboration_graph(shared_signals)
    alerts = [
        _candidate_alert(graph, candidate)
        for candidate in _find_structural_candidates(graph)
    ]
    alerts.sort(key=lambda alert: alert["alert_id"])
    return {
        "alerts": alerts,
        "summary": {
            "signals_processed": graph.number_of_edges(),
            "pseudonymous_entities": graph.number_of_nodes(),
            "structural_findings": len(alerts),
            "local_risk_score_usage": "displayed as evidence only; not fused into detection or severity",
            "schema_validation": "restricted shared-signal schema accepted",
        },
        "graph": _graph_payload(graph),
    }


def compare_local_and_collaborative(
    shared_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare structural findings at each bank with the combined signal view.

    Counts here are structural findings, not transaction-alert counts or a
    generalized fraud-performance metric.
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
    local_finding_count = sum(
        result["summary"]["structural_findings"]
        for result in local_results.values()
    )
    collaborative_finding_count = collaborative_result["summary"]["structural_findings"]
    return {
        "comparison_unit": "structural pattern findings",
        "local_only": {
            "institutions": list(local_results),
            "signals_processed": len(shared_signals),
            "finding_count": local_finding_count,
            "findings_by_institution": {
                institution_id: result["alerts"]
                for institution_id, result in local_results.items()
            },
        },
        "collaborative": {
            "institutions": sorted(by_institution),
            "signals_processed": len(shared_signals),
            "finding_count": collaborative_finding_count,
            "findings": collaborative_result["alerts"],
        },
        "interpretation": (
            "Controlled synthetic comparison only. Each bank sees its own "
            "permitted subgraph; the combined view can reconstruct patterns "
            "whose supporting edges are split across banks."
        ),
    }
