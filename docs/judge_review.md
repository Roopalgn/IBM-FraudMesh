# Critical review against the judging criteria

The strongest defensible claim is a measurable workflow for three simulated banks to contribute limited, linkable relationship signals, reconstruct coordinated patterns, and prioritize review using an actual trained local model. The system is a prototype, not a deployed banking privacy guarantee or a new foundational ML algorithm.

| Judging question | Implemented evidence | Remaining limit |
| --- | --- | --- |
| Who benefits and what is the community value | Investigators see contributing banks, pseudonymous relationships, supporting signals and reason codes; raw ledger rows stay outside collaborative requests | No bank partner or user-impact study; no measured financial loss reduction |
| What is original | Restricted cross-institution graph, candidate-specific evidence, bank-local ML, explicit local/combined comparison and ML-informed prioritization in one reproducible workflow | HMAC, logistic regression and graph rules are established methods; do not claim a world-first algorithm |
| Is AI substantive | Original trained logistic model supplies real scores to the review-priority calculation; an ablation changes review decisions when scores change | Review weights are engineering choices, not a trained/calibrated second model; model's synthetic transaction F1 remains 0.5813 |
| Is the engineering sound | Versioned scenario-reference API, strict signals, bounded graph workload, local/combined tests, hash-linked journal, fixtures separated from live API | One-process bank simulation, loopback service, no production participant authentication or external audit anchor |
| Is LinuxONE used meaningfully | User-supplied evidence records actual s390x execution of backend 3058fb8, 71 passing tests and scoped in-process/HTTP benchmarks including journal writes | Evidence is transcribed, not independently retrieved or remotely attested. Recheck the new UI release. Hosting alone proves no Secure Execution, hardware acceleration, availability, or superiority |

## Biggest gaps fixed in this revision

1. Person 4's 15f6d89 adapter/client/fixtures are integrated and tested against real HTTP endpoint responses. The backend accepts the proposed person3.graph.v2 reference envelope; no raw ledger or secret needs to reach the browser. The legacy signal-request path is retained explicitly.
2. ML now affects review recommendation. A fixed versioned policy weights structure strength 0.35, mean supporting transaction-model score 0.35, nearby UTC-hour buckets 0.20, and amount-band consistency 0.10; recommendation threshold is 0.75. Cycles and two-sided hubs get full structural strength; one-sided fans get 0.25. Every candidate remains visible. Priority is not fraud probability.
3. A two-sided hub requires at least three distinct inbound and three outbound counterparties with complete supporting references. It reconstructs a pattern whose inbound and outbound fragments can be split between banks. Self-transfers do not count as distinct fan counterparties.
4. The new 90-scenario cohort measures false positives, misses and ablations rather than quoting one cherry-picked ring.
5. Successful API analyses produce a receipt linked to local SQLite journal entries. Entries contain counts and digests, not input rows, signal references, tokens or keys. Inconsistent edits are detectable; wholesale rewriting/truncation is not detectable without an external anchor.
6. Deployment verification now generates actual platform and optional concurrent HTTP evidence; the LinuxONE script refuses to label a non-s390x host as LinuxONE.

## Reproducible evaluation

Command: `python scripts/evaluate_collaboration.py`. Seed 20261018; ten independently seeded repetitions per family: cross-bank cycle, single-bank cycle, two-sided mule hub, payroll, multi-bank payroll, ordinary chain, slow cycle, benign fast cycle, and deliberately ambiguous fast cycle. There are 30 positive and 60 negative scenarios. Scenario entities are disjoint and timestamps follow the trained model's January training period. Labels remain in the evaluator and never enter inference or shared signals.

The transaction model is unchanged. Review-policy weights/threshold are fixed before running the cohort and are not optimized from its labels. This is a controlled stress-test cohort, not real-bank generalization evidence. Each measurement is a scenario-level risk screen: at least one positive transaction flag, structural finding or recommended review. These methods do not all reconstruct the same object; report the unit explicitly and do not call the figures ring recall.

| Screening method | Precision | Recall | F1 | False-positive scenarios |
| --- | ---: | ---: | ---: | ---: |
| ML-only transaction risk screen | 0.5000 | 1.0000 | 0.6667 | 30 |
| Local structural findings | 0.6667 | 0.6667 | 0.6667 | 10 |
| Combined structural findings | 0.3750 | 1.0000 | 0.5455 | 50 |
| Local ML-informed triage | 1.0000 | 0.3333 | 0.5000 | 0 |
| Combined ML-informed triage | 0.7500 | 1.0000 | 0.8571 | 10 |

Ambiguous legitimate fast cycles deliberately share the available signals of suspicious cycles; ten false-positive scenarios remain. That limitation is part of the result, not a reason to suppress those examples. The payroll structural finding remains visible, but is not recommended by the review policy. Dataset composition and synthetic assumptions strongly influence all numbers.

The original held-out transaction benchmark is separate: precision 0.497041, recall 0.700000, F1 0.581315 on 832 synthetic transfers. Never substitute the 0.8571 scenario-screen F1 for the transaction classifier F1.

## Honest IBM platform statement

The recorded backend run supports: We executed inference, HMAC signal preparation, cross-bank graph computation, prioritization and audit persistence on the supplied LinuxONE s390x VM at commit 3058fb8. See frontend/public/linuxone-run-evidence.json for the transcription and source. The new UI release still needs a VM smoke check. No comparison here establishes that LinuxONE outperforms another machine.

IBM documents Secure Execution as a specific technology requiring deployment configuration, not a property automatically established by having a VM: https://www.ibm.com/docs/en/linux-on-systems?topic=execution-introduction . IBM's Community Cloud introduction provides access and s390x context: https://community.ibm.com/zsystems/l1cc/ . These sources describe platform capability; they do not verify this allocation or workload.

## Remaining tasks before judging

- Retain the original s390x reports/logs for backend 3058fb8, update the VM to the merged UI release and smoke-test the interface through the tunnel.
- Run the live loopback HTTP benchmark, confirm journal consistency, and rehearse through the SSH tunnel.
- Ask the IBM mentor whether verified Secure Execution is available only if time permits; otherwise keep it out of implemented claims.
- Prepare the pitch and backup recording with the before/after graph, real evidence and explicitly synthetic metrics.
- State the key-sharing/linkability, organizational-isolation and false-positive limitations. Confirm the hub cutoff and submit all required deliverables.
