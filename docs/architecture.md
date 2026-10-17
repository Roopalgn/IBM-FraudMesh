# FraudMesh integrated architecture

FraudMesh demonstrates restricted collaboration across three simulated bank processing stages. All examples are synthetic and execute in one process; the stage boundaries model intended data flow, not production access isolation.

1. `fraudmesh/demo.py` uses Person 2's `generate_demo_ledger` for the default 21-transfer common scenario and `BankLocalReplay` to score cumulative per-bank history. Small ring/normal/local controls remain available. Each bank passes its complete available history to Person 2's `score_transactions`. History is isolated by institution and sender, uses only prior events, and is recalculated for each request.
2. `prepare_bank_signals` maps uppercase ML bank IDs to lowercase shared IDs, joins scores by local transaction reference, HMACs shared synthetic entity IDs once, derives independent opaque signal references, and coarsens timestamps and amounts. Raw rows and labels are not returned by the demo endpoint.
3. `fraudmesh/privacy.py` rejects unknown fields and invalid value formats before graph construction. Valid syntax does not authenticate a sender or establish that an upstream bank obeyed its policies.
4. Person 3's `build_analysis_response` constructs the graph and comparison. Local structural detection permits one bank; collaborative classification requires two. Identical structural thresholds avoid forcing the local result to zero. Person 3's detector finds candidate-specific directed cycles of three to six nodes and fans with at least three distinct counterparties. Local and combined views use the same detector; the dashboard classifies cross-institution patterns separately. Each candidate carries its exact supporting signal references. Hour-bucket propagation spans at most two hours. Risk values are context; they do not determine structural detection.
5. `fraudmesh/analysis.py` adds a versioned ML-informed review policy over all structural candidates, retaining their original structural labels. `fraudmesh/triage.py` uses supporting model scores, structure, hour proximity and amount bands; recommendation is not a fraud probability. Two-sided hubs require at least three distinct inbound and outbound neighbors. `fraudmesh/service.py` retains the legacy display adapter. In the current component adapter, node scores remain unavailable; membership reflects contributing signals, not legal account ownership.
6. `app/main.py` exposes the API and serves only approved public frontend assets. Requests are bounded to 128,000 bytes, 200 signals, 60 entities, and 100 structural findings (overflow is rejected without partial results). Rejected data is not echoed in validation responses.
7. The browser requests only a supported synthetic scenario reference and adapts the computed person3.graph.v2 response. Saved component fixtures and authored replay remain explicitly labelled alternatives. Local views contain only the selected bank's supplied signals. Successful analyses persist a count/digest receipt to a local hash-linked SQLite journal; it is not externally anchored or administrator-proof.

## Shared scenario and three controls

The default common scenario uses the same 21-event ledger, independent signal-reference map, actual incremental ML scores, and privacy transformer from the teammates’ implementations. Nine background payments, six legitimate payroll transfers, and six cycle transfers produce one local fan-out finding and one cross-bank cycle case. The payroll finding is a false positive under the synthetic evaluation truth, which stays outside detection. The combined graph has two findings total.


The ring contains a six-edge directed cycle contributed in three two-edge bank fragments, plus three independent ordinary transfers. Each bank's graph lacks the complete cycle. The combined permitted graph produces one suspicious component.

The normal scenario is a three-bank directed chain with no cycle or branching. It produces no case under the current rules.

The local positive control includes a complete three-edge cycle in Bank A plus ordinary Bank B/C activity. It produces a local suspicious component, demonstrating that the local detector is capable of firing. The cycle is not a multi-bank case.

These examples validate behaviour, not generalization. Legitimate cycles and business fan patterns can still produce false positives. Candidate evidence is restricted to supporting directed pairs; this prototype does not perform causal attribution, calibrated ring scoring, or production case deduplication.

## Deployment boundary

The target is the user's Ubuntu Python 3.12 s390x LinuxONE VM. Local Windows verification does not establish LinuxONE deployment, Secure Execution, data-in-use protection, or acceleration. Serve on 127.0.0.1 and forward an SSH tunnel. No public service, firewall changes, or Docker are required.
