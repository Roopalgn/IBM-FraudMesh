# Common ML/demo handoff for Person 1 and Person 3

Canonical branch: `feature/ml_baseline`. The trained v2 model and its public
four-field scoring interface are unchanged. No backend, dashboard, privacy,
graph or authoritative shared-contract files are edited by this workstream.

## One source of demonstration transactions

```bash
python -B -S scripts/generate_ml_demo.py --output-dir /tmp/fraudmesh-common-demo
```

Use an equivalent writable scratch directory on Windows. No third-party packages
or network access are required. Generator: `fraudmesh.ml_demo.generate_demo_ledger`.
Seed 20261017; 21 chronological UTC events on 17 October 2026:
9 ordinary transfers, 6 legitimate payroll-like burst transfers, 6 transfers
forming a repeated three-bank cycle. Entity IDs are consistent across sender
and recipient roles. The small ledger is a presentation fixture, **not** a
replacement for the held-out evaluation dataset or proof of model performance.

All files are deliberately under `local_only/`:

- `transactions.json`: exactly the eight required local input fields, no labels.
- `evaluation_truth.json`: transaction references, fraud_label and scenario_label.
  Join locally for evaluation only; never feed these values into inference.
- `reference_map.json`: bank-local transaction_id -> independent shared signal_id.
  Never send this mapping to collaborative analysis or the investigator browser.
- `bank_scores.json`: actual incremental ML scores and local records per bank;
  this is a local handoff/debug file, not a shared API response.
- `manifest.json`: seed, provenance, size, model version and local-only warning.

The generator is the single source: Person 3 should transform these transactions;
Person 4 should use the integrated API's outputs from these same transactions,
instead of maintaining a second hand-authored set of scores/case outcomes.
This proposal does not change either teammate's authoritative schema.

## Replay without losing history

```python
from fraudmesh.ml_demo import generate_demo_ledger
from fraudmesh.ml_replay import BankLocalReplay

demo = generate_demo_ledger()
replay = BankLocalReplay()
for transaction in demo['transactions']:
    new_score = replay.score_new([transaction])[0]
    # Join by transaction_id locally; hand off to the bank-local privacy step.
replay.reset()                  # restart all banks
replay.reset('BANK_A')          # or clear one bank only
```

`score_new` returns only requested new results in request order. State is grouped
by bank; the existing scorer groups features by bank and source. It delegates to
`score_transactions` on cumulative bank history, so there is no duplicate feature
implementation. Labels and unknown metadata are not retained in replay state.
Invalid batches have no state effect. Duplicate transaction references raise.
Records cannot be earlier than a bank's accepted timestamp: reset/replay on late
events rather than retroactively changing emitted results. Equal-time events use
arrival/input order. A fresh/reset adapter deterministically reproduces the run.

State is in-memory, single-process, not thread-safe, durable or tenant-authorized.
Do not put one global adapter behind concurrent API clients without a bank/session
scope and synchronization strategy. It rescans cumulative history, intentionally
adequate for 21 events, not an optimized production stream.

## Exact mapping to Person 3's reviewed transformer

Reviewed against `origin/feature/privacy-graph` at `cb355b8`.

| ML/local value | Bank-local transformer keyword | Shared result |
|---|---|---|
| BANK_A/BANK_B/BANK_C | institution_id = bank_a/bank_b/bank_c | Lowercase bank ID |
| score.risk_score | local_risk_score | Actual ML score, unchanged |
| source_entity_token | source_entity_id | Transformer applies HMAC |
| destination_entity_token | destination_entity_id | Transformer applies HMAC |
| timestamp | timestamp | Transformer returns timestamp_bucket |
| amount | amount | Transformer returns amount_bucket |
| channel | channel | Permitted channel |
| Local reference map value | signal_id | Independent shared reference |
| transaction_id, fraud/scenario labels | NOT passed | NOT shared |

Despite their names, the input `*_entity_token` strings are opaque synthetic
IDs, **not verified HMAC tokens**. Treat them as local canonical IDs for this
fixture. Person 3's transformer produces the real `fm1:` HMAC outputs. If a future
API supplies already-HMACed inputs, Person 1 and Person 3 must agree how to avoid
double-tokenization; this adapter makes no silent change to that contract.

Do not use `transaction_id` as `signal_id`. The independent references are seeded
demo UUID-like strings, not a formal privacy guarantee or a production key scheme.
Keep their mapping local; sender/recipient identity consistency lets the privacy
transformer produce linkable relationships with the same demo-session secret.

After Person 3's code is integrated, this is the bank-local call pattern:

```python
from fraudmesh.ml_demo import generate_demo_ledger
from fraudmesh.ml_model import score_transactions
from fraudmesh.ml_replay import transform_scored_bank
from fraudmesh.privacy import create_shared_signal, validate_shared_signals
import secrets

demo = generate_demo_ledger()
session_secret = secrets.token_bytes(32)  # demo only; never log/export/commit
shared_signals = []
for bank in ('BANK_A', 'BANK_B', 'BANK_C'):
    local = [row for row in demo['transactions'] if row['institution_id'] == bank]
    scores = score_transactions(local)
    references = {row['transaction_id']: row['signal_id']
                  for row in demo['local_reference_map'] if row['institution_id'] == bank}
    shared_signals.extend(transform_scored_bank(
        local, scores, references,
        transformer=create_shared_signal, validator=validate_shared_signals,
        secret=session_secret,
    ))
# Only shared_signals goes to the collaborative engine / endpoint.
# Do not send local, demo, scores-by-bank files, secret, or reference mappings.
```

`transform_scored_bank` accepts one bank at a time, joins scores by transaction_id
regardless of score ordering, validates one-to-one alignment and references,
calls Person 3's transformer, then calls Person 3's validator before returning.
Exact time, amount and local IDs exist only in the simulated bank's transformer
arguments. This module does not implement or duplicate HMAC, coarse buckets,
shared-signal policy or graph detection. Bank isolation is simulated code scoping,
not protection against the VM administrator.

## Executed checks and boundaries

```bash
python -B -S -m unittest discover -s tests -v
python -B -S scripts/train_ml_baseline.py
python -B -S scripts/generate_ml_demo.py --output-dir /tmp/fraudmesh-common-demo
```

24 tests pass in the existing clean Python 3.12.2 Windows venv without pip and
with site packages disabled. Tests cover original scoring plus replay/batch
equivalence, prefix/future independence, bank isolation, full/bank reset,
rollback, ordering, stable ledger/CLI export, separated truth, aligned handoff,
no label in transformer inputs, and propagated privacy-validator rejection.

Additional scratch integration smoke test executed against the actual reviewed
Person 3 `privacy.py`: all 21 real transformer outputs validated with exactly
signal_id, institution_id, source_entity_token, destination_entity_token,
timestamp_bucket, amount_bucket, local_risk_score and channel. Original local
IDs, exact amounts/times, labels and secret were absent from the output. HMAC
ring endpoints matched across banks. No teammate implementation was modified.

Graph detection was **not run** here: NetworkX is not installed in the local
runtime. That optional dependency remains Person 3's graph workstream requirement,
not an ML training/inference dependency. Dashboard/API integration and LinuxONE
s390x execution were **not tested**. No collaboration uplift is reported.

Training evaluation was rerun: 4,160 rows, seed 20261017, whole-day 60/20/20 split,
2,496 train/832 validation/832 test, 360/120/120 positive labels. Features: amount,
prior-hour outgoing count and distinct destinations. Training-only scaling;
threshold 0.55 maximizes validation F1 over 0.05..0.95. Held-out precision
0.4970414201, recall 0.7000000000, F1 0.5813148789, confusion matrix
[[627,85],[36,84]]. Regenerated model matches embedded v2 within documented
floating-point tolerance. Transaction classification is not ring detection;
synthetic performance is not real-world validation; scores are uncalibrated;
reason codes are contextual flags; shared model weights are not federated learning.
