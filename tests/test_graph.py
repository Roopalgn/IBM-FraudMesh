"""Regression coverage for FraudMesh privacy and graph-side integration."""

from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from fraudmesh.graph_engine import (
    compare_local_and_collaborative,
    detect_fraud_rings,
)
from fraudmesh.integration import build_analysis_response
from fraudmesh.local_transform import transform_bank_local_ledger
from fraudmesh.privacy import (
    PrivacyContractError,
    create_shared_signal,
    pseudonymize_identifier,
)
from fraudmesh.scenarios import (
    DEMO_SECRET,
    three_bank_demo_ledger,
    three_bank_fraud_ring,
)


def cycle_signals(
    *,
    institutions: tuple[str, str, str] = ("bank_a", "bank_b", "bank_c"),
    timestamps: tuple[str, str, str] = (
        "2026-10-17T10:05:00Z",
        "2026-10-17T10:25:00Z",
        "2026-10-17T10:50:00Z",
    ),
) -> list[dict]:
    entities = ("entity-a", "entity-b", "entity-c")
    return [
        create_shared_signal(
            signal_id=f"cycle-{index}",
            institution_id=institutions[index - 1],
            source_entity_id=entities[index - 1],
            destination_entity_id=entities[index % 3],
            timestamp=timestamps[index - 1],
            amount=12_000,
            local_risk_score=0.4,
            secret=DEMO_SECRET,
            channel="transfer",
        )
        for index in range(1, 4)
    ]


class SharedSignalValidationTests(unittest.TestCase):
    def test_hmac_linking_is_deterministic_keyed_and_canonical(self):
        first = pseudonymize_identifier("Shared Entity", DEMO_SECRET)
        self.assertEqual(first, pseudonymize_identifier(" shared entity ", DEMO_SECRET))
        self.assertNotEqual(first, pseudonymize_identifier("Shared Entity", "another-key"))
        self.assertRegex(first, r"^fm1:[0-9a-f]{64}$")

    def test_malformed_token_and_exact_values_disguised_as_buckets_are_rejected(self):
        for field, value in (
            ("source_entity_token", "fm1:RAW-ACCOUNT-123"),
            ("timestamp_bucket", "2026-10-17T10:05:23Z"),
            ("amount_bucket", "18500.73"),
        ):
            signal = three_bank_fraud_ring()[0]
            signal[field] = value
            with self.subTest(field=field):
                with self.assertRaises(PrivacyContractError):
                    detect_fraud_rings([signal])

    def test_nested_raw_data_in_approved_field_is_rejected(self):
        signal = three_bank_fraud_ring()[0]
        signal["channel"] = {"customer_name": "not allowed"}
        with self.assertRaises(PrivacyContractError):
            detect_fraud_rings([signal])

    def test_boolean_and_nonfinite_scores_are_rejected(self):
        for value in (True, math.inf, -math.inf, math.nan):
            signal = three_bank_fraud_ring()[0]
            signal["local_risk_score"] = value
            with self.subTest(value=repr(value)):
                with self.assertRaises(PrivacyContractError):
                    detect_fraud_rings([signal])

    def test_empty_malformed_and_duplicate_batches_are_rejected(self):
        for batch in ([], "not-a-batch", ["not-an-object"]):
            with self.subTest(batch_type=type(batch).__name__):
                with self.assertRaises(PrivacyContractError):
                    detect_fraud_rings(batch)
        signals = three_bank_fraud_ring()
        signals[1]["signal_id"] = signals[0]["signal_id"]
        with self.assertRaises(PrivacyContractError):
            detect_fraud_rings(signals)

    def test_labels_remain_local_and_are_rejected_if_submitted(self):
        signals = transform_bank_local_ledger(
            three_bank_demo_ledger(), linkage_secret=DEMO_SECRET
        )
        self.assertTrue(all("label" not in signal for signal in signals))
        self.assertTrue(all("scenario_ground_truth" not in signal for signal in signals))
        signals[0]["label"] = 1
        with self.assertRaises(PrivacyContractError):
            detect_fraud_rings(signals)

    def test_bank_local_transform_pseudonymizes_once_before_graph_boundary(self):
        ledger = three_bank_demo_ledger()
        signal = transform_bank_local_ledger([ledger[0]], linkage_secret=DEMO_SECRET)[0]
        expected = pseudonymize_identifier(ledger[0]["source_entity_id"], DEMO_SECRET)
        self.assertEqual(signal["source_entity_token"], expected)
        self.assertNotEqual(pseudonymize_identifier(expected, DEMO_SECRET), expected)


class StructuralDetectionTests(unittest.TestCase):
    def test_complete_cycle_visible_to_one_bank_is_detected_locally(self):
        signals = cycle_signals(institutions=("bank_a", "bank_a", "bank_a"))
        result = detect_fraud_rings(signals)
        self.assertEqual(result["summary"]["structural_findings"], 1)
        alert = result["alerts"][0]
        self.assertEqual(alert["structural_pattern"], "cycle")
        self.assertFalse(alert["cross_institution"])
        self.assertEqual(alert["risk_level"], "medium")

    def test_split_cross_bank_cycle_requires_collaborative_view(self):
        comparison = compare_local_and_collaborative(three_bank_fraud_ring())
        self.assertEqual(comparison["comparison_unit"], "structural pattern findings")
        self.assertEqual(comparison["local_only"]["finding_count"], 0)
        self.assertEqual(comparison["collaborative"]["finding_count"], 1)
        finding = comparison["collaborative"]["findings"][0]
        self.assertTrue(finding["cross_institution"])
        self.assertIn(
            "cross_institution_cycle",
            [item["code"] for item in finding["evidence"]],
        )

    def test_ordinary_multi_bank_chain_is_not_a_structural_finding(self):
        signals = [
            create_shared_signal(
                signal_id=f"ordinary-{index}",
                institution_id=bank,
                source_entity_id=source,
                destination_entity_id=destination,
                timestamp="2026-10-17T10:00:00Z",
                amount=200,
                local_risk_score=0.1,
                secret=DEMO_SECRET,
                channel="card",
            )
            for index, (bank, source, destination) in enumerate(
                (
                    ("bank_a", "person-1", "merchant-1"),
                    ("bank_b", "merchant-1", "merchant-2"),
                    ("bank_c", "merchant-2", "merchant-3"),
                ),
                1,
            )
        ]
        self.assertEqual(detect_fraud_rings(signals)["alerts"], [])

    def test_parallel_edges_do_not_create_a_distinct_counterparty_fan(self):
        signals = [
            create_shared_signal(
                signal_id=f"parallel-{index}",
                institution_id="bank_a",
                source_entity_id="origin",
                destination_entity_id="one-recipient",
                timestamp=f"2026-10-17T1{index}:00:00Z",
                amount=5_000,
                local_risk_score=0.3,
                secret=DEMO_SECRET,
                channel="transfer",
            )
            for index in range(1, 4)
        ]
        self.assertEqual(detect_fraud_rings(signals)["alerts"], [])

    def test_distinct_counterparty_fan_is_detected(self):
        signals = [
            create_shared_signal(
                signal_id=f"fan-{index}",
                institution_id="bank_a",
                source_entity_id="origin",
                destination_entity_id=f"recipient-{index}",
                timestamp="2026-10-17T10:00:00Z",
                amount=5_000,
                local_risk_score=0.3,
                secret=DEMO_SECRET,
                channel="transfer",
            )
            for index in range(1, 4)
        ]
        alert = detect_fraud_rings(signals)["alerts"][0]
        self.assertEqual(alert["structural_pattern"], "fan_out")
        self.assertEqual(alert["supporting_signal_ids"], ["fan-1", "fan-2", "fan-3"])

    def test_external_edge_does_not_make_a_local_cycle_cross_institution(self):
        signals = cycle_signals(institutions=("bank_a", "bank_a", "bank_a"))
        signals.append(
            create_shared_signal(
                signal_id="external-1",
                institution_id="bank_b",
                source_entity_id="entity-a",
                destination_entity_id="outside-entity",
                timestamp="2026-10-17T10:30:00Z",
                amount=1_000,
                local_risk_score=0.2,
                secret=DEMO_SECRET,
                channel="transfer",
            )
        )
        alert = detect_fraud_rings(signals)["alerts"][0]
        self.assertFalse(alert["cross_institution"])
        self.assertNotIn(
            "cross_institution_cycle", [item["code"] for item in alert["evidence"]]
        )

    def test_rapid_propagation_uses_actual_bucket_elapsed_time(self):
        close = detect_fraud_rings(cycle_signals())["alerts"][0]
        midnight = detect_fraud_rings(
            cycle_signals(
                timestamps=(
                    "2026-10-17T23:05:00Z",
                    "2026-10-18T00:10:00Z",
                    "2026-10-18T01:15:00Z",
                )
            )
        )["alerts"][0]
        distant = detect_fraud_rings(
            cycle_signals(
                timestamps=(
                    "2026-10-01T10:00:00Z",
                    "2026-10-08T10:00:00Z",
                    "2026-10-15T10:00:00Z",
                )
            )
        )["alerts"][0]
        self.assertIn("rapid_propagation", [item["code"] for item in close["evidence"]])
        self.assertIn("rapid_propagation", [item["code"] for item in midnight["evidence"]])
        self.assertNotIn("rapid_propagation", [item["code"] for item in distant["evidence"]])

    def test_invalid_bucket_date_is_rejected(self):
        signal = three_bank_fraud_ring()[0]
        signal["timestamp_bucket"] = "2026-02-30T10:00Z"
        with self.assertRaises(PrivacyContractError):
            detect_fraud_rings([signal])

    def test_alerts_and_graph_references_are_deterministic(self):
        forward = detect_fraud_rings(three_bank_fraud_ring())
        reverse = detect_fraud_rings(list(reversed(three_bank_fraud_ring())))
        self.assertEqual(forward["alerts"], reverse["alerts"])
        self.assertEqual(forward["graph"], reverse["graph"])
        edge_ids = {edge["id"] for edge in forward["graph"]["edges"]}
        for alert in forward["alerts"]:
            self.assertTrue(set(alert["supporting_signal_ids"]).issubset(edge_ids))


class IntegrationResponseTests(unittest.TestCase):
    def test_component_response_is_json_serializable_and_truthful_about_boundary(self):
        response = build_analysis_response(three_bank_fraud_ring())
        json.dumps(response, sort_keys=True)
        self.assertEqual(response["component_metadata"]["scenario"], "synthetic_only")
        self.assertNotIn("raw_transaction_rows_received", response["privacy"])
        self.assertEqual(len(response["collaborative_alerts"]), 1)
        self.assertEqual(len(response["graph"]["nodes"]), 3)
        self.assertEqual(len(response["graph"]["edges"]), 3)
        memberships = {
            tuple(node["institution_ids"]) for node in response["graph"]["nodes"]
        }
        self.assertEqual(
            memberships,
            {("bank_a", "bank_b"), ("bank_a", "bank_c"), ("bank_b", "bank_c")},
        )

    def test_serialized_detector_example_matches_the_deterministic_demo(self):
        example_path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "examples"
            / "three_bank_detector_response.json"
        )
        self.assertEqual(
            json.loads(example_path.read_text(encoding="utf-8")),
            detect_fraud_rings(three_bank_fraud_ring()),
        )


if __name__ == "__main__":
    unittest.main()
