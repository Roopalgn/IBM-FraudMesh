# FraudMesh ML baseline: provisional team contract v2

This component is a trained, bank-local logistic-regression baseline. All data
and metrics are **synthetic controlled-demo measurements**, not real-bank results.
No graph detector, API, dashboard or confidential execution is implemented here.

## Inspected context and ownership

The initial repository contained a one-line README. The shared architecture and
data-contract documents remain absent in fetched remote trees. This version
implements the provisional raw-input/four-field-output contract supplied directly
by the team lead. It supersedes the earlier feature-enriched v1 interface.
No teammates' API, privacy, graph, dashboard or root README files were changed.
Latest requested branch: `feature/ml-baseline`.

## Input contract

`score_transactions(transactions: list[dict]) -> list[dict]`

```python
from fraudmesh.ml_model import score_transactions

result = score_transactions([{
    'transaction_id': 'TX-A-001',
    'institution_id': 'BANK_A',
    'timestamp': '2026-10-17T10:30:00Z',
    'source_entity_token': 'entity_001',
    'destination_entity_token': 'entity_007',
    'amount': 12500.0,
    'transaction_type': 'transfer',
    'channel': 'online',
    'fraud_label': 0,
}])
```

| Field | Required type and handling |
|---|---|
| transaction_id | Nonempty string, unique within a batch; retained in output |
| institution_id | BANK_A, BANK_B or BANK_C; bank-local history partition |
| timestamp | ISO-8601 string with explicit UTC/offset timezone |
| source_entity_token | Nonempty string; local history key, never a model feature |
| destination_entity_token | Nonempty string; distinct-recipient history only |
| amount | Finite, non-negative number; bool and numeric string rejected |
| transaction_type | Nonempty string; validated context, not a model feature |
| channel | Nonempty string; validated context, not a model feature |
| fraud_label | Optional ground truth, ignored by inference regardless of value |

Unknown fields are ignored by public scoring. Caller-provided velocity/fan-out
are **overwritten by derived history**, preventing accidental injected features.
No account age is required or used. Tokens are opaque synthetic identifiers;
the ML module does not implement pseudonymization or authorize shared signals.

`[]` returns `[]`. Invalid rows raise `ValueError` naming the original row index.
A duplicate transaction ID, unknown institution, naive/invalid timestamp, or
missing field rejects the batch. No silent numerical imputation is performed.
Inputs are not mutated and outputs preserve input order.

## Model and past-only feature processing

Trained class-balanced L2 logistic regression, 350 full-batch gradient steps,
implemented entirely with Python standard library. This is a trained model,
not a heuristic fallback. Reason codes are contextual rules, not model attributions.

Model inputs are amount, prior outgoing transaction count in one hour, and
prior distinct-recipient count in one hour. Events sort internally by absolute
time; input order breaks timestamp ties. State is partitioned by institution
and source token. The current event and future events are excluded; an event
exactly one hour old is excluded. `log1p(min(value, 1e12))` then training-only
mean/scale transforms the three features. Labels, token strings, scenario IDs,
transaction IDs, type, channel and account age are not numerical model inputs.

**Batch-local history resets on every call.** For replay, pass the cumulative
bank-local history and select new outputs by transaction_id, or build a stateful
adapter in integration. Scoring one record per call loses velocity context.
All simulated banks use the same model trained on synthetic training records;
this is not federated training or separate privately trained bank models.

## Output contract

Each output has exactly:

```text
transaction_id: string
risk_score: float in [0,1]
risk_level: 'low' | 'medium' | 'high'
reason_codes: list[string]
```

The score is an **uncalibrated model risk score**, not a validated fraud probability.
High: unrounded score >= 0.55 (validation-selected binary decision threshold).
Medium: 0.275 <= score < 0.55. Low: score < 0.275. Medium is a display band only,
not a separately optimized decision. Returned scores round to eight decimals;
category comparisons use the unrounded value.

Reason codes describe observed signals: `elevated_prior_transfer_velocity`
(prior count >= 3), `multiple_prior_recipients` (prior unique count >= 3), and
`large_transfer_amount` (amount >= 5000). Normal transfers can have these flags.
No label, institution, original record or entity token is echoed in outputs.
Transaction IDs may still be sensitive: sharing requires the privacy module's
explicit allowlist and reference/token policy. This module does not emit shared
signals or call the graph detector.

## Dataset provenance, terms and actual schema

Candidate considered: https://github.com/IBM/AML-Data . Its published description
identifies synthetic AML labels and CDLA-Sharing-1.0 data terms distinct from the
repository's Apache-2.0 license. No candidate CSV was downloaded or inspected;
its usable schema/access was not verified here, and it is not our dataset.

Instead, `generate_dataset(seed=20261017)` creates original deterministic
synthetic records. No real customers, external rows or private data are included.
No third-party dataset license is inherited or asserted; repository-wide project
licensing is for the owner to decide. This branch adds no project-wide license.

40 independent synthetic days, 4,160 transfers, three banks. Each day contains
80 background transfers, nine legitimate business transfers, nine transfers in
a three-bank A -> B -> C -> A ring, and six suspicious burst transfers. Source
entities are disjoint across days. Ring endpoint tokens connect consistently.
These are opaque synthetic tokens, not proof of HMAC/privacy implementation.

Actual generated fields: the nine contract fields above plus `scenario_id`
(string, evaluation metadata), `velocity_1h` (int), `fan_out_1h` (int). All generated
values are present/non-null. Amount is float, fraud_label is int, remaining
contract fields are strings. The export profiles actual types/null counts and
canonical-JSON SHA-256. The enriched ledger is local evaluation material, not an
approved collaborative signal payload. Labels and scenarios must remain outside
the inference inputs; the demo exporter explicitly strips them before scoring.

## Reproduce with no third-party dependencies

From repository root, using Python 3.12:

```bash
python -B -S -m unittest discover -s tests -v
python -B -S scripts/train_ml_baseline.py
python -B -S scripts/train_ml_baseline.py --output-dir /tmp/fraudmesh-ml
```

Use a scratch output directory outside the repository (adapt `/tmp` on Windows).
No pip install is required for inference **or training**. The default evaluation
command performs no writes. Optional export writes transactions.json, model.json,
evaluation.json and local_baseline_demo.json. The latter partitions held-out
records into BANK_A/B/C scores with separately marked evaluation-only metrics
and ring truth, enabling the graph teammate to compare the same transaction IDs.
It is not an `/analyze` API schema and must not be transmitted as shared signals.

`--seed 123` evaluates another controlled simulation. `--write-model` intentionally
updates only the embedded coefficient block in fraudmesh/ml_model.py; review its
diff, rerun tests and update documentation before deployment. Without that option,
exported demo scores use the deployed embedded model, while evaluation.json and
model.json describe the freshly trained model. They match for the default seed.
Cross-platform coefficient reproduction permits 1e-10 relative/1e-12 absolute
rounding tolerance; it does not permit materially different models.

## Measured v2 results (supersede v1)

Seed 20261017; chronological whole-day 60/20/20 split with disjoint entities.
Train: 2,496 rows/360 positive; validation: 832/120; test: 832/120. Preprocessing
fits training only. Threshold maximizes validation F1 over 0.05-0.95 in steps of
0.01; the higher threshold breaks ties. Test labels never select the threshold.

| Partition | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Validation | 0.503030 | 0.691667 | 0.582456 | 630 | 82 | 37 | 83 |
| Held-out test | 0.497041 | 0.700000 | 0.581315 | 627 | 85 | 36 | 84 |

Confusion matrix `[[627,85],[36,84]]`: rows actual [0,1], columns predicted [0,1].
An always-normal classifier would appear 85.58% accurate with zero positive
recall, so accuracy alone is misleading. The v1 results used an account-age
feature unavailable in the supplied contract and must not be quoted for v2.

## Audit, compatibility and remaining limitations

14 executed tests pass in a fresh **Python 3.12.2 Windows x86-64 venv without pip**,
with site-packages disabled. Tests cover the supplied example/exact output shape,
empty and malformed batches, all required fields, label/feature injection,
normal/suspicious examples, order/determinism/no mutation, timezone/window
boundaries, independent past-only history reconstruction, three-bank isolation,
ring relationships, chronological splits, regenerated exports and metrics from
the public raw-input scorer matching held-out evaluation.

Only the four owned ML/data files change. Final/staged diffs, whitespace, file
scope, generated artifacts and credential patterns are inspected before commit.
No private datasets, caches, virtual environments or credentials are committed.

No scientific wheels or compiler are needed on s390x. Actual LinuxONE execution
is **not tested in this chat**; team lead should run the same two test/evaluation
commands there. API/graph integration remains for the team lead and graph member.
The provisional field contract is implemented; no unavailable field is invented.

Synthetic train/test share generator assumptions, so metrics do not establish
real-world generalisation, calibrated probabilities, ring-level detection or
collaborative improvement. No fraud ring detector is implemented in this module.
Partitioning is simulated and is not a security boundary against a VM administrator.
