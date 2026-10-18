# FraudMesh

A working synthetic prototype for the IBM Z Datathon 2026 theme **AI Secured: Innovation Without Exposure**. Three simulated banks score transactions locally, export HMAC entity tokens and coarse signals, and investigate computed cross-bank graph findings.

## Run the integrated application

Python 3.12 is recommended. No Node installation, Docker, pandas, SciPy, or scikit-learn is required to serve the dashboard and API.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Linux / LinuxONE:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The page automatically runs Person 2's 21-transaction shared team scenario through actual replay, privacy transformation, and graph detection. Use the scenario selector and **Run analysis** to compare:

| Scenario | Local structural findings | Multi-bank cases |
| --- | ---: | ---: |
| Shared team scenario (21 transfers) | 1 | 1 |
| Cross-bank ring | 0 | 1 |
| Normal multi-bank chain | 0 | 0 |
| Complete local cycle | 1 | 0 |

These are computed outcomes of small controlled examples, not general accuracy or improvement claims. The shared scenario contains a legitimate payroll burst that triggers a local fan-out finding: this is a documented false positive. Its combined graph has two structural findings (payroll fan and cross-bank cycle); the multi-bank case view shows the cycle. The versioned review policy now combines actual ML scores with supporting structure, timing, and amount-band evidence. No ground-truth label enters detection or prioritization. Use **Local only** to inspect separate bank-visible copies of shared entities. Use the gear button and **Use synthetic demo** for the original authored replay fixture, clearly distinguished from API results.

## Validate

```bash
python -B -m unittest discover -s tests -v
python -B scripts/train_ml_baseline.py
python -B scripts/verify_runtime.py
```

If Node 18+ is installed, also run:

```bash
node --test frontend/tests/*.test.mjs
```

For Node backend-contract tests, activate the virtual environment first, or set `FRAUDMESH_TEST_PYTHON` to its Python executable. The tests also recognize a repository-local `.venv` automatically. There is no frontend build step.

The finalized UI suite contains 41 Node tests alongside 71 Python tests. The repository includes CI for Linux Python 3.12. User-supplied terminal output and screenshots record a clean LinuxONE s390x run of backend commit `3058fb8`, with all 71 Python tests passing and in-process/HTTP benchmarks completed. The [transcribed run evidence](frontend/public/linuxone-run-evidence.json) names its source and measurement scope. Recheck each later release on the VM; a local UI preview does not attest its current host. Runtime reports remain in ignored `output/`.

## Interfaces and implementation

- `GET /health`: actual process architecture/Python and explicit synthetic/security status.
- `GET /demo/scenario?name=common|ring|normal|local`: declares response profile `person3.graph.v2` and returns only a scenario reference.
- `POST /analyze` with that reference performs bank-local ML, HMAC/coarsening, graph detection and ML-informed prioritization on the server.
- `GET /audit/status`: verifies consistency of the local hash-linked analysis journal.
- Legacy programmatic signal requests remain supported by explicitly submitting `shared_signals`; `GET /demo/scenario?profile=dashboard.v1` returns that legacy request. It never accepts raw transaction arrays or a tokenization secret.
- `/docs`: generated API documentation.
- The same Python process serves approved public dashboard assets at `/`.

[Architecture](docs/architecture.md), [authoritative data contract](docs/data_contract.md), [LinuxONE steps](docs/linuxone.md), and [team integration handoff](docs/integration_handoff.md) describe the boundaries and mappings.

The trained local logistic model remains Person 2's standard-library implementation. Its synthetic held-out test results reproduce precision 0.497041, recall 0.700000, and F1 0.581315 on 832 transactions. See [ML provenance and evaluation](data/README.md). The demo calls this actual scorer; graph alerts use structural rules rather than pretending that the model is a graph neural network. ML scores do not change structural candidate extraction, but they now directly affect the versioned review-priority policy. This is hand-weighted fusion over a trained transaction model, not a second trained graph model.

The new dashboard preserves transaction scores on signal rows and leaves node scores unavailable; it does not invent entity fraud probabilities. Graph findings are structural patterns for investigation, not confirmed criminal activity.

## Scope and configuration

This is a **synthetic-only, unauthenticated prototype**. Banks are simulated in one process, not isolated organizations. The local-view switch is presentation, not access control. HMAC tokens and relationships remain linkable. Schema validation checks accepted fields and value formats; raw-row traffic is displayed as not independently audited rather than an invented measured zero. Secure aggregation, confidential execution, remote attestation, production authorization, and hardware acceleration are not implemented or verified.

Keep the server bound to loopback and use an SSH tunnel for LinuxONE demonstrations. Do not open a public unauthenticated service merely to make the dashboard reachable.

Optional configuration:
- `FRAUDMESH_DEMO_SECRET`: synthetic-demo tokenization key. Never send it to the browser. The fallback is explicitly demo-only; changing it changes tokens.
- `FRAUDMESH_ALLOWED_ORIGINS`: comma-separated frontend origins for a separately served dashboard. Default allows localhost/127.0.0.1 port 4173; the unified server needs no CORS setup.

Runtime requirements pin the four directly used application packages. Those versions executed in the recorded LinuxONE run of `3058fb8`. No credentials or environments belong in Git.

## Judge evidence and remaining limits

Person 4's latest work at 15f6d89 is integrated: its 26 original tests plus four real-API bridge tests pass. The proposed person3.graph.v2 scenario-reference contract is now implemented, not just a frontend harness. Saved computed fixtures remain explicitly separate from live API results.

Run `python scripts/evaluate_collaboration.py` for 90 reproducible synthetic scenarios over nine families, including ambiguous legitimate cycles and payroll. In this controlled cohort the ML-only scenario risk screen has precision 0.50/recall 1.00; unfiltered combined structure has precision 0.375/recall 1.00; combined ML-informed triage has precision 0.75/recall 1.00 (10 false-positive scenarios remain). These are scenario-level screening measurements, not transaction-model metrics, ring recall, calibrated probabilities, or real-world accuracy. The fixed policy was not fitted on this cohort. See [critical judge review](docs/judge_review.md) for the protocol and limitations.

Run `python scripts/benchmark_runtime.py` on the actual execution host. On LinuxONE add `--require-s390x`; after starting the service also use `--http-url http://127.0.0.1:8000` to measure loopback requests including journal writes. Reports record architecture, commit, package versions, model/policy versions, and precise measurement scope. A Windows or CI benchmark is never a LinuxONE result. No intrinsic speed advantage or hardware-crypto acceleration is claimed.

Every successful analysis is hash-linked in ignored output/analysis-audit.sqlite3 with counts and input/output digests, not raw rows or graph tokens. It detects inconsistent local edits; truncation or complete rewriting requires an external anchor to detect. This is not an immutable audit service.
