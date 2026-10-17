import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from fraudmesh.ml_model import MODEL, prepare_transactions, score_transactions
from scripts.train_ml_baseline import generate_dataset, run, split_dataset, local_only_demo, models_match, dataset_profile

def transaction(**updates):
    row = dict(transaction_id='TX-A-001', institution_id='BANK_A', timestamp='2026-10-17T10:30:00Z', source_entity_token='entity_001', destination_entity_token='entity_007', amount=12500.0, transaction_type='transfer', channel='online')
    row.update(updates)
    return row

class MLTests(unittest.TestCase):
    def test_contract(self):
        result = score_transactions([transaction(fraud_label=0)])[0]
        self.assertEqual(set(result), {'transaction_id','risk_score','risk_level','reason_codes'})
        self.assertEqual(result['transaction_id'], 'TX-A-001')
        self.assertTrue(0 <= result['risk_score'] <= 1)
        self.assertIn(result['risk_level'], ['low','medium','high'])
        self.assertTrue(all(isinstance(r,str) for r in result['reason_codes']))

    def test_empty(self):
        self.assertEqual(score_transactions([]), [])

    def test_invalid_batches(self):
        for value in (None, {}, 'bad', [None], [3]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                score_transactions(value)

    def test_required_fields(self):
        for field in transaction():
            row = transaction()
            del row[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, r'transactions\[0\]'):
                score_transactions([row])

    def test_invalid_values(self):
        for value in (None, '5', True, -1, float('nan'), float('inf'), 10**1000):
            with self.assertRaises(ValueError):
                score_transactions([transaction(amount=value)])
        for field in set(transaction()) - {'amount'}:
            for value in (None, '', '  ', 12):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    score_transactions([transaction(**{field:value})])
        for timestamp in ('invalid','2026-10-17T10:30:00','2026-99-01T00:00:00Z'):
            with self.assertRaises(ValueError):
                score_transactions([transaction(timestamp=timestamp)])
        with self.assertRaises(ValueError):
            score_transactions([transaction(institution_id='OTHER')])
        with self.assertRaisesRegex(ValueError, r'transactions\[1\]'):
            score_transactions([transaction(), transaction()])

    def test_label_and_feature_injection(self):
        raw = transaction()
        injected = transaction(fraud_label=1,is_fraud=1,label=1,ground_truth=1,scenario_id='ring',velocity_1h=9999,fan_out_1h=9999,account_age_days=0)
        self.assertEqual(score_transactions([raw]), score_transactions([injected]))
        injected['fraud_label'] = 0
        self.assertEqual(score_transactions([raw]), score_transactions([injected]))

    def test_determinism_order_mutation(self):
        rows = [transaction(transaction_id='late',timestamp='2026-10-17T11:00:00Z'), transaction()]
        before = copy.deepcopy(rows)
        self.assertEqual(score_transactions(rows), score_transactions(rows))
        self.assertEqual(rows,before)
        self.assertEqual([r['transaction_id'] for r in score_transactions(rows)], ['late','TX-A-001'])

    def test_timezone_window(self):
        rows = [transaction(transaction_id='late',timestamp='2026-10-17T12:00:00+01:00'),transaction(),transaction(transaction_id='boundary',timestamp='2026-10-17T12:00:00Z')]
        self.assertEqual([r['velocity_1h'] for r in prepare_transactions(rows)],[1,0,0])

    def test_normal_suspicious_and_extremes(self):
        rows = generate_dataset(days=5)
        scored = score_transactions(rows)
        self.assertTrue(any(r['risk_level']=='high' for r,t in zip(scored,rows) if t['fraud_label']))
        self.assertTrue(any(r['risk_level']!='high' for r,t in zip(scored,rows) if not t['fraud_label']))
        for amount in (0,1e308):
            self.assertTrue(0 <= score_transactions([transaction(amount=amount)])[0]['risk_score'] <= 1)

    def test_dataset_split_and_rings(self):
        rows = generate_dataset(days=10)
        self.assertEqual(rows,generate_dataset(days=10))
        self.assertNotEqual(rows,generate_dataset(seed=2,days=10))
        train,val,test = split_dataset(rows)
        self.assertLess(max(r['timestamp'] for r in train), min(r['timestamp'] for r in val))
        self.assertLess(max(r['timestamp'] for r in val), min(r['timestamp'] for r in test))
        self.assertFalse({r['source_entity_token'] for r in train} & {r['source_entity_token'] for r in test})
        ring = [r for r in rows if r['scenario_id']=='d0-ring']
        self.assertEqual(len(ring),9)
        self.assertEqual({r['institution_id'] for r in ring},{'BANK_A','BANK_B','BANK_C'})
        self.assertEqual({r['source_entity_token'] for r in ring},{r['destination_entity_token'] for r in ring})

    def test_past_only_features(self):
        rows = generate_dataset(days=5)
        for i,row in enumerate(rows):
            now = datetime.fromisoformat(row['timestamp'])
            prior = [r for r in rows[:i] if r['source_entity_token']==row['source_entity_token'] and r['institution_id']==row['institution_id'] and timedelta(0)<=now-datetime.fromisoformat(r['timestamp'])<timedelta(hours=1)]
            self.assertEqual(row['velocity_1h'],len(prior))
            self.assertEqual(row['fan_out_1h'],len({r['destination_entity_token'] for r in prior}))

    def test_retraining_and_public_predictions(self):
        rows,model,report = run()
        self.assertTrue(models_match(model,MODEL))
        test = split_dataset(rows)[2]
        matrix = [[0,0],[0,0]]
        for row,result in zip(test,score_transactions(test)):
            matrix[row['fraud_label']][int(result['risk_level']=='high')] += 1
        self.assertEqual(matrix,report['held_out_test']['confusion_matrix'])

    def test_bank_isolation(self):
        rows = generate_dataset(days=5)
        demo = local_only_demo(rows)
        self.assertEqual(set(demo['banks']),{'BANK_A','BANK_B','BANK_C'})
        for bank,payload in demo['banks'].items():
            local = [r for r in rows if r['institution_id']==bank]
            self.assertEqual(payload['scores'],score_transactions(local))
            self.assertEqual(payload,local_only_demo(local)['banks'][bank])

    def test_clean_cli_export_regeneration(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.run([sys.executable,'-B','-S',str(root/'scripts/train_ml_baseline.py'),'--output-dir',directory],cwd=directory,capture_output=True,text=True,check=True)
            report = json.loads(process.stdout)
            self.assertEqual(report,json.loads((Path(directory)/'evaluation.json').read_text()))
            rows = json.loads((Path(directory)/'transactions.json').read_text())
            self.assertEqual(rows,generate_dataset())
            self.assertEqual(report['dataset_profile'],dataset_profile(rows))
            demo = json.loads((Path(directory)/'local_baseline_demo.json').read_text())
            self.assertEqual(sum(b['transaction_count'] for b in demo['banks'].values()),832)

if __name__ == '__main__':
    unittest.main()
