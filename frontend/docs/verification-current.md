# Current verification — October 17, 2026

Person 4's component verification below applies to `15f6d89`. Person 1 has since implemented and browser-verified the team API, including common/normal/local controls, with 71 Python and 30 Node tests passing. Pending API statements below are historical; LinuxONE/security deployment remains unverified. Root `docs/integration_handoff.md` records the current integrated status.

## Automated

From frontend: `node --test tests/*.test.mjs`: **26 passed, 0 failed**. Original 10 tests retained. Added actual corrected-response mapping, memberships, supporting references, counts, empty/multiple cases, local-control positive case, unavailable values, privacy scope, local exports, safe scenario request, HTTP/JSON/contract errors, timeout and cancellation checks.

`node --check src/app.js`: passed. `git diff --check`: passed.

## Actual computation used

Generated with unchanged Person 3 Python source at `34822ed09e167a810abc29cdde5104b569e84b72`, NetworkX 3.4.2, using the tracked generator. Ring: three entities, three signals, zero local structures, one combined case. Unrelated activity: six entities, three signals, zero cases. Single-bank cycle control: three entities, three signals, one local structure and one combined case. No ML training, transformation or detection source was edited.

## Browser checks actually executed

Default authored fixture, bank/entity selection, keyboard entity activation, keyboard tab navigation, graph zoom/reset, local and collaborative views, all four tabs, evidence highlighting, replay reset/step/play/pause, final-evidence case visibility, privacy disclosures, partial-replay JSON export and explicit fixture recovery were checked.

The corrected response was then checked for generated ring, per-edge hour/amount/score evidence, shared memberships, valid local-control case, and API test-harness loading through health → scenario → analyze. Multiple-case selection, empty output, missing optional information, invalid graph references, invalid JSON, HTTP 503, forbidden raw scenario input and failed reconnection preserving a nonempty graph were tested through the updated HTTP harness. It is explicitly labeled API test harness and does not run a live detector. Synthetic API snapshots disable replay.

Presentation viewport: 1440 × 900. Mobile: 390 × 844, document width 375; no horizontal page overflow. Evidence tables/tab strip can scroll within their panels. Screenshots in screenshots/ capture the corrected generated result. Browser error/warning log inspection returned an empty list. The earlier browser sequence also verified unrelated-activity no-case behavior and a partial authored export; its downloaded JSON contained exactly one edge and no cases at replay step one.

## Limits

Actual team API endpoint shapes/approval and reachability remain unverified because Person 1's endpoint work was not available. The proposed scenario-reference envelope must be approved before production integration. LinuxONE deployment, Secure Execution, remote attestation, detector accuracy, calibrated probabilities and end-to-end inference latency were not verified. Snapshots are not incrementally measured detection runs. The corrected response no longer asserts audited raw-row counts; the UI shows those as unavailable.
