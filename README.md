# FraudMesh

FraudMesh is an IBM Z Datathon 2026 prototype exploring whether three simulated
banks can identify suspicious cross-bank networks using explicitly permitted
pseudonymous relationship signals, while keeping raw transaction records local.
Our theme is **AI Secured: Innovation Without Exposure**.

## What we're building

- **Local ML scoring:** a trained, reproducible transaction-risk baseline using
  amount and past bank-local behavior. Python 3.12; no third-party dependencies.
- **Privacy and graph analysis:** HMAC entity linking, strict shared-field
  validation, and rule-based cross-bank cycle/fan-in/fan-out detection.
- **Investigator dashboard:** three-bank views, a relationship graph, evidence,
  local-versus-collaborative comparison, and a synthetic replay.

All example data is **synthetic**. Model metrics are controlled-demo results,
not real-world validation. Pseudonymization remains linkable and does not provide
an absolute privacy guarantee.

## Current development branches

| Component | Branch | Details |
|---|---|---|
| ML / dataset | [`feature/ml_baseline`](https://github.com/Roopalgn/IBM-FraudMesh/tree/feature/ml_baseline) | `fraudmesh/ml_model.py`, `scripts/train_ml_baseline.py`, `data/README.md` |
| Privacy / graph | [`feature/privacy-graph`](https://github.com/Roopalgn/IBM-FraudMesh/tree/feature/privacy-graph) | Shared-signal contract, graph detector, API response adapter and tests |
| Dashboard | [`feat/dashboard`](https://github.com/Roopalgn/IBM-FraudMesh/tree/feat/dashboard) | Static Node-served dashboard, mock fixtures and API connection support |

These components are developed separately; a fully integrated API and LinuxONE
deployment are not verified by this branch. Integration must map ML `risk_score`
to graph `local_risk_score`, normalize bank IDs (`BANK_A` versus `bank_a`), and
reconcile the graph response with the frontend contract. The dashboard's bundled
scores and outcomes are fixtures, not live ML results.

## Run the ML baseline

From this branch's repository root:

```bash
python -B -S scripts/train_ml_baseline.py
python -B -S -m unittest discover -s tests -v
```

The scorer accepts raw transaction dictionaries and returns `transaction_id`,
`risk_score`, `risk_level`, and `reason_codes`. History is batch-local: pass
cumulative bank-local records for replay. See [data/README.md](data/README.md)
for the exact schema, measured results, reproduction and limitations.

On the dashboard branch, run `node frontend/server.mjs` and open
`http://localhost:4173` (Node.js 18+). Its API connection expects the team's
separately implemented `/health`, `/demo/scenario`, and `/analyze` endpoints.

The intended deployment target is **IBM LinuxONE, Ubuntu 24.04, s390x, Python
3.12**. Actual server execution, hardware acceleration and confidential execution
must be verified separately before being claimed.
