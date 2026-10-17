# FraudMesh investigator dashboard

The dependency-free HTML/CSS/JavaScript frontend includes Person 4's `feat/dashboard` at `15f6d89` and Person 1's live API integration. No install/build step is needed for runtime.

## Run from a teammate's checkout

Requires Node.js 18 or newer; no npm install or build is needed.

```sh
cd frontend
node server.mjs
```

Open http://localhost:4173 and keep the terminal running. `npm start` is equivalent. Windows users can double-click `START-DASHBOARD.cmd`; its Codex-runtime fallback is optional and machine-specific, while `node server.mjs` is portable. Alternatively serve this directory with `python -m http.server 4173 --bind 127.0.0.1`. Direct `file://` opening is unsupported.

## Choose a result source

- **Authored synthetic replay:** existing six-event fallback. Outcomes are pre-authored. Play, pause, reset, step and evidence-safe exports remain available.
- **Computed synthetic ring:** saved output from Person 3's unchanged corrected code at `34822ed09e167a810abc29cdde5104b569e84b72`. Three signals, three entities, zero local structural findings and one combined cycle.
- **Computed unrelated activity:** three unrelated signals, six entities, no structural findings.
- **Computed single-bank cycle:** all three cycle edges contributed by Bank A. One local finding and one combined finding, demonstrating that local detection is not forced to zero.
- **API:** configurable gear-dialog connection. Snapshot only; no unsupported replay. Synthetic provenance remains visible. Errors retain previous data and never silently load the fallback.

Computed fixture provenance and source hashes are in `public/integration/*.json`. `scripts/generate-integration-fixtures.py` runs the pinned graph code in a temporary directory; it does not modify that code or export raw local ledgers or linkage keys. Optional regeneration from the repository root: install NetworkX 3.4.2 in a separate Python environment, fetch the graph branch, then run `python frontend/scripts/generate-integration-fixtures.py --repo .`.

## Tests

From `frontend/`:

```sh
node --test tests/*.test.mjs
node --check src/app.js
```

26 tests passed: the original 10 plus response adaptation, memberships, corrected local structures, evidence references, provenance, privacy limits, exports, request safety, errors, timeouts and cancellation.

## API integration

Person 1 has implemented the `person3.graph.v2` scenario-reference envelope in the team API. The same-origin application loads computed common/ring/normal/local scenarios; the browser sends only the scenario reference. Root `docs/data_contract.md` is authoritative. The legacy dashboard.v1 signal interface remains explicitly available for earlier clients. See root `docs/integration_handoff.md` for integration verification; LinuxONE execution remains unverified.

For frontend wiring tests only, run a second terminal:

```sh
node tests/mock-api.mjs
```

Connect using `http://127.0.0.1:4180/ring`. The UI explicitly labels this **API test harness**, not a live detector. Test suffixes: `/normal`, `/multiple`, `/empty`, `/optional`, `/malformed`, `/invalid-json`, `/unavailable`, `/unsafe-scenario`. Multiple-case/empty/error variants are test-only mutations, not computed evaluation results. CORS permits only the two local dashboard origins on port 4173.

## Representation and honest scope

One entity can appear in several institutions' contributed relationships. Memberships are preserved and validated against incident edges; they do not establish exclusive ownership. Local mode shows the selected bank's contributed signals. It is not authentication or access control, because the browser receives the permitted response.

Transaction-risk flags, local structural findings and combined cases are separate units. ML flag counts and node scores are unavailable when not supplied. Per-signal scores appear on evidence rows without invented node aggregation. Structural extraction remains rule-based; live API results additionally include a fixed ML-informed review policy that affects recommendation/severity and preserves the original structural label. Priority is not fraud probability. Hour buckets do not establish event-level detection timing.

The corrected service reports validation scope and limitations, not an audited count of raw rows shared/received. Those values stay unavailable. LinuxONE deployment, Secure Execution, remote attestation and production privacy guarantees remain unverified. See `docs/verification-current.md`, `docs/demo_script.md` and `docs/person1_handoff.md`.


## Retained reliability work after the latest main merge

The current branch preserves main's primary `person3.graph.v2` reference API, every existing fixture/test, and the ML-informed review policy. No backend or shared-contract code is changed by this frontend diff.

The Result source selector adds **Saved API shared/ring/normal/local** examples. These are regenerated using the unchanged current `fraudmesh.analysis.analyze_signals` function, not the older component-only fixtures. Each records a backend revision and source hashes. Their badge says **Saved API result · synthetic**, and they never claim a live request or measured detection timing. Regenerate from the root with `python frontend/scripts/generate-snapshots.py` after installing root requirements.

Live API results now preserve and display the actual `measurement.analysis_ms` and its supplied scope; missing timing stays unavailable. In the current service, scenario-reference timing includes bank-local preparation but excludes HTTP, journal write and rendering. The UI uses the returned scope rather than assuming a fixed definition.

Request generation guards prevent old responses or fixture loads replacing a newer user selection. Closing settings cancels safely without reopening an error dialog. New tests compare saved results against current real backend computation and validate their source hashes.

Integrated launch from the repository root: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, then open http://127.0.0.1:8000. Existing standalone Node launch instructions remain valid. Full frontend checks: `node --test frontend/tests/*.test.mjs` (Python with requirements-dev installed is needed by endpoint tests); set FRAUDMESH_TEST_PYTHON if using a separate environment. Current result: **36 passed**. See docs/recovery-verification.md.
