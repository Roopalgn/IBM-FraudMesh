from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from fraudmesh.analysis import analyze_signals
from fraudmesh.audit import record_analysis, verify_journal
from fraudmesh.demo import demo_request
from fraudmesh.evaluation import evaluate_scenarios, evaluation_case, metrics
from fraudmesh.integration import build_analysis_response
from fraudmesh.triage import prioritize, POLICY_VERSION


class ReadinessTests(unittest.TestCase):
    def test_ml_scores_actually_change_review_priority(self):
        signals = demo_request("ring")["shared_signals"]
        finding = build_analysis_response(signals)["collaborative_alerts"][0]
        low, high = deepcopy(signals), deepcopy(signals)
        for row in low:
            row["local_risk_score"] = 0.0
        for row in high:
            row["local_risk_score"] = 1.0
        self.assertFalse(prioritize(finding, low)["review_recommended"])
        self.assertTrue(prioritize(finding, high)["review_recommended"])
        self.assertEqual(prioritize(finding, high)["policy_version"], POLICY_VERSION)

    def test_payroll_candidate_is_retained_but_not_recommended(self):
        result = analyze_signals(demo_request("common")["shared_signals"])
        self.assertEqual(result["summary"]["structural_findings"], 2)
        self.assertEqual(result["review_queue"]["combined_recommended"], 1)
        self.assertEqual(result["review_queue"]["local_recommended"], 0)
        for finding in result["collaborative_alerts"]:
            self.assertEqual(sum(e["code"] == "ml_informed_priority" for e in finding["evidence"]), 1)

    def test_two_sided_cross_bank_hub_has_complete_evidence(self):
        from fraudmesh.demo import prepare_bank_signals
        rows, _ = evaluation_case("mule_hub", 0)
        result = analyze_signals(prepare_bank_signals(rows, "test-only-key"))
        hubs = [finding for finding in result["collaborative_alerts"] if finding["structural_pattern"] == "flow_hub"]
        self.assertEqual(len(hubs), 1)
        self.assertEqual(len(hubs[0]["supporting_signal_ids"]), 6)
        self.assertTrue(hubs[0]["cross_institution"])

    def test_evaluation_is_deterministic_and_labels_stay_outside_inference(self):
        first, second = evaluate_scenarios(1), evaluate_scenarios(1)
        self.assertEqual(first, second)
        self.assertEqual(first["scenario_count"], 9)
        self.assertIn("ambiguous_fast_cycle", [row["kind"] for row in first["outcomes"]])
        rows, truth = evaluation_case("cross_bank_cycle", 0)
        self.assertTrue(truth)
        self.assertTrue(all("fraud_label" not in row for row in rows))
        self.assertEqual(metrics([(True, True), (False, True), (True, False), (False, False)])["confusion_matrix"], [[1, 1], [1, 1]])

    def test_scenario_reference_profile_and_real_computation(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"FRAUDMESH_AUDIT_PATH": str(Path(directory)/"audit.sqlite3")}):
            client = TestClient(app)
            scenario = client.get("/demo/scenario").json()
            self.assertEqual(scenario["response_profile"], "person3.graph.v2")
            self.assertEqual(set(scenario["analysis_request"]), {"scenario_id"})
            result = client.post("/analyze", json=scenario["analysis_request"])
            self.assertEqual(result.status_code, 200, result.text)
            payload = result.json()
            self.assertEqual(payload["summary"]["signals_processed"], 21)
            self.assertEqual(payload["review_queue"]["combined_recommended"], 1)
            self.assertTrue(payload["audit"]["event_hash"])
            self.assertTrue(client.get("/audit/status").json()["valid"])

    def test_audit_excludes_payloads_and_detects_inconsistent_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"audit.sqlite3"
            signals = demo_request("ring")["shared_signals"]
            response = analyze_signals(signals)
            record_analysis(target, signals, response, "synthetic-ring")
            record_analysis(target, signals, response, "synthetic-ring")
            self.assertEqual(verify_journal(target)["events"], 2)
            with closing(sqlite3.connect(target)) as db, db:
                serialized = db.execute("SELECT payload FROM events LIMIT 1").fetchone()[0]
                self.assertNotIn(signals[0]["source_entity_token"], serialized)
                self.assertNotIn(signals[0]["signal_id"], serialized)
                db.execute("UPDATE events SET payload='{}' WHERE seq=1")
            self.assertFalse(verify_journal(target)["valid"])

    def test_audit_failure_does_not_report_success(self):
        with patch("app.main.record_analysis", side_effect=OSError("DO-NOT-ECHO")):
            result = TestClient(app).post("/analyze", json={"scenario_id": "synthetic-common"})
            self.assertEqual(result.status_code, 503)
            self.assertNotIn("DO-NOT-ECHO", result.text)

    def test_unknown_reference_and_unexpected_request_fields_are_rejected(self):
        client = TestClient(app)
        self.assertEqual(client.post("/analyze", json={"scenario_id": "synthetic-custom"}).status_code, 422)
        self.assertEqual(client.post("/analyze", json={"scenario_id": "synthetic-common", "secret": "DO-NOT-ECHO"}).status_code, 422)
