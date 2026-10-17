# Reviewed team integration

Person 2 feature/ml_baseline at 6e8187d: all 24 standalone tests reproduced without third-party packages. Person 3 feature/privacy-graph at 34822ed: all 18 standalone tests reproduced. Person 4 feat/dashboard now contains 15f6d89; its 26 standalone tests passed. The updated adapter, client, computed fixtures and documentation are included through a normal merge preserving branch ancestry.

The combined application uses Person 2's actual 21-transfer ledger and request-local BankLocalReplay, calls the real privacy transformer, and returns Person 3's candidate-specific findings/evidence through the accepted person3.graph.v2 scenario-reference contract. The integrated suite passes 71 Python tests and 30 Node tests. Main is updated only after the integration checks and CI pass. LinuxONE execution remains a separate server-side verification.

Resolved integration differences:

- Approved the ML demo's coarse online channel in the shared allowlist.
- Adapted finding_count/findings_by_institution, supporting_signal_ids, structured evidence, and candidate-specific cross_institution flags.
- Preserved API empty snapshots while retaining the graph component's nonempty-batch contract.
- Kept timezone-aware local transformation and rejection of oversized numeric values.
- Bounded pattern enumeration at 100 findings; excessive graphs are rejected without partial outputs.
- Defaulted the UI to the shared scenario and added a labelled selected-case subgraph with a Show all signals control.
- Displayed raw-row traffic as not audited rather than claiming a measured zero.

The shared ledger includes a legitimate payroll burst that triggers one local fan-out finding, a documented structural false positive. The combined graph retains that fan and one cross-bank cycle. The new versioned ML-informed policy recommends the cycle for review and retains the fan without recommending it. Labels stay in local evaluation material and never enter inference or shared-signal requests. See judge_review.md for the 90-scenario evaluation and its remaining false positives.

Teammates should fetch main and reconcile subsequent feature changes against the root authoritative docs/data_contract.md. Preserve original component commits. No confidential execution, production organizational isolation, secure aggregation, or real-world model performance is claimed.
