"""Seeded synthetic generator, batch logistic training, chronological evaluation.

Run from repo root: python scripts/train_ml_baseline.py
No third-party dependency, network access, or external dataset required.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudmesh.ml_model import (FEATURE_NAMES, MODEL, extract_features,
                                predict_probability, sigmoid)

SEED = 20261017


def generate_dataset(seed: int = SEED, days: int = 40) -> list[dict]:
    """Original synthetic ledger, not real customers or an external dataset.

    Each day has disjoint entities and its own three-bank ring. Features are
    calculated chronologically from bank-local history, before inserting the
    current transfer. Labels are assigned to generated scenarios, not inferred
    from the features, and are retained for evaluation only.
    """
    rng = random.Random(seed)
    rows = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    banks = ("BANK_A", "BANK_B", "BANK_C")
    for day in range(days):
        events = []
        account_ages = {}
        def add(minute, sender, recipient, bank, dest_bank, amount, age, label, scenario):
            source_id = f"d{day}-{bank}-{sender}"
            destination_id = f"d{day}-{dest_bank}-{recipient}"
            account_ages.setdefault(source_id, age)
            events.append({"timestamp": (start + timedelta(days=day, minutes=minute)).isoformat(),
                           "source_account_id": source_id,
                           "destination_account_id": destination_id,
                           "institution_id": bank, "destination_institution_id": dest_bank,
                           "amount": round(amount, 2), "account_age_days": account_ages[source_id],
                           "is_fraud": label, "scenario_id": f"d{day}-{scenario}"})
        # Background includes new accounts, large payments and repeat senders.
        for _ in range(80):
            add(rng.randrange(1440), f"normal{rng.randrange(20)}", f"merchant{rng.randrange(15)}",
                rng.choice(banks), rng.choice(banks), rng.lognormvariate(6.2, 1.2),
                rng.randrange(1, 1600), 0, "background")
        # Legitimate business burst is an intentional hard negative.
        minute = rng.randrange(200, 1000)
        for i in range(9):
            add(minute + i * 2, "business", f"supplier{i}", "BANK_A", rng.choice(banks),
                rng.uniform(200, 8000), rng.randrange(20, 1500), 0, "business")
        # Three cycles: A -> B -> C -> A. Early legs may look locally ordinary.
        minute = rng.randrange(200, 1000)
        for i in range(9):
            sender = i % 3
            add(minute + i * 2, f"ring{sender}", f"ring{(sender + 1) % 3}",
                banks[sender], banks[(sender + 1) % 3], rng.uniform(250, 1800),
                rng.randrange(1, 180), 1, "ring")
        # Some suspicious burst activity is detectable by a local baseline.
        minute = rng.randrange(200, 1000)
        for i in range(6):
            add(minute + i, "burst", f"target{i}", "BANK_B", rng.choice(banks),
                rng.uniform(500, 6000), rng.randrange(1, 45), 1, "suspicious-burst")
        history = defaultdict(list)
        for event in sorted(events, key=lambda item: item["timestamp"]):
            timestamp = datetime.fromisoformat(event["timestamp"])
            key = (event["institution_id"], event["source_account_id"])
            recent = [(t, recipient) for t, recipient in history[key]
                      if timedelta(0) <= timestamp - t < timedelta(hours=1)]
            event["velocity_1h"] = len(recent)
            event["fan_out_1h"] = len({recipient for _, recipient in recent})
            event["transaction_id"] = f"SYN-{day:03d}-{len(rows):06d}"
            rows.append(event)
            history[key] = recent + [(timestamp, event["destination_account_id"])]
    return rows


def split_dataset(rows):
    """60/20/20 by whole chronological days; entities are disjoint by day."""
    days = sorted({row["timestamp"][:10] for row in rows})
    train_end, validation_end = int(len(days) * .6), int(len(days) * .8)
    return tuple([row for row in rows if row["timestamp"][:10] in set(part)]
                 for part in (days[:train_end], days[train_end:validation_end], days[validation_end:]))


def train_model(rows, epochs=350):
    x = [extract_features(row) for row in rows]
    y = [row["is_fraud"] for row in rows]
    n, width = len(x), len(FEATURE_NAMES)
    means = [sum(row[j] for row in x) / n for j in range(width)]
    scales = [max(1e-9, math.sqrt(sum((row[j] - means[j]) ** 2 for row in x) / n))
              for j in range(width)]
    x = [[(v - means[j]) / scales[j] for j, v in enumerate(row)] for row in x]
    weights, bias = [0.0] * width, 0.0
    positives = sum(y)
    if not 0 < positives < n:
        raise ValueError("Training requires both classes")
    class_weights = {0: n / (2 * (n - positives)), 1: n / (2 * positives)}
    for _ in range(epochs):
        gradient, bias_gradient = [0.0] * width, 0.0
        for row, target in zip(x, y):
            error = (sigmoid(bias + sum(w * v for w, v in zip(weights, row))) - target)
            error *= class_weights[target]
            bias_gradient += error
            for j in range(width):
                gradient[j] += error * row[j]
        weights = [w - .15 * (gradient[j] / n + .01 * w) for j, w in enumerate(weights)]
        bias -= .15 * bias_gradient / n
    return {"means": means, "scales": scales, "weights": weights,
            "bias": bias, "threshold": .5}


def evaluate(rows, model):
    tn = fp = fn = tp = 0
    for row in rows:
        prediction = predict_probability(row, model) >= model["threshold"]
        target = row["is_fraud"]
        tn += int(not target and not prediction)
        fp += int(not target and prediction)
        fn += int(target and not prediction)
        tp += int(target and prediction)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"rows": len(rows), "positives": tp + fn,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "confusion_matrix": [[tn, fp], [fn, tp]],
            "confusion_matrix_order": "rows=true [0,1], columns=predicted [0,1]"}


def run(seed=SEED):
    rows = generate_dataset(seed)
    train, validation, test = split_dataset(rows)
    model = train_model(train)
    # Threshold selection uses validation only; tie-break chooses higher threshold.
    candidates = []
    for i in range(5, 96):
        candidate = dict(model, threshold=i / 100)
        candidates.append((evaluate(validation, candidate)["f1"], i / 100))
    model["threshold"] = max(candidates)[1]
    report = {"data_kind": "synthetic controlled-demo measurements; not real-world validation",
              "seed": seed, "split_method": "whole-day chronological 60/20/20; disjoint entities by day",
              "features": list(FEATURE_NAMES), "epochs": 350,
              "training": {"rows": len(train), "positives": sum(r["is_fraud"] for r in train)},
              "threshold_selection": "maximum validation F1, higher threshold breaks ties",
              "threshold": model["threshold"], "validation": evaluate(validation, model),
              "held_out_test": evaluate(test, model),
              "embedded_model_matches": model == MODEL}
    return rows, model, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output-dir", type=Path, help="Optional generated ledger/model/report directory")
    parser.add_argument("--write-model", action="store_true", help="Replace embedded model in owned ml_model.py")
    args = parser.parse_args()
    rows, model, report = run(args.seed)
    if args.write_model:
        path = ROOT / "fraudmesh" / "ml_model.py"
        text = path.read_text(encoding="utf-8")
        replacement = "# BEGIN TRAINED MODEL\nMODEL = " + repr(model) + "\n# END TRAINED MODEL"
        text, count = re.subn(r"# BEGIN TRAINED MODEL.*?# END TRAINED MODEL", replacement, text, flags=re.S)
        if count != 1:
            raise RuntimeError("Expected exactly one embedded model block")
        path.write_text(text, encoding="utf-8")
        report["embedded_model_matches"] = True
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "transactions.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        (args.output_dir / "model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
        (args.output_dir / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
