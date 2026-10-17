"""Unit tests for the Person 3 privacy and graph implementation."""

import unittest

from fraudmesh.graph_engine import detect_fraud_rings
from fraudmesh.privacy import PrivacyContractError, create_shared_signal, pseudonymize_identifier
from fraudmesh.scenarios import DEMO_SECRET, three_bank_fraud_ring


class PrivacyTests(unittest.TestCase):
    def test_hmac_linking_is_deterministic_and_keyed(self):
        first = pseudonymize_identifier("Shared Entity", DEMO_SECRET)
        self.assertEqual(first, pseudonymize_identifier(" shared entity ", DEMO_SECRET))
        self.assertNotEqual(first, pseudonymize_identifier("Shared Entity", "another-key"))
        self.assertNotIn("Shared Entity", first)

    def test_raw_fields_are_rejected_at_collaboration_boundary(self):
        signal = three_bank_fraud_ring()[0]
        signal["amount"] = 18_500
        with self.assertRaises(PrivacyContractError):
            detect_fraud_rings([signal])


class GraphEngineTests(unittest.TestCase):
    def test_three_bank_ring_is_detected_with_evidence(self):
        result = detect_fraud_rings(three_bank_fraud_ring())
        self.assertEqual(result["summary"]["raw_transaction_rows_received"], 0)
        self.assertEqual(result["summary"]["alerts_generated"], 1)
        alert = result["alerts"][0]
        self.assertEqual(alert["institutions_involved"], ["bank_a", "bank_b", "bank_c"])
        self.assertIn("cross_institution_cycle", alert["evidence"])
        self.assertIn("rapid_propagation", alert["evidence"])

    def test_unrelated_single_bank_activity_is_not_a_ring(self):
        signal = create_shared_signal(
            signal_id="normal-1",
            institution_id="bank_a",
            source_entity_id="customer-1",
            destination_entity_id="merchant-1",
            timestamp="2026-10-17T10:05:00Z",
            amount=150,
            local_risk_score=0.10,
            secret=DEMO_SECRET,
            channel="card",
        )
        result = detect_fraud_rings([signal])
        self.assertEqual(result["alerts"], [])


if __name__ == "__main__":
    unittest.main()

