"""Seeded synthetic generator, batch logistic training, chronological evaluation.

Run from repo root: python scripts/train_ml_baseline.py
No third-party dependency, network access, or external dataset required.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import hashlib
import math
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudmesh.ml_model import (FEATURE_NAMES, MODEL, MODEL_VERSION, extract_features,
                                predict_probability, sigmoid, score_transactions, prepare_transactions)

SEED = 20261017


def generate_dataset(seed: int = SEED, days: int = 40) -> list[dict]:
    """Original synthetic ledger, not real customers or an external dataset.

    Each day has disjoint entities and its own three-bank ring. Features are
    calculated chronologically from bank-local history, before inserting the
    current transfer. Labels are assigned to generated scenarios, not inferred
    from the features, and are retained for evaluation only.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 5:
        raise ValueError("days must be an integer >= 5 for train/validation/test splits")
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
    # Map the original synthetic ledger into the newly agreed raw-input contract.
    raw = []
    for row in rows:
        raw.append({"transaction_id": row["transaction_id"], "institution_id": row["institution_id"],
                    "timestamp": row["timestamp"], "source_entity_token": row["source_account_id"],
                    "destination_entity_token": row["destination_account_id"], "amount": row["amount"],
                    "transaction_type": "transfer", "channel": "online",
                    "fraud_label": row["is_fraud"], "scenario_id": row["scenario_id"]})
    return prepare_transactions(raw)


def split_dataset(rows):
    """60/20/20 by whole chronological days; entities are disjoint by day."""
    days = sorted({row["timestamp"][:10] for row in rows})
    train_end, validation_end = int(len(days) * .6), int(len(days) * .8)
    if len(days) < 5:
        raise ValueError("At least five distinct days are required")
    partitions = [set(part) for part in
                  (days[:train_end], days[train_end:validation_end], days[validation_end:])]
    return tuple([row for row in rows if row["timestamp"][:10] in part]
                 for part in partitions)


def train_model(rows, epochs=350):
    if not rows:
        raise ValueError("Training requires non-empty rows")
    if any(type(row.get("fraud_label")) is not int or row["fraud_label"] not in (0, 1) for row in rows):
        raise ValueError("Training labels must be integer 0 or 1")
    x = [extract_features(row) for row in rows]
    y = [row["fraud_label"] for row in rows]
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
        target = row["fraud_label"]
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


def models_match(first, second):
    """Allow ordinary cross-platform floating-point rounding, not model drift."""
    return all(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)
               for key in ("means", "scales", "weights")
               for a, b in zip(first[key], second[key])) and all(
        math.isclose(first[key], second[key], rel_tol=1e-10, abs_tol=1e-12)
        for key in ("bias", "threshold"))


def dataset_profile(rows):
    """Inspect actual generated rows rather than assume their schema."""
    fields = sorted({key for row in rows for key in row})
    return {"rows": len(rows), "columns": {
        field: {"types": sorted({type(row[field]).__name__ for row in rows if field in row}),
                "missing_or_null": sum(field not in row or row[field] is None for row in rows)}
        for field in fields}, "sha256_canonical_json": hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()}


def local_only_demo(rows):
    """Bank-partitioned embedded-model outputs, with separate evaluation truth.

    No graph detection, cross-bank features, or access-control claim. The caller
    provides bank-visible prior-history features; labels are stripped explicitly
    before inference. This artifact stays local to the evaluation workstream.
    """
    banks = {}
    for bank in sorted({row["institution_id"] for row in rows}):
        local_rows = [row for row in rows if row["institution_id"] == bank]
        inference_rows = [{key: row[key] for key in
                           ("transaction_id", "institution_id", "timestamp", "source_entity_token",
                            "destination_entity_token", "amount", "transaction_type", "channel")}
                          for row in local_rows]
        scores = score_transactions(inference_rows)
        banks[bank] = {"transaction_count": len(local_rows), "scores": scores,
                       "evaluation_only_metrics": evaluate(local_rows, MODEL)}
    scores_by_id = {score["transaction_id"]: score for bank in banks.values() for score in bank["scores"]}
    truth = []
    for row in rows:
        if row["scenario_id"].endswith("-ring"):
            truth.append({"transaction_id": row["transaction_id"], "scenario_id": row["scenario_id"],
                          "institution_id": row["institution_id"], "fraud_label": row["fraud_label"],
                          "local_prediction": int(scores_by_id[row["transaction_id"]]["risk_level"] == "high")})
    return {"data_kind": "synthetic; embedded local baseline only",
            "model_version": MODEL_VERSION, "banks": banks,
            "evaluation_only_ring_truth": truth,
            "limitations": "Partitions are simulated, not security isolation. No collaborative metrics or ring detector."}


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
              "training": {"rows": len(train), "positives": sum(r["fraud_label"] for r in train)},
              "threshold_selection": "maximum validation F1, higher threshold breaks ties",
              "threshold": model["threshold"], "validation": evaluate(validation, model),
              "held_out_test": evaluate(test, model),
              "embedded_model_matches": models_match(model, MODEL),
              "dataset_profile": dataset_profile(rows)}
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
        # Align subsequent in-process demo scoring with the model just written.
        MODEL.clear()
        MODEL.update(model)
        report["embedded_model_matches"] = True
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "transactions.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        (args.output_dir / "model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
        (args.output_dir / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        # The deployed embedded model is separate from an arbitrary --seed retrain.
        # Report which model is used so alternate runs cannot mislabel its outputs.
        _, _, held_out = split_dataset(rows)
        (args.output_dir / "local_baseline_demo.json").write_text(
            json.dumps(local_only_demo(held_out), indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
