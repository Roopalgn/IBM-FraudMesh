"""Independent synthetic scenario evaluation. Labels are evaluation-only.

The fixed review policy is not fitted or selected on this cohort. Similar
legitimate and suspicious cycles intentionally expose irreducible ambiguity.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import random
import hashlib
import json

from fraudmesh.demo import prepare_bank_signals
from fraudmesh.analysis import analyze_signals
from fraudmesh.ml_model import score_transactions
from fraudmesh.ml_model import MODEL_VERSION
from fraudmesh.triage import POLICY_VERSION, REVIEW_THRESHOLD

KINDS = ("cross_bank_cycle", "single_bank_cycle", "mule_hub", "payroll",
         "multi_bank_payroll", "normal_chain", "slow_cycle", "benign_fast_cycle", "ambiguous_fast_cycle")
POSITIVE_KINDS = frozenset({"cross_bank_cycle", "single_bank_cycle", "mule_hub"})


def evaluation_case(kind: str, index: int, seed: int = 20261018) -> tuple[list[dict], bool]:
    if kind not in KINDS:
        raise ValueError("Unknown evaluation scenario")
    rng = random.Random(f"{seed}:{kind}:{index}")
    banks = ("BANK_A", "BANK_B", "BANK_C")
    start = datetime(2026, 10, 18, tzinfo=timezone.utc) + timedelta(days=index)
    legs = []
    if kind in {"cross_bank_cycle", "single_bank_cycle", "slow_cycle", "benign_fast_cycle", "ambiguous_fast_cycle"}:
        rounds = 1 if kind == "benign_fast_cycle" else 2
        for i in range(3*rounds):
            bank = "BANK_A" if kind == "single_bank_cycle" else banks[i%3]
            amount = rng.uniform(30, 180) if kind == "benign_fast_cycle" else rng.uniform(650, 950)
            minute = i * (1440 if kind == "slow_cycle" else 2)
            legs.append((bank, f"node-{i%3}", f"node-{(i+1)%3}", amount, minute))
    elif kind in {"payroll", "multi_bank_payroll"}:
        for i in range(6):
            legs.append((banks[i%3] if kind == "multi_bank_payroll" else "BANK_A", "employer", f"employee-{i}", rng.uniform(300, 1600), i))
    elif kind == "mule_hub":
        for i in range(3):
            legs.append(("BANK_A", f"sender-{i}", "hub", rng.uniform(650, 950), i))
            legs.append(("BANK_B", "hub", f"receiver-{i}", rng.uniform(650, 950), i+5))
    else:
        for i in range(4):
            legs.append((banks[i%3], f"chain-{i}", f"chain-{i+1}", rng.uniform(40, 800), i))
    prefix = f"eval-{seed}-{kind}-{index}-"
    transactions = [{"transaction_id": f"{prefix}tx-{i}", "institution_id": bank,
        "source_entity_token": prefix+source, "destination_entity_token": prefix+target,
        "timestamp": (start+timedelta(minutes=minute)).isoformat(), "amount": round(amount, 2),
        "transaction_type": "transfer", "channel": "online"}
        for i, (bank, source, target, amount, minute) in enumerate(legs)]
    return sorted(transactions, key=lambda row: row["timestamp"]), kind in POSITIVE_KINDS


def metrics(pairs: list[tuple[bool, bool]]) -> dict:
    tp = sum(truth and predicted for truth, predicted in pairs)
    fp = sum(not truth and predicted for truth, predicted in pairs)
    fn = sum(truth and not predicted for truth, predicted in pairs)
    tn = sum(not truth and not predicted for truth, predicted in pairs)
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    return {"scenarios": len(pairs), "precision": precision, "recall": recall,
            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0,
            "confusion_matrix": [[tn, fp], [fn, tp]], "false_positive_scenarios": fp}


def evaluate_scenarios(repeats: int = 10, seed: int = 20261018) -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ValueError("repeats must be an integer from 1 to 100")
    results, outcomes, input_digests = defaultdict(list), [], []
    for kind in KINDS:
        for index in range(repeats):
            rows, truth = evaluation_case(kind, index, seed)
            input_digests.append(hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest())
            signals = prepare_bank_signals(rows, "synthetic-evaluation-only-key")
            component = analyze_signals(signals)
            predictions = {
                "ml_only_risk_screen": any(row["risk_level"] == "high" for row in score_transactions(rows)),
                "local_structure": component["comparison"]["local_only"]["finding_count"] > 0,
                "combined_structure": component["comparison"]["collaborative"]["finding_count"] > 0,
                "local_ml_graph_triage": component["review_queue"]["local_recommended"] > 0,
                "combined_ml_graph_triage": component["review_queue"]["combined_recommended"] > 0}
            for name, prediction in predictions.items():
                results[name].append((truth, prediction))
            outcomes.append({"kind": kind, "index": index, "evaluation_only_positive": truth, "predictions": predictions})
    return {"seed": seed, "scenario_count": len(outcomes), "policy_version": POLICY_VERSION,
            "transaction_model_version": MODEL_VERSION,
            "input_manifest_sha256": hashlib.sha256(json.dumps(input_digests).encode()).hexdigest(),
            "threshold": REVIEW_THRESHOLD, "threshold_selection": "Fixed engineering policy before evaluating this independent synthetic cohort; not fitted on these labels",
            "unit": "Scenario-level screening: at least one finding/review/transaction flag; not ring recall or production accuracy",
            "cohort": "Post-training dates and disjoint entities; original trained transaction model is unchanged",
            "metrics": {name: metrics(pairs) for name, pairs in results.items()}, "outcomes": outcomes,
            "limitations": ["Synthetic generator assumptions do not establish real-world generalization",
                            "Legitimate repeated fast cycles deliberately overlap suspicious-cycle features",
                            "Review policy is transparent hand-weighted fusion over a trained model, not a second learned classifier",
                            "ML-only screening cannot reconstruct or explain a cross-bank path"]}
