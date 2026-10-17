# Recovered frontend work — October 17, 2026

This change continues the integrated implementation at main `7e6b406`, after the normal conflict-resolution merge `2306cc6`. The prior work at `15f6d89` remains in history; useful improvements were adapted to the authoritative version 1.0 API rather than restoring the superseded graph-component profile. Only frontend files change relative to main. Backend, ML, privacy, graph and authoritative shared-contract files are unchanged.

## Checks executed

- `node --test frontend/tests/*.test.mjs`: 26 passed, 0 failed, including all 14 current main tests plus 12 focused recovery checks.
- `node --check frontend/src/app.js`: passed.
- `git diff --check`: passed (Git may emit line-ending normalization notices on Windows).
- Real local FastAPI service launched using the root pinned runtime requirements in an isolated Python environment. The browser loaded computed synthetic results through `/health`, `/demo/scenario?name=common|ring`, and `/analyze`, using the current permitted-signal contract.
- Shared scenario displayed 21 signals, 8 high transaction flags, 1 local pattern, 2 combined structural patterns and 1 multi-bank case. Timing came from the actual response and showed its supplied scope, excluding local ML, network and rendering. These are controlled scenario values, not a fraud accuracy benchmark.
- Evidence view showed 21 rows and highlighted the six supporting relationships for the selected common-scenario case.
- Saved normal example showed no multi-bank case; saved local control showed 1 local structure, 1 combined structure and 0 multi-bank cases. Source badges distinguished saved output from actual API responses.
- Local/collaborative projections, bank/entity selection, keyboard entity activation, keyboard tab navigation, all tabs and zoom/reset were checked. Membership details and decimal uncalibrated incident scores were displayed.
- A reconnection to a wrong API path produced HTTP 404 and preserved existing data; it did not load a fixture. Returning to authored demo, stepping to event five (no case) and six (case) worked. Play/pause were retained from the existing implementation.
- Saved computed export downloaded successfully. Inspection confirmed `source=snapshot`, `replay_step=null`, no invented measurement, and recorded backend provenance. Original model tests continue to verify no future authored evidence is exported.
- Presentation viewport 1440 × 900 and mobile 390 × 844 were inspected. Mobile document width was 375; no page-level horizontal overflow. Final reloaded browser error/warning logs were empty. The deliberately failed HTTP path was separately verified before the final reload.
- Desktop/mobile screenshots are in `screenshots/recovered-api-*.png`.

Automated failure tests cover invalid JSON, HTTP failure, response-contract failure, unsafe URLs, raw/secret request fields, malformed scalar representations, timeout/cancellation, empty output, multiple cases, duplicate/missing evidence, mismatched comparison counts and missing timing. Browser checks were against the real local API; no claim is made that every automated failure shape was also driven through browser UI.

## Remaining limits

The local API test does not verify LinuxONE architecture, remote deployment, Secure Execution, attestation or production privacy controls. Saved artifacts are generated from backend code and hash its source; they are not signed attestation, calibrated evaluation data or live inference timing. No competing endpoint schema or backend detector is introduced.

Person 1 can review a normal PR from feat/dashboard to main. The branch already includes main via a regular merge and needs no force push or revert. Review and merge the frontend diff; do not synchronize it back to main's files, which would discard these additions again.
