# Team integration handoff

Integration branch: codex/integration. Source baselines: ML 3b49614, graph cb355b8, dashboard 71f5866; main README baseline 028bd8a. The ML and graph histories were merged. The reverted dashboard was deliberately restored from its branch. Component branches were not modified.

## Person 1 work completed

- Integrated FastAPI endpoints and public static frontend serving.
- One shared deterministic synthetic ledger with real ML inference and bank-local signal preparation.
- Explicit uppercase/lowercase institution mapping and opaque shared references.
- API/display adaptation with multi-bank node memberships.
- Fair local structural comparison and local positive control.
- Content validation and corrected hour-bucket timing evidence.
- Runtime/deployment scripts, documentation, gitignore, CI and regression coverage.

## Coordinate before further teammate changes

Person 2: ml_model.py and the training implementation are preserved. demo.py is the integration-owned common small scenario and bank-local preparation adapter. Evolve it together with the lead rather than adding a competing end-to-end scenario. Preserve cumulative per-bank history and label exclusion.

Person 3: integration fixes modify privacy.py, graph_engine.py, and add a scope explanation to integration.py. Review these changes before replacing them with your branch work. Core fixes include strict signal values, canonical tokens/buckets, finite scores, distinct-neighbour fan evidence, elapsed hour-bucket span, deterministic construction, and min_institutions=1 in local comparisons. Extend tests instead of reverting the corrected behaviour. Node memberships denote observed contributing banks, not account ownership.

Person 4: frontend/index.html, src/model.js, src/app.js, styles.css have focused integration edits. Review the authoritative root docs/data_contract.md. API edges add institution_id/local_risk_score; nodes add bank_ids. Local mode splits entity views by institution. The Python server serves assets; Node remains optional for standalone frontend development/tests. The original fixture/replay is preserved. Auto-connect selects the same-origin API when available. Do not overwrite these changes with the old fixture-only branch.

## Remaining work

Run actual LinuxONE verification and inspect CI after push. Reconcile newer teammate commits through reviewed merges. Prepare/rehearse the pitch, capture evidence and a backup video, confirm the official deadline and submit. Production authentication, audit persistence, secure key management, and confidential execution are not implemented.
