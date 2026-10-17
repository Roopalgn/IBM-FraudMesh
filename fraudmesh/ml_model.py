"""Dependency-free local transaction-risk scorer (Python 3.12 / s390x).

Input/output and feature provenance are documented in data/README.md.
Only FEATURE_NAMES enter the model; labels and identifiers never do.
"""
from __future__ import annotations

import math
from numbers import Real

FEATURE_NAMES = ("amount", "velocity_1h", "fan_out_1h", "account_age_days")
MODEL_VERSION = "synthetic-local-logistic-v1"

# BEGIN TRAINED MODEL
MODEL = {'means': [6.519101444142434, 0.26741036558380465, 0.2557142566960691, 5.999343099334726], 'scales': [1.2680255245102228, 0.5508417467650022, 0.5372043732793295, 1.3508786479399093], 'weights': [0.27358469468026186, 0.5681017320939525, 0.011818148215639843, -2.1213615956740166], 'bias': -1.4900468950431665, 'threshold': 0.69}
# END TRAINED MODEL


def sigmoid(value: float) -> float:
    """Stable even for extreme logits."""
    return 1.0 / (1.0 + math.exp(-max(-700.0, min(700.0, value))))


def extract_features(transaction: dict) -> list[float]:
    """Strict, bounded numerical features; never consult a target label.

    Callers compute velocity and fan-out from bank-visible *prior* events.
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


def score_transactions(transactions: list[dict]) -> list[dict]:
    """Return one minimal bank-local result per input, preserving order.

    Invalid batches raise ValueError, including the failing row index. Results
    deliberately do not echo raw inputs or ground-truth labels. This function
    does not authorize sharing its output across banks.
    """
    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list of dicts")
    results = []
    for index, transaction in enumerate(transactions):
        try:
            probability = predict_probability(transaction)
            for field in ("transaction_id", "institution_id"):
                if not isinstance(transaction.get(field), str) or not transaction[field].strip():
                    raise ValueError(f"{field} must be a non-empty string")
        except ValueError as exc:
            raise ValueError(f"transactions[{index}]: {exc}") from exc
        reasons = []
        if transaction["velocity_1h"] >= 3:
            reasons.append("elevated_prior_transfer_velocity")
        if transaction["fan_out_1h"] >= 3:
            reasons.append("multiple_prior_recipients")
        if transaction["account_age_days"] < 30:
            reasons.append("recently_opened_account")
        if transaction["amount"] >= 5000:
            reasons.append("large_transfer_amount")
        results.append({
            "transaction_id": transaction["transaction_id"],
            "institution_id": transaction["institution_id"],
            "local_risk_score": round(probability, 8),
            "prediction": int(probability >= MODEL["threshold"]),
            "reason_codes": reasons,
            "model_version": MODEL_VERSION,
        })
    return results
