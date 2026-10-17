# FraudMesh integrated architecture

FraudMesh demonstrates restricted collaboration across three simulated bank processing stages. All examples are synthetic and execute in one process; the stage boundaries model intended data flow, not production access isolation.

1. `fraudmesh/demo.py` constructs a deterministic bank-local ledger. Each bank passes its complete available history to Person 2's `score_transactions`. History is isolated by institution and sender, uses only prior events, and is recalculated for each request.
2. `prepare_bank_signals` maps uppercase ML bank IDs to lowercase shared IDs, joins scores by local transaction reference, HMACs shared synthetic entity IDs once, derives independent opaque signal references, and coarsens timestamps and amounts. Raw rows and labels are not returned by the demo endpoint.
3. `fraudmesh/privacy.py` rejects unknown fields and invalid value formats before graph construction. Valid syntax does not authenticate a sender or establish that an upstream bank obeyed its policies.
4. Person 3's `build_analysis_response` constructs the graph and comparison. Local structural detection permits one bank; collaborative classification requires two. Identical structural thresholds avoid forcing the local result to zero. The detector finds cycles or distinct-neighbour fan patterns in connected components with at least three edges. Risk values are context; they do not determine structural detection.
5. `fraudmesh/service.py` adapts computed findings to the existing dashboard contract. Node memberships reflect contributing signals, not legal account ownership. Node risk is the maximum incident transaction score.
6. `app/main.py` exposes the API and serves only approved public frontend assets. Requests are bounded to 128,000 bytes, 200 signals, and 60 entities. Rejected data is not echoed in validation responses.
7. The browser displays computed API snapshots with replay disabled. The original authored fixture remains a labelled fallback. Bank-local visualizations duplicate shared entity views by contributing institution so they cannot visually reconstruct a path that requires joining banks.

## Three controlled scenarios

The ring contains a six-edge directed cycle contributed in three two-edge bank fragments, plus three independent ordinary transfers. Each bank's graph lacks the complete cycle. The combined permitted graph produces one suspicious component.

The normal scenario is a three-bank directed chain with no cycle or branching. It produces no case under the current rules.

The local positive control includes a complete three-edge cycle in Bank A plus ordinary Bank B/C activity. It produces a local suspicious component, demonstrating that the local detector is capable of firing. The cycle is not a multi-bank case.

These examples validate behaviour, not generalization. Legitimate cycles and business fan patterns can still produce false positives. One suspicious connected component can include incidental relationships; this prototype does not perform causal attribution, calibrated ring scoring, or production case deduplication.

## Deployment boundary

The target is the user's Ubuntu Python 3.12 s390x LinuxONE VM. Local Windows verification does not establish LinuxONE deployment, Secure Execution, data-in-use protection, or acceleration. Serve on 127.0.0.1 and forward an SSH tunnel. No public service, firewall changes, or Docker are required.
