# ML baseline and synthetic dataset

This workstream implements a bank-local transaction-risk baseline, not the
cross-bank graph detector. All measurements below are **controlled-demo
measurements on synthetic data**, not evidence of real-world generalisation.

## Repository inspection and contract status

At implementation time `README.md` contained only `# IBM-FraudMesh`.
`docs/architecture.md` and `docs/data_contract.md` were missing. They belong to
other workstreams and were not created or overwritten. The function signature
from the handoff is implemented; the field-level interface below is provisional
until integration agrees on the shared contract.

## Dataset decision, provenance, schema and terms

Candidate considered: IBM AML-Data, https://github.com/IBM/AML-Data . Its published
documentation describes synthetic transactions with laundering labels and a
CDLA-Sharing-1.0 data license distinct from its Apache-2.0 repository license.
No candidate CSV was downloaded or inspected for this implementation, so its
exact available schema, usable relationships and download terms were not
verified here. It is not represented as our dataset. To avoid an access/schema
dependency, the implementation uses an original deterministic synthetic generator.
No external rows, customer records, or restricted datasets are included. The
generator's code and generated records are original project material; no
third-party dataset license is asserted or inherited. This branch does not add
or change the repository's project-wide license; the owner decides that policy.

Generator: `scripts/train_ml_baseline.py::generate_dataset(seed=20261017)`.
It produces 4,160 transactions across 40 synthetic days, three simulated banks,
normal payments, legitimate business bursts, and suspicious scenarios. Every day
has a distinct nine-transfer A -> B -> C -> A ring plus six suspicious burst
transfers. Entities are disjoint across days. One source account has a consistent
synthetic age within its day. The bank-partitioned raw ledger is for local use;
it must not be forwarded directly as collaborative shared signals.

| Field | Type / meaning | Prediction use |
|---|---|---|
| transaction_id | Unique synthetic transaction reference | Output association only |
| institution_id | Source simulated bank: BANK_A/B/C | Output association / history partition only |
| destination_institution_id | Destination bank | Graph workstream context, not model input |
| source_account_id | Bank-qualified synthetic source | Local history key, not model input |
| destination_account_id | Bank-qualified synthetic destination | Local distinct-recipient count, not model input |
| timestamp | UTC ISO timestamp | Local history ordering, not model input |
| amount | Non-negative value in a single synthetic currency | Numerical input |
| velocity_1h | Number of source's prior outgoing transfers in the previous hour at that bank | Numerical input |
| fan_out_1h | Distinct destinations among those prior transfers | Numerical input |
| account_age_days | Non-negative synthetic age in days | Numerical input |
| is_fraud | 0 for normal, 1 for seeded suspicious scenario | Training/evaluation target ONLY |
| scenario_id | Synthetic scenario membership | Evaluation/demo metadata ONLY |

History excludes the current payment and all future payments. Ties are processed
in stable generator order. The one-hour window includes events at the current
timestamp already processed, and excludes events exactly one hour old. These
features are **bank-local**, not central graph features. Suspected ring labels do
not mean a bank can necessarily detect the ring from its local features.

## Run / reproduce (from repository root)

Requires Python 3.12 or later; both training and inference use **standard library
only**, with no mandatory NumPy, pandas, scikit-learn or SciPy. No package install
or training is needed to import the scorer. No training occurs at import time.

```bash
python scripts/train_ml_baseline.py
python -m unittest discover -s tests -v
```

The first command regenerates data, fits class-balanced L2 logistic regression
with 350 deterministic full-batch gradient steps, selects the threshold on
validation F1, prints the report, and checks whether it reproduces the embedded
model. It performs no writes unless an option is supplied.

Optional outputs (choose a scratch directory outside the repository):

```bash
python scripts/train_ml_baseline.py --output-dir /tmp/fraudmesh-ml
```

This writes `transactions.json`, `model.json`, and `evaluation.json`. Do not
commit generated ledgers or treat the evaluation JSON as raw API input.
`--seed 123` runs a different controlled simulation.

To intentionally replace the deployed coefficients after retraining:

```bash
python scripts/train_ml_baseline.py --write-model
```

This changes only the marked model block in `fraudmesh/ml_model.py`. Review that
diff and rerun tests; do not use a different seed without updating the documented
results. Tiny floating-point differences across platforms are possible.

## Actual baseline results

Seed: **20261017**. Split: whole-day chronological **60/20/20**, with disjoint
entities across partitions. Days 1-24 train (2,496 rows, 360 positives), days
25-32 validate (832 rows, 120 positives), days 33-40 test (832 rows, 120 positives).
Means/scales are fit on training only. The threshold is chosen on validation only
from 0.05 through 0.95 in 0.01 steps; highest validation F1 wins, with the higher
threshold breaking ties. Selected threshold: **0.69**. Test labels never enter
training or threshold selection.

| Partition | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Validation | 0.841667 | 0.841667 | 0.841667 | 693 | 19 | 19 | 101 |
| Held-out test | 0.683824 | 0.775000 | 0.726563 | 669 | 43 | 27 | 93 |

Held-out confusion matrix: `[[669, 43], [27, 93]]`, with rows = actual [0,1]
and columns = predicted [0,1]. These are local transaction metrics, **not ring
recall, collaboration uplift, calibrated probabilities, or LinuxONE benchmarks**.

## Integration: score_transactions

```python
from fraudmesh.ml_model import score_transactions

rows = [{
    "transaction_id": "T1", "institution_id": "BANK_A",
    "amount": 100.0, "velocity_1h": 0, "fan_out_1h": 0,
    "account_age_days": 1000,
}]
results = score_transactions(rows)
assert results[0]["transaction_id"] == "T1"
assert 0 <= results[0]["local_risk_score"] <= 1
```

Each result contains `transaction_id`, `institution_id`, `local_risk_score`,
`prediction` (0/1), `reason_codes` (list of strings), and `model_version`.
Order is preserved. Inputs are not mutated or echoed. Labels and account IDs are
never copied into results. Transaction IDs may themselves be local-sensitive;
the privacy teammate must select/tokenize allowed fields before sharing results.

All four feature fields are required finite non-negative numbers (bools and
numeric strings are rejected), and `fan_out_1h <= velocity_1h`. Both association
IDs must be non-empty strings. `[]` returns `[]`. A malformed batch raises
`ValueError` with its failing row index; it does not silently impute missing
history. The API layer should translate validation errors to its agreed client
error response. Unknown fields are ignored and never become model features.

Feature transform: `log1p(min(value, 1e12))`, followed by train-only z-scaling and
the embedded learned logistic model. The score is a bounded model risk score,
not a calibrated fraud probability. Reason codes are observed contextual flags,
not causal explanations or exact model contributions; flags can appear on normal
transactions too. Thresholding uses the unrounded score; the returned score is
rounded to eight decimals.

## Tests and limitations

Tests cover empty/malformed batches, missing/nonfinite/negative features,
inconsistent counts, normal/suspicious examples, large inputs, deterministic
order, no input mutation, label/identifier leakage, seeded rings, chronological
splits, independent reconstruction of past-only features, and retraining
reproduction of the embedded model.

The generator intentionally creates learnable patterns (including account age)
and legitimate hard negatives. A model trained and tested on the same generator
can learn its assumptions; results do not establish real-bank effectiveness.
All partitions contain both classes. Fresh-scenario and external-data evaluation
would be needed before generalisation claims. Cross-bank graph detection,
pseudonymization, shared-signal policies, API, dashboard, and LinuxONE deployment
belong to the other workstreams. No confidential execution or server performance
claim is made by this local component.
