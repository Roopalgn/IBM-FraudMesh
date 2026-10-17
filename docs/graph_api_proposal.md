# FraudMesh graph component integration proposal

This document is a proposal for Person 1 and Person 4. It does not replace the
authoritative API contract or dashboard model they own.

## Component boundary

The graph component accepts a non-empty list of shared signals. Every signal is
a JSON object with exactly these fields:

| Field | Type | Accepted values |
| --- | --- | --- |
| `signal_id` | string | Opaque reference matching `[A-Za-z0-9][A-Za-z0-9._:-]{0,63}`. It is not a raw transaction ID. |
| `institution_id` | string | `bank_a`, `bank_b`, or `bank_c`. |
| `source_entity_token` | string | `fm1:` followed by 64 lowercase hexadecimal characters. |
| `destination_entity_token` | string | Same canonical token format. |
| `timestamp_bucket` | string | Canonical valid UTC hour: `YYYY-MM-DDTHH:00Z`. |
| `amount_bucket` | string | `lt_1k`, `1k_10k`, `10k_50k`, or `gte_50k`. |
| `local_risk_score` | number | Finite non-boolean value in `[0, 1]`. |
| `channel` | string or null | `transfer`, `card`, `ach`, `wire`, `upi`, or `null`. |

Unknown, missing, nested, raw-data, malformed, duplicate, and empty-batch
inputs are rejected. The bank-local adapter
`transform_bank_local_ledger(local_rows, linkage_secret=...)` is the intended
place to map Person 2's `risk_score` to `local_risk_score`, HMAC entity IDs,
and coarsen local timestamps and amounts. Labels and scenario ground truth stay
in the local fixture and are not emitted.

The collaborative service never receives the linkage secret. Strict syntax
validation cannot authenticate a bank, prove HMAC provenance, or remove all
inference risk from linkable relationships and coarse time data.

## Detection behavior

The detector uses the same structural rules over an individual bank's view and
the combined permitted view:

- A directed cycle has at least three distinct pseudonymous entities.
- A fan-in or fan-out requires at least three distinct counterparties;
  repeated transfers to the same counterparty do not satisfy that rule.
- `rapid_propagation` means all supporting signals span two UTC hour buckets or
  less. It does not claim sub-hour ordering because the input is hour-bucketed.
- A cycle receives `cross_institution_cycle` only when its own supporting edges
  involve at least two banks.

`local_risk_score` is displayed with evidence but does not trigger a graph
finding or change severity. This prototype does not implement model-and-graph
score fusion.

## Controlled demonstration outcome

`three_bank_demo_ledger()` contains three local rows, one at each simulated
bank. After local transformation, each bank sees a single edge and no complete
structural pattern. The combined permitted graph sees one three-node directed
cycle spanning all three banks. The reported units are structural findings, not
transaction-alert counts or a general fraud-performance claim.

## Component response and proposed API mapping

`build_analysis_response(shared_signals)` returns JSON with:

| Component field | Meaning | Proposed final API/dashboard mapping |
| --- | --- | --- |
| `component_metadata` | Schema, validation, and synthetic-scenario metadata | Add as `metadata` if Person 1 accepts it. |
| `bank_results[]` | Bank ID, signal count, local structural findings | Map to `banks[]`. |
| `collaborative_alerts[]` | Candidate-specific structural findings | Map to `collaborative_alerts[]`. |
| `graph.nodes[]` | `id` pseudonym and `institution_ids` membership | Map directly; membership is not single-bank ownership. |
| `graph.edges[]` | `id`, source, target, bank, permitted time/amount buckets, score, channel | Map directly; `id` is the signal reference. |
| `comparison` | Controlled local-only and combined structural findings | Map to `comparison`; retain `comparison_unit`. |
| `privacy` | Verified interface scope and limitations | Map to `sharing_summary`. |
| `summary` | Signal/entity/finding totals and score-usage statement | Map to `summary`. |

Every collaborative alert has `supporting_signal_ids`; these resolve to
`graph.edges[].id`. Its `evidence` is a list of objects, not display-ready
strings. Person 4 can render `code`, associated institutions, linked entities,
and supporting signal references without exposing raw identifiers.

## Example generation

Run this from the repository root after installing `requirements.txt`:

```powershell
python -c "import json; from fraudmesh.integration import build_analysis_response; from fraudmesh.scenarios import three_bank_fraud_ring; print(json.dumps(build_analysis_response(three_bank_fraud_ring()), indent=2, sort_keys=True))"
```

## Known limitations

- HMAC pseudonyms remain linkable and shared relationship graphs can expose
  sensitive information.
- Shared-key custody and rotation are not implemented.
- Three banks are simulated; this is not production organizational isolation.
- Secure Execution, secure aggregation, differential privacy, and remote
  attestation are not implemented or verified here.
- LinuxONE/s390x compatibility has not been verified by this component in this
  workspace. The code uses Python 3.12 and NetworkX only.
