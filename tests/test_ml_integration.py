"""ML-owned replay/ledger/handoff checks; no API, NetworkX or credentials needed."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fraudmesh.ml_demo import generate_demo_ledger
from fraudmesh.ml_model import INPUT_FIELDS, prepare_transactions, score_transactions
from fraudmesh.ml_replay import BankLocalReplay, transform_scored_bank


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.rows = generate_demo_ledger()["transactions"]

    def test_incremental_batch_reset_and_alignment(self):
        expected = score_transactions(self.rows)
        replay = BankLocalReplay()
        actual = [replay.score_new([row])[0] for row in self.rows]
        self.assertEqual(expected, actual)
        self.assertEqual([r["transaction_id"] for r in actual], [r["transaction_id"] for r in self.rows])
        replay.reset()
        self.assertEqual(replay.score_new(self.rows), expected)
        self.assertEqual(replay.score_new([]), [])

    def test_future_and_other_bank_independence(self):
        full = score_transactions(self.rows)
        self.assertEqual(full[:12], score_transactions(self.rows[:12]))
        for bank in ("BANK_A", "BANK_B", "BANK_C"):
            local = [row for row in self.rows if row["institution_id"] == bank]
            replay = BankLocalReplay()
            self.assertEqual(replay.score_new(local), score_transactions(local))
            by_id = {score["transaction_id"]: score for score in full}
            self.assertEqual(score_transactions(local), [by_id[row["transaction_id"]] for row in local])
        # Even identical opaque source strings must not combine bank histories.
        first = dict(self.rows[0], source_entity_token="shared-spelling")
        second = dict(first, transaction_id="second-a", timestamp="2026-10-17T10:10:00Z")
        other = dict(first, transaction_id="other-b", institution_id="BANK_B",
                     timestamp="2026-10-17T10:05:00Z")
        isolated = score_transactions([first, second])
        combined = score_transactions([first, other, second])
        self.assertEqual(isolated, [combined[0], combined[2]])

    def test_late_duplicate_and_invalid_batch_rollback(self):
        replay = BankLocalReplay()
        replay.score_new(self.rows[:3])
        with self.assertRaises(ValueError):
            replay.score_new([self.rows[0]])
        late = dict(self.rows[0], transaction_id="late", timestamp="2026-10-17T09:00:00Z")
        with self.assertRaises(ValueError):
            replay.score_new([late])
        with self.assertRaises(ValueError):
            replay.score_new([self.rows[3], dict(self.rows[4], amount=None)])
        # A failed call did not consume the otherwise valid fourth record.
        self.assertEqual(replay.score_new(self.rows[3:]), score_transactions(self.rows)[3:])

    def test_bank_reset_and_caller_mutation(self):
        replay = BankLocalReplay()
        rows = copy.deepcopy(self.rows[:3])
        replay.score_new(rows)
        rows[0]["amount"] = 1e9
        replay.reset("BANK_A")
        self.assertEqual(replay.score_new([self.rows[0]]), score_transactions([self.rows[0]]))
        with self.assertRaises(ValueError):
            replay.score_new([self.rows[1]])
        with self.assertRaises(ValueError):
            replay.reset("OTHER")

    def test_labels_and_consistent_entity_renaming_do_not_drive_scores(self):
        changed = []
        for row in self.rows:
            changed.append(dict(row, fraud_label=1, scenario_label="always-fraud",
                                source_entity_token="alias-" + row["source_entity_token"],
                                destination_entity_token="alias-" + row["destination_entity_token"]))
        self.assertEqual(score_transactions(self.rows), score_transactions(changed))


class DemoTests(unittest.TestCase):
    def test_reproducibility_structure_and_truth_separation(self):
        demo = generate_demo_ledger()
        self.assertEqual(demo, generate_demo_ledger())
        self.assertNotEqual(demo, generate_demo_ledger(seed=123))
        self.assertEqual(len(demo["transactions"]), 21)
        self.assertEqual({r["institution_id"] for r in demo["transactions"]}, {"BANK_A", "BANK_B", "BANK_C"})
        for row in demo["transactions"]:
            self.assertEqual(set(row), set(INPUT_FIELDS))
            self.assertTrue(row["timestamp"].endswith("Z"))
        ring_ids = {r["transaction_id"] for r in demo["evaluation_truth"] if r["fraud_label"]}
        ring = [r for r in demo["transactions"] if r["transaction_id"] in ring_ids]
        self.assertEqual(len(ring), 6)
        self.assertEqual({r["source_entity_token"] for r in ring}, {r["destination_entity_token"] for r in ring})
        burst_ids = {r["transaction_id"] for r in demo["evaluation_truth"] if r["scenario_label"] == "legitimate_burst"}
        features = prepare_transactions(demo["transactions"])
        self.assertTrue(any(r["velocity_1h"] >= 3 and r["fan_out_1h"] >= 3 for r in features if r["transaction_id"] in burst_ids))
        refs = demo["local_reference_map"]
        self.assertEqual(len({r["signal_id"] for r in refs}), 21)
        self.assertFalse({r["signal_id"] for r in refs} & {r["transaction_id"] for r in refs})

    def test_export_command_without_dependencies(self):
        script = Path(__file__).resolve().parents[1] / "scripts/generate_ml_demo.py"
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.run([sys.executable, "-B", "-S", str(script), "--output-dir", directory],
                                     cwd=directory, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(process.stdout)["transactions"], 21)
            files = Path(directory) / "local_only"
            self.assertEqual(json.loads((files / "transactions.json").read_text()), generate_demo_ledger()["transactions"])
            bank_scores = json.loads((files / "bank_scores.json").read_text())
            self.assertEqual(sum(len(b["scores"]) for b in bank_scores.values()), 21)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        demo = generate_demo_ledger()
        self.rows = [r for r in demo["transactions"] if r["institution_id"] == "BANK_A"]
        self.scores = score_transactions(self.rows)
        self.refs = {r["transaction_id"]: r["signal_id"] for r in demo["local_reference_map"] if r["institution_id"] == "BANK_A"}

    def test_transformer_receives_actual_aligned_scores_and_no_labels(self):
        calls, validated = [], []

        def transformer(**kwargs):
            calls.append(kwargs)
            # A spy callback, NOT an implementation of tokenization/privacy.
            return {"signal_id": kwargs["signal_id"], "local_risk_score": kwargs["local_risk_score"]}

        signals = transform_scored_bank(self.rows, list(reversed(self.scores)), self.refs,
                                        transformer=transformer, validator=lambda rows: validated.extend(rows),
                                        secret=b"unit-test-placeholder")
        self.assertEqual(validated, signals)
        for row, score, args in zip(self.rows, self.scores, calls):
            self.assertEqual(args["local_risk_score"], score["risk_score"])
            self.assertEqual(args["institution_id"], "bank_a")
            self.assertEqual(args["source_entity_id"], row["source_entity_token"])
            self.assertEqual(args["timestamp"], row["timestamp"])
            self.assertFalse(set(args) & {"fraud_label", "scenario_label", "transaction_id"})
            self.assertEqual(args["signal_id"], self.refs[row["transaction_id"]])
        self.assertNotIn("secret", json.dumps(signals))

    def test_reject_bad_handoffs_before_calling_transformer(self):
        def unexpected(**kwargs):
            self.fail("Transformer must not run on invalid handoff")
        cases = [([], self.refs), (self.scores + self.scores[:1], self.refs),
                 (self.scores, {}), (self.scores, {key: key for key in self.refs}),
                 ([dict(self.scores[0], risk_score=float("nan"))] + self.scores[1:], self.refs),
                 ([dict(self.scores[0], risk_score=10 ** 1000)] + self.scores[1:], self.refs)]
        for scores, refs in cases:
            with self.subTest(scores=len(scores)), self.assertRaises(ValueError):
                transform_scored_bank(self.rows, scores, refs, transformer=unexpected,
                                      validator=lambda rows: None, secret=b"unit-test-placeholder")
        with self.assertRaises(ValueError):
            transform_scored_bank(generate_demo_ledger()["transactions"], [], {},
                                  transformer=unexpected, validator=lambda rows: None, secret=b"unit-test-placeholder")

    def test_validator_failure_propagates_and_empty_is_valid(self):
        def reject(signals):
            raise ValueError("privacy rejected")
        with self.assertRaisesRegex(ValueError, "privacy rejected"):
            transform_scored_bank(self.rows, self.scores, self.refs, transformer=lambda **args: {},
                                  validator=reject, secret=b"unit-test-placeholder")
        self.assertEqual(transform_scored_bank([], [], {}, transformer=lambda **args: {},
                                              validator=lambda rows: None, secret=b"unit-test-placeholder"), [])


if __name__ == "__main__":
    unittest.main()
