# Proposed frontend contract v1.0

This is the integration proposal for Person 4's standalone frontend, not a claim that the other teammates already implemented it. All files are confined to `frontend/` to prevent ownership conflicts. The Python component interfaces remain owned by the lead, ML and privacy teammates.

## HTTP endpoints

| Endpoint | Request | Response |
| --- | --- | --- |
| `GET /health` | None | Any successful JSON object, e.g. `{"status":"ok"}` |
| `GET /demo/scenario` | None | `{"analysis_request": { ...backend-defined demo input... }}` |
| `POST /analyze` | Exact `analysis_request` object from the scenario endpoint, JSON | Analysis object below |

The frontend does not invent a raw transaction schema. The scenario endpoint supplies a reproducible request for the backend. This request stays in memory, is forwarded only to the selected API, and is not included in case exports. For an integrated private workflow, keep bank-local raw data on the backend; return a scenario ID or permitted signals as the request. This UI does not provide bank authentication or authorization.

The connection dialog performs the requests sequentially, with 15-second request timeouts. Redirects and embedded URL credentials are rejected. Credential cookies are omitted. The backend must allow the dashboard's origin with CORS, JSON `Content-Type`, and `GET`, `POST`, `OPTIONS`. Configure a narrow origin allowlist rather than deploying the test harness.

## Analysis response

`public/scenario.json` is the complete, executable reference response. Required top-level fields:

| Field | Type / meaning |
| --- | --- |
| `schema_version` | Exactly `"1.0"` |
| `scenario_id` | Nonempty string |
| `synthetic` | Explicit boolean; never inferred from the API connection |
| `banks` | 1–3 bank summaries |
| `graph` | `{ "nodes": [...], "edges": [...] }` |
| `collaborative_alerts` | Case array; empty when no cases exist |
| `sharing_summary` | Sharing declaration and execution-status report |

Bank: `id`, `name`, integer `entity_count`, integer `local_alerts`, integer `local_ring_count`. Optional `local_findings`: array of `{title, detail}`. Counts and findings describe the **complete scenario**; replay temporarily suppresses card counts until that bank has a visible relationship. They are not timed local detector outputs. Local flags are not equivalent to complete fraud rings.

Node: `id`, `bank_id`, `label`, numeric `local_risk` in `[0,1]`. The local risk is a backend score or fixture value, not a calibrated probability unless evaluated separately. Up to 60 display nodes are supported; use a small case subgraph for a readable investigator view. Raw customer identifiers must not be used as node IDs or labels.

Edge: `id`, `source`, `target`, `kind`, integer `step` in `[1,200]`, `time_bucket`, `risk_band`. Entity references must exist. `step` provides replay order for fixtures; live API analysis is displayed as a complete snapshot with replay disabled. Supported display limit: 200 edges. Coarse time buckets and risk bands are permitted signals, still potentially sensitive.

Alert: `id`, `title`, `severity`, integer `detected_at_step`, `node_ids`, `edge_ids`, `reasons`. Each reason has `code`, `title`, `detail`. Graph references must exist, and no supporting edge may arrive after the alert's detection step. Up to 100 cases are accepted; multiple cases use a case selector. The UI displays a review status, rather than treating an alert as a confirmed fraud verdict.

Sharing summary: nonnegative integer `raw_rows_shared`, string-array `shared_fields`, string-array `retained_local`, explicit boolean `execution_verified`. The fields list describes shared **relationship** fields; pseudonymous node IDs, institution IDs, labels and local risk are also displayed. All claims received from the API are labeled backend-reported. A true execution flag is not remote attestation.

## Display and export boundary

`src/model.js` validates the response and projects known display fields. Invalid data fails visibly without replacing current data. Unknown properties are omitted from normalized display/export output; this is defense in depth, not proof of data minimization at the network boundary. Strings are escaped during HTML/SVG rendering. The raw JSON HTTP response still arrives in the browser and must already satisfy the team's bank-sharing policy.

Local mode shows only same-bank edges and no collaborative alerts. Selecting a bank highlights its entities rather than performing a privileged bank login. The comparison uses reported local ring counts and collaborative case counts; these are different units and the chart explicitly avoids accuracy claims. Precision, recall, false-positive rate and inference latency require the ML/backend teammates' measured evaluation.
