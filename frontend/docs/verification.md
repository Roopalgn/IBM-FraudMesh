# Verification record

Verified on October 17, 2026 in the local Codex workspace.

## Automated checks

`node --test tests/model.test.mjs`: **10 passed, 0 failed**.

The checks validate that the fixture really forms a directed cycle through all six entities and three banks; local mode contains only three isolated institutional links; future evidence is withheld during replay; raw transaction fields are absent from the fixture relationships; exports follow the selected mode and replay step; unknown raw payload properties are projected out; invalid references, duplicate IDs, scores, counts and early alerts are rejected; provenance and execution status are explicit.

`node --check src/app.js`: passed.

## Browser verification

- Dashboard served successfully from the dependency-free local HTTP server.
- Completed scenario: six relationships, three cross-bank links, one collaborative case.
- Local-only mode: three same-bank relationships, zero collaborative cases.
- Reset and five single steps: five links, zero cases. Sixth step: six links, one case.
- Entity selection displayed its pseudonym, institution and fixture risk score.
- Bank selection displayed its local finding and highlighted institution entities.
- Evidence tab contained six rows; privacy tab displayed shared fields and scope limitations.
- Contract harness: `GET /health`, `GET /demo/scenario`, `POST /analyze` succeeded; header became `API · synthetic data`, disclosure became backend-reported, and replay disabled.
- Invalid API base returning HTTP 404: visible error, current data unchanged.
- Restoring synthetic mode succeeded after API loading and connection failure.
- Export produced a downloaded JSON case file.
- Desktop and 390 × 844 mobile layouts visually inspected; mobile document had no horizontal page overflow. The tab strip can scroll horizontally.
- A graph caption overlap noticed during inspection was corrected by moving the caption into normal document flow.

## Integration still to confirm

The actual teammates' backend, model evaluation, bank privacy implementation and LinuxONE deployment were not present in the shared repository when this branch was prepared. The harness returns the bundled fixture and proves only frontend HTTP wiring. Neither detector accuracy nor confidential execution was tested. The frontend is supplied on its own Git branch for review and integration.
