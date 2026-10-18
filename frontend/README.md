# FraudMesh investigator dashboard

The dependency-free HTML/CSS/JavaScript frontend includes finalized UI commit `6df9973`, Person 1's API integration, and the replay-safe comparison fix. No install/build step is needed for runtime.

## Final motion and recording preview

The finalized frontend adds locally bundled IBM Plex Sans, luminous bank-colored
evidence, fluid graph/case transitions, and the title **Follow the money. Reveal
the network.** No frontend build or animation dependency is required. Font license
and source notes are in `public/fonts/`.

For the complete API-backed demo, start from the repository root:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8018
```

Open `http://127.0.0.1:8018/?scenario=ring&scope=local`, then select **Reveal the
network**. Windows users with the project virtual environment can run
`frontend/START-PREVIEW.cmd`. The motion toggle pauses transitions and ambient
light; system reduced-motion preferences are honored. Ambient animation also
pauses when hidden/offscreen. Optional `&profile=1` records one local reveal's
frame intervals in the body `data-motion-profile` attribute for developer review;
these measurements are unrelated to inference latency.

The 180-second narration, shot list and caption draft are in `docs/demo/`.
No completed film or narration audio is included. A LinuxONE s390x run of backend
commit `3058fb8` is recorded in `public/linuxone-run-evidence.json`, transcribed
from user-supplied output/screenshots. Recheck this revised UI on the VM before
recording. Confidential execution and hardware acceleration remain unverified.

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

41 tests cover model/adapter/API checks, presentation helpers, frame-reporting validation, replay-safe cross-bank counts and actual API local/cross-bank distinctions.

## API integration

Person 1 has implemented the `person3.graph.v2` scenario-reference envelope in the team API. The same-origin application loads computed common/ring/normal/local scenarios; the browser sends only the scenario reference. Root `docs/data_contract.md` is authoritative. The legacy dashboard.v1 signal interface remains explicitly available for earlier clients. Root `docs/linuxone.md` distinguishes the recorded backend execution from the required new UI smoke check.

For frontend wiring tests only, run a second terminal:

```sh
node tests/mock-api.mjs
```

Connect using `http://127.0.0.1:4180/ring`. The UI explicitly labels this **API test harness**, not a live detector. Test suffixes: `/normal`, `/multiple`, `/empty`, `/optional`, `/malformed`, `/invalid-json`, `/unavailable`, `/unsafe-scenario`. Multiple-case/empty/error variants are test-only mutations, not computed evaluation results. CORS permits only the two local dashboard origins on port 4173.

## Representation and honest scope

One entity can appear in several institutions' contributed relationships. Memberships are preserved and validated against incident edges; they do not establish exclusive ownership. Local mode shows the selected bank's contributed signals. It is not authentication or access control, because the browser receives the permitted response.

Transaction-risk flags, local structural findings and combined cases are separate units. ML flag counts and node scores are unavailable when not supplied. Per-signal scores appear on evidence rows without invented node aggregation. Structural extraction remains rule-based; live API results additionally include a fixed ML-informed review policy that affects recommendation/severity and preserves the original structural label. Priority is not fraud probability. Hour buckets do not establish event-level detection timing.

The service reports validation scope and limitations, not an audited count of raw rows shared/received. Those values stay unavailable. Recorded LinuxONE execution is distinct from Secure Execution, remote attestation, hardware acceleration and production privacy guarantees, which remain unverified. Earlier component verification notes are historical; root docs/linuxone.md records the current deployment handoff.
