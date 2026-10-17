# LinuxONE deployment and verification

The integration has been tested locally. These steps must run on your actual LinuxONE allocation before claiming LinuxONE execution. They preserve the earlier ~/fraudmesh directory and its environment.

## First deployment in PuTTY

```bash
git clone --branch main https://github.com/Roopalgn/IBM-FraudMesh.git ~/fraudmesh-integrated
cd ~/fraudmesh-integrated
bash scripts/check_linuxone.sh
```

If ~/fraudmesh-integrated already exists, inspect it first. For an existing clean checkout of main use `git status --short`, then `git pull --ff-only`; do not reset or discard server changes. Do not repeat git clone into an existing directory.

The script creates/reuses a dedicated virtual environment, installs the lean runtime and HTTP test dependency, checks package consistency, runs all Python tests, reproduces ML evaluation, and writes platform/scenario evidence under ignored output/. No sudo, Docker, scientific-library builds, or firewall changes are required. Stop and preserve the error if a command fails.

Start the dashboard and API together:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal connected during the demonstration. Closing the terminal stops this foreground process. If tmux is already available, start a tmux session before launching the server so you can reconnect; a production service manager is outside this prototype.

## Reach the dashboard from Windows

Use PuTTY's SSH tunnel rather than exposing the unauthenticated prototype to the public internet:

1. In the connected PuTTY window, open the window menu and choose Change Settings.
2. Open Connection > SSH > Tunnels.
3. Source port: 8080.
4. Destination: 127.0.0.1:8000.
5. Choose Local, click Add, then Apply.
6. Open http://127.0.0.1:8080 in your Windows browser.

The source port is on your laptop; destination port 8000 is on LinuxONE. Port 8080 avoids conflicting with the local Windows development server. Keep PuTTY connected. No SSH keys or credentials belong in Git or the browser.

If PuTTY cannot apply the forwarding change to an active connection, add the same tunnel to the saved session before reconnecting and restart the server as needed. Confirm success in the browser before the demo.

## Evidence to retain

- `git rev-parse HEAD` for the exact deployed commit.
- `output/test-results.txt` for actual server tests.
- `output/ml-evaluation.json` for the reproduced synthetic benchmark.
- `output/runtime_report.json` for actual OS, Python, architecture, scenario outcomes, and scoped timings.
- A screenshot of the browser connected through the tunnel and PuTTY showing the running service.

Expected architecture is s390x. The report always states confidential_execution_verified=false: it does not test Secure Execution or remote attestation. Do not change that flag just because the process runs on LinuxONE.

## Demo sequence

1. Open the tunneled dashboard. The header should say API / synthetic data.
2. Run Shared team scenario: 21 transfers, 1 local payroll fan-out finding, and 1 multi-bank cycle. Explain that the legitimate payroll finding is a false positive. Use Show all signals to inspect the background; the initial graph focuses the selected case.
3. Run Cross-bank ring: 0 local patterns, 1 multi-bank case.
4. Switch to Local only to see separate institution views; switch back and inspect the supporting evidence.
5. Run Normal activity: 0 local patterns, 0 multi-bank cases.
6. Run Local positive control: 1 local pattern, 0 multi-bank cases. This shows local detection is not disabled.
7. Explain the HMAC/coarse-signal boundary and its linkability limitations.

These are scenario outcomes, not a general production improvement benchmark. Record a backup video and finish the event submission/pitch separately.
