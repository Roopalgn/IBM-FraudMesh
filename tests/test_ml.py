import copy
import math
import unittest

from fraudmesh.ml_model import MODEL, extract_features, score_transactions
from scripts.train_ml_baseline import generate_dataset, run, split_dataset


def transaction(**updates):
    row = {"transaction_id": "T1", "institution_id": "BANK_A", "amount": 100,
           "velocity_1h": 0, "fan_out_1h": 0, "account_age_days": 1000}
    row.update(updates)
    return row


class ScoringTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(score_transactions([]), [])

    def test_invalid_batch_and_rows(self):
        for value in (None, {}, "bad", [None], [3]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                score_transactions(value)

    def test_missing_and_malformed(self):
        for field in ("amount", "velocity_1h", "fan_out_1h", "account_age_days"):
            for value in (None, "5", True, -1, math.nan, math.inf, 10 ** 1000):
                with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(ValueError):
                    score_transactions([transaction(**{field: value})])
            row = transaction()
            del row[field]
            with self.assertRaises(ValueError):
                score_transactions([row])
        with self.assertRaises(ValueError):
            score_transactions([transaction(fan_out_1h=2, velocity_1h=1)])
        with self.assertRaisesRegex(ValueError, r"transactions\[1\]"):
            score_transactions([transaction(), transaction(transaction_id="")])

    def test_normal_and_suspicious(self):
        normal, suspicious = score_transactions([
            transaction(), transaction(transaction_id="T2", amount=2500,
                                       account_age_days=5, velocity_1h=5, fan_out_1h=5)])
        self.assertLess(normal["local_risk_score"], suspicious["local_risk_score"])
        self.assertEqual(normal["prediction"], 0)
        self.assertEqual(suspicious["prediction"], 1)

    def test_determinism_order_and_no_mutation(self):
        rows = [transaction(transaction_id="B"), transaction(transaction_id="A")]
        before = copy.deepcopy(rows)
        self.assertEqual(score_transactions(rows), score_transactions(rows))
        self.assertEqual(rows, before)
        self.assertEqual([r["transaction_id"] for r in score_transactions(rows)], ["B", "A"])

    def test_no_label_or_identifier_leakage(self):
        a = transaction(is_fraud=0, fraud=0, label=0, ground_truth=0)
        b = transaction(is_fraud=1, fraud=1, label=1, ground_truth=1,
                        scenario_id="fraud-ring", source_account_id="criminal")
        self.assertEqual(extract_features(a), extract_features(b))
        self.assertEqual(score_transactions([a]), score_transactions([b]))
        result = score_transactions([b])[0]
        self.assertFalse(set(result) & {"is_fraud", "fraud", "label", "ground_truth",
                                       "source_account_id", "scenario_id"})

    def test_zero_and_large_finite_inputs(self):
        for amount in (0, 1e308):
            score = score_transactions([transaction(amount=amount)])[0]["local_risk_score"]
            self.assertTrue(0 <= score <= 1)


class DatasetTests(unittest.TestCase):
    def test_seed_and_chronology(self):
        rows = generate_dataset(days=10)
        self.assertEqual(rows, generate_dataset(days=10))
        self.assertNotEqual(rows, generate_dataset(seed=2, days=10))
        train, validation, test = split_dataset(rows)
        self.assertLess(max(r["timestamp"] for r in train), min(r["timestamp"] for r in validation))
        self.assertLess(max(r["timestamp"] for r in validation), min(r["timestamp"] for r in test))
        self.assertFalse({r["source_account_id"] for r in train} & {r["source_account_id"] for r in test})
        ring = [r for r in rows if r["scenario_id"] == "d0-ring"]
        self.assertEqual({r["institution_id"] for r in ring}, {"BANK_A", "BANK_B", "BANK_C"})
        self.assertEqual(len(ring), 9)

    def test_features_use_only_prior_bank_history(self):
        rows = generate_dataset(days=2)
        from datetime import datetime, timedelta
        for index, row in enumerate(rows):
            now = datetime.fromisoformat(row["timestamp"])
            prior = [r for r in rows[:index]
                     if r["source_account_id"] == row["source_account_id"]
                     and r["institution_id"] == row["institution_id"]
                     and timedelta(0) <= now - datetime.fromisoformat(r["timestamp"]) < timedelta(hours=1)]
            self.assertEqual(row["velocity_1h"], len(prior))
            self.assertEqual(row["fan_out_1h"], len({r["destination_account_id"] for r in prior}))

    def test_training_reproduces_embedded_model_and_metrics(self):
        _, model, report = run()
        self.assertEqual(model, MODEL)
        metric = report["held_out_test"]
        self.assertEqual(sum(map(sum, metric["confusion_matrix"])), metric["rows"])
        self.assertTrue(0 <= metric["f1"] <= 1)


if __name__ == "__main__":
    unittest.main()
