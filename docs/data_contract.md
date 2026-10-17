# FraudMesh shared-signal data contract

## Boundary

Each simulated bank retains its transaction rows, direct customer and account identifiers, exact monetary values, exact timestamps, and fraud labels. The collaborative graph service accepts only the allowlisted record below. It rejects extra fields instead of silently discarding them, so an integration error cannot quietly broaden the privacy boundary.

This is a controlled synthetic-data prototype. Deterministic HMAC tokens are pseudonymous and linkable; they are not anonymous, and they do not provide a formal privacy guarantee. A participant holding the shared secret and a candidate identifier can recreate a token. Real deployments require key custody, rotation, access controls, participant agreements, retention rules, and a separate assessment of graph-inference risk.

## Allowed record

| Field | Type | Purpose | Constraint |
| --- | --- | --- | --- |
| `signal_id` | string | Unique reference for a permitted signal | No raw transaction ID |
| `institution_id` | string | Identifies the simulated contributing bank | `bank_a`, `bank_b`, or `bank_c` in the demo |
| `source_entity_token` | string | HMAC-SHA-256 pseudonym for the source entity | `fm1:` versioned token only |
| `destination_entity_token` | string | HMAC-SHA-256 pseudonym for the destination entity | `fm1:` versioned token only |
| `timestamp_bucket` | string | UTC hour for limited velocity analysis | Exact timestamp remains local |
| `amount_bucket` | string | Coarse value band | Exact amount remains local |
| `local_risk_score` | number | Locally computed score in `[0, 1]` | No label used at inference |
| `channel` | string or null | Optional coarse transaction context | Must be explicitly agreed |

## Explicitly prohibited

The service must reject raw transaction rows; customer, account, source and destination IDs; exact timestamps; exact amounts; transaction IDs; and fraud or AML labels. Ground truth is reserved for evaluation and does not enter live detection.

## Entity linking

Banks call `pseudonymize_identifier(identifier, secret)` before signal creation. The shared secret is demo-only and never belongs in a production repository or collaborative request. Matching synthetic identifiers with the same secret produce the same `fm1:` token, allowing relationship edges to be linked without exposing the original identifier.

## Detector contract

`detect_fraud_rings(shared_signals: list[dict]) -> dict` validates all signals, rejects duplicate signal references, creates a directed NetworkX graph, and returns alerts only for multi-bank connected components containing at least three edges and a structural pattern such as a cycle, fan-in, or fan-out. Alert evidence includes the contributing signal references, involved institutions, pseudonymous nodes, time buckets, and rule-based reason codes. It does not claim that every alert is fraud.

`compare_local_and_collaborative(shared_signals: list[dict]) -> dict` runs the same detector once per bank and once over the combined allowlisted signals. Its output is a controlled synthetic comparison for the dashboard and demo; it must not be presented as a generalization or production performance benchmark.

