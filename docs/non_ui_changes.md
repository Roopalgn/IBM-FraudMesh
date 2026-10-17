# Non UI readiness changes

The existing Person 4 dashboard is retained. Functional integration edits add the actual scenario-reference API, approved online/mobile/ATM channel compatibility, same-origin startup, live control selection, case focus, and the ML-priority explanation. The adapter still distinguishes saved fixtures, authored replay, harness responses and actual computed API data. No visual redesign is part of this revision.

Backend additions: fraudmesh/triage.py, fraudmesh/evaluation.py, fraudmesh/audit.py, and fraudmesh/analysis.py. Graph extraction adds a supported two-sided hub candidate and excludes self-transfers from fan counts. scripts/evaluate_collaboration.py and scripts/benchmark_runtime.py generate evidence, while tests/test_judge_readiness.py checks score impact, retained negatives, hub references, journal tampering and failed persistence.

The new API default follows person3.graph.v2: GET /demo/scenario returns only a matching scenario_id request and POST /analyze resolves permitted signals within the server. Legacy dashboard.v1 requests remain explicit via the profile query and shared_signals payload. Each success includes a local journal receipt; failures to persist are reported as 503. GET /audit/status reports hash-chain consistency, not protected or externally anchored auditing.

Bank-local keys and ground truth never appear in the scenario-reference request. The simulated banks still share one process and linkage-key assumption. Do not describe this as production federated learning, secure aggregation or confidential execution.
