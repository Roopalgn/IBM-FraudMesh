# Reviewed team integration

Person 2 feature/ml_baseline at 6e8187d: all 24 standalone tests reproduced without third-party packages. Person 3 feature/privacy-graph at 34822ed: all 18 standalone tests reproduced. Person 4 feat/dashboard remains at 71f5866 with all 10 standalone tests passing; no newer frontend push was present. Its authored fixture UI is complete within its stated scope; live integration is implemented on the integration branch.

The combined application uses Person 2's actual 21-transfer ledger and request-local BankLocalReplay, calls the real privacy transformer, and adapts Person 3's candidate-specific findings/evidence to the existing display. The integrated suite passes 63 Python tests and 14 Node tests. Main is updated only after the integration checks and CI pass. LinuxONE execution remains a separate server-side verification.

Resolved integration differences:

- Approved the ML demo's coarse online channel in the shared allowlist.
- Adapted finding_count/findings_by_institution, supporting_signal_ids, structured evidence, and candidate-specific cross_institution flags.
- Preserved API empty snapshots while retaining the graph component's nonempty-batch contract.
- Kept timezone-aware local transformation and rejection of oversized numeric values.
- Bounded pattern enumeration at 100 findings; excessive graphs are rejected without partial outputs.
- Defaulted the UI to the shared scenario and added a labelled selected-case subgraph with a Show all signals control.
- Displayed raw-row traffic as not audited rather than claiming a measured zero.

The shared ledger includes a legitimate payroll burst that triggers one local fan-out finding, a documented false positive. The combined graph finds that fan and one cross-bank cycle; the multi-bank case list contains the cycle. Labels stay in local evaluation material and never enter inference or shared-signal requests.

Teammates should fetch main and reconcile subsequent feature changes against the root authoritative docs/data_contract.md. Preserve original component commits. No confidential execution, production organizational isolation, secure aggregation, or real-world model performance is claimed.
