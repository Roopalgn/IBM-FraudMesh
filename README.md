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

These are computed outcomes of small controlled examples, not general accuracy or improvement claims. The shared scenario contains a legitimate payroll burst that triggers a local fan-out finding: this is a documented false positive. Its combined graph has two structural findings (payroll fan and cross-bank cycle); the multi-bank case view shows the cycle. No ground-truth label enters detection. Use **Local only** to inspect separate bank-visible copies of shared entities. Use the gear button and **Use synthetic demo** for the original authored replay fixture, clearly distinguished from API results.

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

The integration was verified locally on Windows Python 3.12 with 63 Python tests and 14 Node tests. The repository includes CI for Linux Python 3.12; CI must pass on the merged head; actual LinuxONE execution must be checked separately. Runtime evidence is written to ignored `output/runtime_report.json` and includes the platform where it was actually run.

## Interfaces and implementation

- `GET /health`: actual process architecture/Python and explicit synthetic/security status.
- `GET /demo/scenario?name=common|ring|normal|local`: prepares the synthetic ledger within simulated bank stages and returns only an allowlisted analysis request.
- `POST /analyze`: accepts `shared_signals` and a documented synthetic scenario ID. It never accepts raw transaction arrays or a tokenization secret.
- `/docs`: generated API documentation.
- The same Python process serves approved public dashboard assets at `/`.

[Architecture](docs/architecture.md), [authoritative data contract](docs/data_contract.md), [LinuxONE steps](docs/linuxone.md), and [team integration handoff](docs/integration_handoff.md) describe the boundaries and mappings.

The trained local logistic model remains Person 2's standard-library implementation. Its synthetic held-out test results reproduce precision 0.497041, recall 0.700000, and F1 0.581315 on 832 transactions. See [ML provenance and evaluation](data/README.md). The demo calls this actual scorer; graph alerts use structural rules rather than pretending that the model is a graph neural network. ML scores supply contextual evidence, not the structural alert threshold.

Node display scores are the maximum incident transaction scores within the displayed scope. They are not calibrated entity fraud probabilities. Graph findings are structural patterns for investigation, not confirmed criminal activity.

## Scope and configuration

This is a **synthetic-only, unauthenticated prototype**. Banks are simulated in one process, not isolated organizations. The local-view switch is presentation, not access control. HMAC tokens and relationships remain linkable. Schema validation checks accepted fields and value formats; raw-row traffic is displayed as not independently audited rather than an invented measured zero. Secure aggregation, confidential execution, remote attestation, production authorization, and hardware acceleration are not implemented or verified.

Keep the server bound to loopback and use an SSH tunnel for LinuxONE demonstrations. Do not open a public unauthenticated service merely to make the dashboard reachable.

Optional configuration:
- `FRAUDMESH_DEMO_SECRET`: synthetic-demo tokenization key. Never send it to the browser. The fallback is explicitly demo-only; changing it changes tokens.
- `FRAUDMESH_ALLOWED_ORIGINS`: comma-separated frontend origins for a separately served dashboard. Default allows localhost/127.0.0.1 port 4173; the unified server needs no CORS setup.

Runtime requirements pin the four directly used application packages. They match the package versions observed in the supplied LinuxONE installation screenshot, but actual execution remains to be verified on that server. No credentials or environments belong in Git.
