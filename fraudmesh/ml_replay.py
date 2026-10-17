"""Bank-local replay and explicit handoff to Person 3's privacy transformer.

No tokenization, graph detection, network requests, or cross-bank raw export.
"""
from __future__ import annotations

from datetime import datetime
import math
from numbers import Real
from typing import Callable

from fraudmesh.ml_model import INPUT_FIELDS, prepare_transactions, score_transactions

BANK_ID_MAPPING = {"BANK_A": "bank_a", "BANK_B": "bank_b", "BANK_C": "bank_c"}


def _time(row: dict) -> datetime:
    return datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))


class BankLocalReplay:
    """Cumulative raw history per bank, delegating all scoring to the public scorer.

    New events may be unordered within a call but cannot precede a bank's
    previously accepted timestamp. Late events raise instead of silently
    revising already emitted scores. Reset clears history. State commits only
    after the entire batch validates and scores successfully. Small-demo adapter:
    rescoring cumulative history is intentionally not an unbounded stream design.
    """

    def __init__(self) -> None:
        self._history: dict[str, list[dict]] = {}

    def reset(self, institution_id: str | None = None) -> None:
        if institution_id is None:
            self._history.clear()
        elif institution_id in BANK_ID_MAPPING:
            self._history.pop(institution_id, None)
        else:
            raise ValueError("reset institution_id must be BANK_A, BANK_B or BANK_C")

    def score_new(self, transactions: list[dict]) -> list[dict]:
        # Reuse scorer validation. Do not retain caller labels/metadata in state.
        validated = prepare_transactions(transactions)
        if not validated:
            return []
        records = [{field: row[field] for field in INPUT_FIELDS} for row in validated]
        seen = {row["transaction_id"] for bank in self._history.values() for row in bank}
        if any(row["transaction_id"] in seen for row in records):
            raise ValueError("Replay transaction_id already processed; reset before replaying")
        candidate = {bank: list(history) for bank, history in self._history.items()}
        changed = {row["institution_id"] for row in records}
        for bank in changed:
            new = [row for row in records if row["institution_id"] == bank]
            history = candidate.setdefault(bank, [])
            if history and min(map(_time, new)) < max(map(_time, history)):
                raise ValueError(f"Late event for {bank}; reset and replay chronologically")
            history.extend(new)
        results = {}
        for bank in sorted(changed):
            for result in score_transactions(candidate[bank]):
                results[result["transaction_id"]] = result
        self._history = candidate
        return [results[row["transaction_id"]] for row in records]


def transform_scored_bank(
    transactions: list[dict], scores: list[dict], reference_map: dict[str, str], *,
    transformer: Callable, validator: Callable, secret: str | bytes,
) -> list[dict]:
    """Call Person 3's create_shared_signal and validate_shared_signals locally.

    Exact amounts/times and opaque local IDs are arguments to the local privacy
    transformer only. Only its validated output may enter collaborative analysis.
    reference_map is bank-local and MUST NOT be sent alongside the shared output.
    The privacy transformer, not this module, supplies HMAC/coarse buckets.
    """
    validated = prepare_transactions(transactions)
    if len({row["institution_id"] for row in validated}) > 1:
        raise ValueError("Transform one bank's records at a time")
    if not isinstance(scores, list) or any(not isinstance(row, dict) for row in scores):
        raise ValueError("scores must be a list of score dictionaries")
    ids = {row["transaction_id"] for row in validated}
    score_ids = [row.get("transaction_id") for row in scores]
    if any(not isinstance(item, str) for item in score_ids):
        raise ValueError("Every score needs a string transaction_id")
    if len(score_ids) != len(set(score_ids)) or set(score_ids) != ids:
        raise ValueError("Scores must align one-to-one with local transactions")
    if not isinstance(reference_map, dict) or set(reference_map) != ids:
        raise ValueError("reference_map must cover exactly this bank-local batch")
    references = list(reference_map.values())
    if any(not isinstance(value, str) or not value.strip() or value in ids for value in references):
        raise ValueError("Shared references must be nonempty and distinct from raw transaction IDs")
    if len(references) != len(set(references)):
        raise ValueError("Shared signal references must be unique")
    by_id = {row["transaction_id"]: row for row in scores}
    # Validate every score before passing anything to the transformer.
    for row in scores:
        score = row.get("risk_score")
        if isinstance(score, bool) or not isinstance(score, Real):
            raise ValueError("risk_score must be a finite number in [0,1]")
        try:
            numeric = float(score)
        except (ValueError, OverflowError) as exc:
            raise ValueError("risk_score must be a finite number in [0,1]") from exc
        if not math.isfinite(numeric) or not 0 <= numeric <= 1:
            raise ValueError("risk_score must be a finite number in [0,1]")
    signals = [transformer(
        signal_id=reference_map[row["transaction_id"]],
        institution_id=BANK_ID_MAPPING[row["institution_id"]],
        source_entity_id=row["source_entity_token"],
        destination_entity_id=row["destination_entity_token"],
        timestamp=row["timestamp"], amount=row["amount"],
        local_risk_score=by_id[row["transaction_id"]]["risk_score"],
        secret=secret, channel=row["channel"],
    ) for row in validated]
    validator(signals)
    return signals
