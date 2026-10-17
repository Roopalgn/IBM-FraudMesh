"""Dependency-free local transaction-risk scorer (Python 3.12 / s390x).

Input/output and feature provenance are documented in data/README.md.
Only FEATURE_NAMES enter the model; labels and identifiers never do.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from numbers import Real

FEATURE_NAMES = ("amount", "velocity_1h", "fan_out_1h")
MODEL_VERSION = "synthetic-local-logistic-v2"

# BEGIN TRAINED MODEL
MODEL = {'means': [6.519101444142434, 0.26741036558380465, 0.2557142566960691], 'scales': [1.2680255245102228, 0.5508417467650022, 0.5372043732793295], 'weights': [0.5125882543484722, 0.866762062744875, 0.05318610688457971], 'bias': -0.40001247292035685, 'threshold': 0.55}
# END TRAINED MODEL


def sigmoid(value: float) -> float:
    """Stable even for extreme logits."""
    return 1.0 / (1.0 + math.exp(-max(-700.0, min(700.0, value))))


def extract_features(transaction: dict) -> list[float]:
    """Strict, bounded numerical features; never consult a target label.

    prepare_transactions computes velocity/fan-out from bank-visible prior events.
    Silently substituting zero for missing history would hide integration bugs.
    """
    if not isinstance(transaction, dict):
        raise ValueError("Each transaction must be a dict")
    features = []
    for field in FEATURE_NAMES:
        value = transaction.get(field)
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{field} must be a finite non-negative number")
        try:
            numeric = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError(f"{field} must be finite") from exc
        if not math.isfinite(numeric) or numeric < 0:
            raise ValueError(f"{field} must be a finite non-negative number")
        features.append(math.log1p(min(numeric, 1e12)))
    if transaction["fan_out_1h"] > transaction["velocity_1h"]:
        raise ValueError("fan_out_1h cannot exceed velocity_1h")
    return features


def predict_probability(transaction: dict, model: dict | None = None) -> float:
    model = MODEL if model is None else model
    x = extract_features(transaction)
    standardized = [(v - mean) / scale for v, mean, scale in
                    zip(x, model["means"], model["scales"])]
    return sigmoid(model["bias"] + sum(w * v for w, v in
                                      zip(model["weights"], standardized)))


def prepare_transactions(transactions: list[dict]) -> list[dict]:
    """Validate raw contract and derive past-only bank-local batch features.

    Batch-local history resets on each call. All timestamps must have an
    explicit timezone. Sort internally by UTC time, preserving original output
    order and using original input order to break timestamp ties.
    """
    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list of dicts")
    times, prepared, seen = [], [], set()
    for index, transaction in enumerate(transactions):
        try:
            if not isinstance(transaction, dict):
                raise ValueError("Each transaction must be a dict")
            for field in ("transaction_id", "institution_id", "timestamp", "source_entity_token",
                          "destination_entity_token", "transaction_type", "channel"):
                if not isinstance(transaction.get(field), str) or not transaction[field].strip():
                    raise ValueError(f"{field} must be a non-empty string")
            if transaction["institution_id"] not in {"BANK_A", "BANK_B", "BANK_C"}:
                raise ValueError("institution_id must be BANK_A, BANK_B or BANK_C")
            if transaction["transaction_id"] in seen:
                raise ValueError("duplicate transaction_id")
            seen.add(transaction["transaction_id"])
            timestamp = datetime.fromisoformat(transaction["timestamp"].replace("Z", "+00:00"))
            if timestamp.utcoffset() is None:
                raise ValueError("timestamp must include a timezone")
            # Validate amount with the same strict numerical policy as training.
            extract_features({"amount": transaction.get("amount"), "velocity_1h": 0, "fan_out_1h": 0})
            times.append(timestamp)
            prepared.append(dict(transaction))
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"transactions[{index}]: {exc}") from exc
    history = defaultdict(list)
    for index in sorted(range(len(prepared)), key=lambda i: (times[i], i)):
        row, timestamp = prepared[index], times[index]
        key = (row["institution_id"], row["source_entity_token"])
        prior = [(time, target) for time, target in history[key]
                 if timedelta(0) <= timestamp - time < timedelta(hours=1)]
        row["velocity_1h"] = len(prior)
        row["fan_out_1h"] = len({target for _, target in prior})
        history[key] = prior + [(timestamp, row["destination_entity_token"])]
    return prepared


def score_transactions(transactions: list[dict]) -> list[dict]:
    """Score raw provisional-contract records without labels or graph detection.

    Return exactly four fields per row. Invalid batches raise indexed ValueError.
    Scores are uncalibrated model outputs, not verified fraud probabilities.
    """
    results = []
    for transaction in prepare_transactions(transactions):
        probability = predict_probability(transaction)
        reasons = []
        if transaction["velocity_1h"] >= 3:
            reasons.append("elevated_prior_transfer_velocity")
        if transaction["fan_out_1h"] >= 3:
            reasons.append("multiple_prior_recipients")
        if transaction["amount"] >= 5000:
            reasons.append("large_transfer_amount")
        results.append({
            "transaction_id": transaction["transaction_id"],
            "risk_score": round(probability, 8),
            "risk_level": ("high" if probability >= MODEL["threshold"] else
                           "medium" if probability >= MODEL["threshold"] / 2 else "low"),
            "reason_codes": reasons,
        })
    return results
