# FraudMesh investigator dashboard

The existing dependency-free HTML/CSS/JavaScript frontend, continued on `feat/dashboard` from reviewed commit `71f5866`. No framework migration. Only `frontend/` is changed.

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

Person 1 still owns the final endpoint contract. `docs/data_contract.md` gives the explicit `person3.graph.v2` mapping and the proposed scenario-reference envelope; approval and live integration remain pending. The response is Person 3's actual corrected component response, not the original frontend schema. No compatibility guessing is done.

For frontend wiring tests only, run a second terminal:

```sh
node tests/mock-api.mjs
```

Connect using `http://127.0.0.1:4180/ring`. The UI explicitly labels this **API test harness**, not a live detector. Test suffixes: `/normal`, `/multiple`, `/empty`, `/optional`, `/malformed`, `/invalid-json`, `/unavailable`, `/unsafe-scenario`. Multiple-case/empty/error variants are test-only mutations, not computed evaluation results. CORS permits only the two local dashboard origins on port 4173.

## Representation and honest scope

One entity can appear in several institutions' contributed relationships. Memberships are preserved and validated against incident edges; they do not establish exclusive ownership. Local mode shows the selected bank's contributed signals. It is not authentication or access control, because the browser receives the permitted response.

Transaction-risk flags, local structural findings and combined cases are separate units. ML flag counts and node scores are unavailable when not supplied. Per-signal scores are shown only on evidence rows, without node aggregation or probability claims. They do not drive this graph detector's severity. Hour buckets do not establish event-level detection timing.

The corrected service reports validation scope and limitations, not an audited count of raw rows shared/received. Those values stay unavailable. LinuxONE deployment, Secure Execution, remote attestation and production privacy guarantees remain unverified. See `docs/verification-current.md`, `docs/demo_script.md` and `docs/person1_handoff.md`.
