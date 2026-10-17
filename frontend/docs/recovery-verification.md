# Recovery and conflict reconciliation — October 17, 2026

The branch first included main through 2306cc6, added recovered work in 318744d, then merged the newer main 3058fb8. That newer main restores the earlier dashboard and adopts person3.graph.v2 as primary. The final resolution preserves those incoming features and all existing fixtures/tests; it adds meaningful work rather than making the branch identical to main. No force push or direct main push is used.

## Current checks

`node --test frontend/tests/*.test.mjs`: **36 passed, 0 failed** (all 30 current-main checks plus 6 new focused recovery checks). Endpoint tests were run outside the Windows sandbox with an isolated Python runtime matching requirements-dev; the in-sandbox FastAPI worker stalled and was stopped. `node --check frontend/src/app.js` and `git diff --check` passed.

New tests verify source hashes, exact equality of all four saved responses to actual current backend computation, structural versus ML review outputs, optional scoped timing validation, provenance-preserving exports and scenario-specific reference requests. Existing tests cover memberships, local controls, evidence, empty/multiple responses, failures, cancellation and authored replay boundaries.

The actual local FastAPI server was restarted after merging new main and the browser loaded the current primary reference API successfully. The result context displayed the returned processing time and exact scope, including bank-local preparation and excluding HTTP/journal/rendering. Saved API common, normal and local controls loaded with a separate source badge; normal had no case, local had a local cycle. Returned live API results preserved the current review-policy outputs. Earlier in this work, the previous main contract was also tested against a real local API, including failed reconnection preserving data, authored step-five/step-six case gating, entity/bank selection, keyboard navigation, zoom, evidence highlighting and JSON export. Those earlier numerical scope claims are superseded by the current returned scope.

Desktop 1440×900 and mobile 390×844 layouts were checked; mobile page width was 375 with no page-level horizontal overflow. Screenshots under screenshots/recovered-api-*.png are refreshed for the final primary API. Final browser error/warning inspection returned no errors before the deliberate failed-path test. The saved-export test includes source provenance and does not claim replay timing.

No backend, ML, privacy, detector, review policy, audit or authoritative shared contract changes are made relative to latest main. LinuxONE architecture, remote deployment and Secure Execution are not established by this local test. Saved source hashes are reproducibility evidence, not remote attestation.

Person 1 can merge a normal PR from feat/dashboard to main after reviewing the retained frontend diff. Do not synchronize the branch back to main's file tree; that would discard the additional work again. GitHub mergeability is checked after the final push.
