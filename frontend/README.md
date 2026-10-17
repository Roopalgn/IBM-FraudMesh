# Integrated application

The recommended launch command from the repository root is `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` after installing the root requirements. Open http://127.0.0.1:8000. The Python server serves this UI and automatically loads computed API results. Use the scenario selector for the ring, normal negative control, and local positive control. See the root README and docs/data_contract.md for the authoritative integration contract.

The integration adds multi-bank entity memberships, attributed edges, separate bank-local visual projections, live snapshot controls, and a Run analysis button. Node risk is a maximum incident transaction score. Original fixture/replay mode remains available in the settings dialog. The standalone frontend instructions below remain useful for fixture development.

# FraudMesh — Person 4: Dashboard & Demo

A dependency-free investigator dashboard for the team's three-bank experiment. All bundled entities, local flags, risk scores and case outcomes are **synthetic, pre-authored fixtures**. No classifier or fraud detector runs in this frontend.

## Run locally

Requires Node.js 18 or newer. No package installation or build step. On Windows, double-click `START-DASHBOARD.cmd`; it also recognizes the bundled Codex Node runtime on this computer. Keep the terminal open while using the dashboard.

```powershell
cd frontend  # from your repository root
node server.mjs
```

Open http://localhost:4173. From a teammate's checkout, change into its `frontend` directory instead. `npm start` is equivalent. If Node is unavailable, `python -m http.server 4173 --bind 127.0.0.1` from this directory also serves the dashboard. Do not open `index.html` directly: modules and the fixture require HTTP.

## What is implemented

- Three institution cards, entity focus, local finding details and local risk scores.
- SVG graph with keyboard-selectable entities and zoom controls.
- Local-only versus collaborative graph views; six-event replay with play, pause, reset and single step.
- Case evidence with reason codes and relationship table; data-sharing boundary and presentation trail.
- Case export as JSON containing the current mode, visible evidence, provenance and limitations.
- API connection dialog using `GET /health`, `GET /demo/scenario`, `POST /analyze`.
- Strict response validation, escaped backend text, responsive layout and reduced-motion support.

## Handoff to the team lead

The dashboard lives entirely within `frontend/` in the shared repository. No Python/backend files or shared root contracts were modified. Start the API separately and use the gear icon to connect. The **proposed frontend contract** is documented in `docs/data_contract.md`; compare it with your team's actual payload and adapt the boundary in `src/model.js` or the backend response. The repository contained only its root README when this branch was prepared, so compatibility with the eventual backend implementation remains to be confirmed.

Live API loading is a snapshot. Replay is disabled for API data so the UI does not fabricate event timing. Failed connections retain the current displayed data. The demo is always recoverable with **Use synthetic demo**.

API CORS must permit the actual dashboard origin, such as `http://localhost:4173`, and JSON POST requests. The static server binds loopback only. For LinuxONE deployment, the lead can serve these static files through the team's existing web server; change the API base URL in the dialog. An HTTPS dashboard needs an HTTPS API. Do not enter SSH keys or secrets into this frontend.

## Verify

```powershell
node --test tests/model.test.mjs
```

The tests check the actual fixture's cross-bank cycle, local-only fragments, replay evidence timing, raw-field exclusions, current-view exports and invalid backend responses.

Optional integration harness (synthetic response, **not a real detector**):

```powershell
node tests/mock-api.mjs
```

With the dashboard running, open the gear icon, set `http://127.0.0.1:4180` and connect. The header should become **API · synthetic data** and replay controls should disable. Restore the fixture afterward.

See `docs/demo_script.md` for the presentation sequence and `docs/verification.md` for completed checks.

## Scope of privacy claims

The browser receives the full permitted graph. The local-only toggle hides cross-bank edges for comparison; it is not a bank authorization boundary. The export projection excludes unknown fields, but that does not prove the upstream API never transmitted them. The bundled fixture contains no raw transaction records. Backend `raw_rows_shared` and `execution_verified` values are reported claims, not independently audited or attested by the UI. Pseudonyms remain linkable. No production authentication, persistence, secure key exchange or confidential execution is implemented here.

There are no CDN dependencies, remote fonts, analytics or image requests. The fixture runs offline once served. No dataset or third-party asset was downloaded.
