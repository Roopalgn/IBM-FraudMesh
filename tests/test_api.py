"""End-to-end and boundary regressions for the integrated synthetic prototype."""
from copy import deepcopy
import json
import unittest

from fastapi.testclient import TestClient

from app.main import app
from fraudmesh.demo import demo_request, demo_transactions, prepare_bank_signals
from fraudmesh.graph_engine import compare_local_and_collaborative, detect_fraud_rings
from fraudmesh.privacy import PrivacyContractError, coarse_amount_bucket, validate_shared_signals


class APIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def request(self, name="ring"):
        response = self.client.get("/demo/scenario", params={"name": name})
        self.assertEqual(response.status_code, 200)
        return response.json()["analysis_request"]

    def test_health_and_only_public_static_assets(self):
        health = self.client.get("/health").json()
        self.assertEqual(health["status"], "ok")
        self.assertFalse(health["confidential_execution_verified"])
        for path in ("/", "/styles.css", "/src/app.js", "/public/scenario.json"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ("/.git/config", "/data/README.md", "/fraudmesh/demo.py", "/.env"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_real_ml_to_graph_to_display_flow(self):
        request = self.request()
        response = self.client.post("/analyze", json=request)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["synthetic"])
        self.assertEqual(len(result["banks"]), 3)
        self.assertEqual(len(result["graph"]["edges"]), 9)
        self.assertEqual(len(result["collaborative_alerts"]), 1)
        self.assertEqual(result["comparison"]["local_only"]["alerts_generated"], 0)
        self.assertFalse(result["sharing_summary"]["execution_verified"])
        self.assertGreaterEqual(result["measurement"]["analysis_ms"], 0)
        self.assertTrue(any(len(node["bank_ids"]) > 1 for node in result["graph"]["nodes"]))

    def test_normal_multibank_negative_control(self):
        result = self.client.post("/analyze", json=self.request("normal")).json()
        self.assertEqual(result["collaborative_alerts"], [])
        self.assertEqual(result["comparison"]["local_only"]["alerts_generated"], 0)

    def test_complete_single_bank_cycle_is_detectable_locally(self):
        result = self.client.post("/analyze", json=self.request("local")).json()
        self.assertEqual(result["comparison"]["local_only"]["alerts_generated"], 1)
        self.assertEqual(result["collaborative_alerts"], [])

    def test_empty_analysis_is_valid(self):
        result = self.client.post("/analyze", json={"shared_signals": []})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["graph"], {"nodes": [], "edges": []})

    def test_no_raw_demo_data_or_secrets_in_requests_and_responses(self):
        payload = self.request()
        result = self.client.post("/analyze", json=payload).json()
        serialized = json.dumps([payload, result])
        for row in demo_transactions():
            for field in ("transaction_id", "source_entity_token", "destination_entity_token", "timestamp"):
                self.assertNotIn(row[field], serialized)
        for field in ("amount", "fraud_label", "customer_name", "secret"):
            self.assertNotIn('"' + field + '"', serialized)

    def test_rejected_data_is_not_echoed(self):
        response = self.client.post("/analyze", json={"raw_transactions": [{"customer": "DO-NOT-ECHO"}]})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("DO-NOT-ECHO", response.text)
        response = self.client.post("/analyze", content='{"shared_signals":DO-NOT-ECHO}', headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("DO-NOT-ECHO", response.text)

    def test_shared_field_content_is_validated(self):
        changes = [("source_entity_token", "fm1:RAW-ACCOUNT-123"),
                   ("timestamp_bucket", "2026-10-17T10:05:37Z"),
                   ("timestamp_bucket", "2026-02-30T10:00Z"),
                   ("amount_bucket", "18500.43"),
                   ("channel", {"customer_name": "DO-NOT-ECHO"}),
                   ("institution_id", "unknown"), ("local_risk_score", True),
                   ("local_risk_score", "0.5")]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                payload = self.request()
                payload["shared_signals"][0][field] = value
                response = self.client.post("/analyze", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("DO-NOT-ECHO", response.text)

    def test_duplicate_and_extra_fields_rejected(self):
        for mutate in (lambda signals: signals.append(deepcopy(signals[0])),
                       lambda signals: signals[0].update(amount=100),
                       lambda signals: signals.__setitem__(0, None)):
            payload = self.request()
            mutate(payload["shared_signals"])
            self.assertEqual(self.client.post("/analyze", json=payload).status_code, 422)

    def test_request_limits(self):
        self.assertEqual(self.client.post("/analyze", content="x" * 128001).status_code, 413)
        self.assertEqual(self.client.post("/analyze", json={"shared_signals": [{}] * 201}).status_code, 422)
        signals = self.request()["shared_signals"]
        original = signals[0]
        signals = [dict(original, signal_id=f"limit-{i}", source_entity_token=f"fm1:{2*i:064x}",
                        destination_entity_token=f"fm1:{2*i+1:064x}") for i in range(31)]
        self.assertEqual(self.client.post("/analyze", json={"shared_signals": signals}).status_code, 413)

    def test_cors_allows_only_configured_origins(self):
        for origin, allowed in (("http://localhost:4173", True), ("https://unapproved.example", False)):
            response = self.client.options("/analyze", headers={"Origin": origin,
                "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
            self.assertEqual(response.headers.get("access-control-allow-origin") == origin, allowed)


class GraphRegressionTests(unittest.TestCase):
    def test_distant_buckets_do_not_imply_rapid_propagation(self):
        signals = demo_request()["shared_signals"]
        for i, signal in enumerate(signals):
            signal["timestamp_bucket"] = f"2026-10-{i+1:02d}T10:00Z"
        for alert in detect_fraud_rings(signals)["alerts"]:
            self.assertNotIn("rapid_propagation", alert["evidence"])

    def test_repeated_same_counterparty_is_not_fan_out(self):
        base = demo_request()["shared_signals"][0]
        signals = [dict(base, signal_id=f"repeat-{i}", institution_id="bank_a" if i == 0 else "bank_b") for i in range(3)]
        self.assertEqual(detect_fraud_rings(signals)["alerts"], [])

    def test_local_detector_is_not_disabled_by_bank_count(self):
        comparison = compare_local_and_collaborative(demo_request("local")["shared_signals"])
        self.assertEqual(comparison["local_only"]["alerts_generated"], 1)

    def test_labels_and_future_rows_do_not_change_bank_local_preparation(self):
        rows = demo_transactions()
        original = deepcopy(rows)
        signals = prepare_bank_signals(rows, "synthetic-test-key")
        self.assertEqual(rows, original)
        for row in rows:
            row["fraud_label"] = "ignored-evaluation-only"
        self.assertEqual(signals, prepare_bank_signals(rows, "synthetic-test-key"))
        prefix = prepare_bank_signals(rows[:3], "synthetic-test-key")
        full = {signal["signal_id"]: signal for signal in signals}
        self.assertTrue(all(signal == full[signal["signal_id"]] for signal in prefix))

    def test_nonfinite_and_boolean_values_rejected(self):
        for value in (float("nan"), float("inf"), True, -1):
            with self.subTest(value=value):
                with self.assertRaises(PrivacyContractError):
                    coarse_amount_bucket(value)
                signals = demo_request()["shared_signals"]
                signals[0]["local_risk_score"] = value
                with self.assertRaises(PrivacyContractError):
                    validate_shared_signals(signals)

    def test_determinism_and_key_consistency(self):
        first = demo_request()
        self.assertEqual(first, demo_request())
        signals = first["shared_signals"]
        expected = detect_fraud_rings(signals)["alerts"]
        self.assertEqual(expected, detect_fraud_rings(list(reversed(signals)))["alerts"])


if __name__ == "__main__":
    unittest.main()
