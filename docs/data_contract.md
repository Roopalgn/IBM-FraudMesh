# Current API profile

The default browser API now implements Person 4's proposed person3.graph.v2 contract. GET /demo/scenario?name=common|ring|normal|local returns response_profile, scenario_id, synthetic, and analysis_request containing only scenario_id. POST /analyze with that reference computes raw component sections on the server. The browser adapts component_metadata, bank_results, graph, comparison, privacy and summary via frontend/src/graph-adapter.js. Saved fixtures remain pinned to Person 3's older unprioritized component output.

API outputs additionally include review_queue, per-finding triage, measurement and audit. Prioritization adds ml_informed_priority evidence without removing candidates; review priority is not a probability. The raw component module remains usable without that policy wrapper. The new flow_hub pattern includes at least three inbound/outbound counterparties and complete supporting signal references.

Local ML scores now affect review prioritization, while structural extraction remains a rule engine. A two-sided hub/cycle structure, mean supporting transaction score, nearby hour buckets and amount-band consistency contribute fixed weights 0.35/0.35/0.20/0.10. Review threshold is 0.75. Candidate severity reflects the review policy in live API output; structural_risk_level retains the original rule label.

Every successful API analysis persists a count/digest journal entry and returns its sequence/hash. The receipt is not external attestation, and the journal can be truncated or fully rewritten by an administrator. Read /audit/status for current local chain consistency. Request limits and generic rejection responses remain unchanged.

The legacy dashboard.v1 profile remains available via GET /demo/scenario?profile=dashboard.v1 and explicit shared_signals POST requests. Its previous contract follows for backwards compatibility.

# Authoritative integrated data contract

This integration contract reconciles the existing ML, graph, and frontend components. The system accepts only synthetic demonstrations. Do not create a second competing API schema in a component.

## Bank-local scoring

`score_transactions(transactions: list[dict]) -> list[dict]` retains Person 2's documented contract in `data/README.md`. Bank IDs are BANK_A, BANK_B, BANK_C. Its source/destination token fields are opaque bank-local history identifiers; the field name alone does not establish pseudonymization. Inference excludes labels. Submit cumulative bank-local history rather than one new row per call, because state resets per invocation.

Outputs are transaction_id, risk_score, risk_level, reason_codes. The bank-local adapter joins by transaction_id and maps risk_score to local_risk_score. Transaction references and exact amounts/times stay outside the collaborative request.

## Permitted shared signal

Every signal contains exactly these fields:

| Field | Required representation |
| --- | --- |
| signal_id | Opaque 1-64 character alphanumeric-leading reference with alphanumeric, dot, underscore, colon, or hyphen characters reference; never reuse a raw transaction ID |
| institution_id | bank_a, bank_b, or bank_c |
| source_entity_token | fm1: followed by 64 lowercase hexadecimal characters |
| destination_entity_token | Same HMAC token syntax |
| timestamp_bucket | Valid canonical UTC hour, such as 2026-10-17T10:00Z |
| amount_bucket | lt_1k, 1k_10k, 10k_50k, or gte_50k |
| local_risk_score | Finite number in [0,1]; booleans and numeric strings rejected |
| channel | transfer, online, card, ach, wire, upi, mobile, atm, or null |

Missing/extra fields, duplicate signal references, nested values in scalar fields, exact-value bucket substitutions, invalid dates, and malformed token syntax are rejected. Syntax validation cannot prove an opaque reference contains no encoded identifying information or that a sender generated a genuine HMAC. Participant authentication is not implemented.

The local transformer requires timezone-aware raw timestamps and finite nonnegative amounts. Matching synthetic entity IDs and the same key produce matching HMACs. Key custody/rotation and graph leakage remain limitations.

## HTTP requests

`GET /health` returns process status, architecture, Python version, synthetic_only=true, and confidential_execution_verified=false.

`GET /demo/scenario?name=common|ring|normal|local` returns `{"synthetic": true, "analysis_request": {...}}`. The request contains scenario_id and shared_signals only. No raw ledger or secret is sent to the browser.

`POST /analyze` accepts exactly:

```json
{"scenario_id": "synthetic-ring", "shared_signals": []}
```

scenario_id may be synthetic-common, synthetic-ring, synthetic-normal, synthetic-local, or synthetic-custom; it is display metadata and never enters detection. It defaults to synthetic-custom. Maximums: 200 signals, 60 unique entity tokens, 128,000 request bytes, 100 structural findings. The graph component rejects empty batches; the API explicitly supports an empty analysis snapshot without invoking it. The service returns 422 for invalid data, 413 for size/entity/pattern-capacity limits, and never echoes rejected payload values in validation errors. Validation does not imply that rejected bytes never reached the service.

## Dashboard response version 1.0

Required fields remain schema_version="1.0", scenario_id, synthetic=true, banks, graph, collaborative_alerts, sharing_summary. Additional API metadata includes comparison, summary, score_semantics, and measurement.

Bank records retain id, name, entity_count, local_alerts, local_ring_count, local_findings. For compatibility, local_ring_count counts local structural patterns (cycles or fan patterns), not exclusively mathematical cycles. local_alerts counts transaction scores at least 0.55; it is a different unit. The UI labels local patterns separately.

Nodes retain id, label, local_risk, bank_id. The integration adds bank_ids, a list of institutions contributing incident relationships. bank_id is the deterministic first membership used for colour only, not exclusive ownership. local_risk is the maximum incident transaction score across the current scope, not entity fraud probability.

Edges retain id, source, target, kind, step, time_bucket, risk_band. The integration adds institution_id and local_risk_score. step is a deterministic display ordering over coarse bucket/reference order, not exact chronology or measured detection timing. The live view disables replay. Node memberships must include the contributing edge bank.

Legacy alerts retain id, title, severity, detected_at_step, node_ids, edge_ids, and reasons (code/title/detail). Supporting references must exist. Structural extraction does not use model scores; the API's subsequent versioned review policy does use them and determines displayed severity. A cross-institution cycle reason refers to an actual detected cycle; supporting_signal_ids and evidence objects come from the exact candidate, rather than unrelated relationships elsewhere in a connected component.

sharing_summary retains raw_rows_shared=null for API outputs (the authored fallback fixture still declares zero), shared_fields, retained_local, execution_verified=false. Null means raw-row traffic has not been independently audited; do not display an invented numeric measurement. The accepted schema excludes raw row fields, which is distinct from network auditing or remote attestation. The API includes validation_scope to explain this distinction. Token/graph linkability remains.

comparison distinguishes local-only structural findings from multi-bank cases and is a controlled visibility comparison. It is not an accuracy percentage. measurement.analysis_ms measures only validation, graph comparison, and response construction; it excludes bank-local ML, HTTP transport, and rendering.

## Frontend local views

Attributed API edges are split into institution-local node views keyed by token plus institution, preserving every bank-contributed signal without joining banks. Local view risk is recomputed from that bank's incident edge scores. The original authored fixture has no edge attribution and retains its legacy presentation. Neither mode implements authentication or access control.

## Current graph-component mapping

Person 3's build_analysis_response returns all structural findings, including local-only candidates. The API display adapter filters cross_institution=true for collaborative_alerts. Comparison uses finding_count and findings_by_institution; counts must not be confused with high transaction-risk flags. The shared 21-transfer scenario has one local payroll fan-out false positive and one cross-bank cycle; there are two combined findings and one multi-bank case.

Graph evidence is an array of objects keyed by code (cycle, fan_in, fan_out, cross_institution_cycle, cross_institution_structure, rapid_propagation). supporting_signal_ids references are mapped to display edge_ids, while institution_ids become display bank_ids. A rapid-propagation reason means supporting UTC hour buckets span at most two hours. It does not establish exact elapsed transaction time.
