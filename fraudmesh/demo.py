"""Bank-local synthetic demo preparation; raw ledger never enters the API payload."""
from __future__ import annotations

import hashlib
import hmac
import os
from collections import defaultdict

from fraudmesh.ml_model import score_transactions
from fraudmesh.ml_demo import generate_demo_ledger
from fraudmesh.ml_replay import BankLocalReplay, transform_scored_bank
from fraudmesh.privacy import create_shared_signal, validate_shared_signals

SCENARIOS = {"common", "ring", "normal", "local"}


def demo_transactions(name: str = "ring") -> list[dict]:
    if name not in SCENARIOS:
        raise ValueError("Unknown synthetic scenario")
    if name == "common":
        return generate_demo_ledger()["transactions"]
    banks = ["BANK_A", "BANK_B", "BANK_C"]
    if name == "normal":
        legs = [(banks[i], f"normal-{i}", f"normal-{i+1}", 200 + i * 50) for i in range(3)]
    elif name == "local":
        legs = [("BANK_A", f"local-{i}", f"local-{(i+1)%3}", 600 + i * 20) for i in range(3)]
        legs += [(bank, f"payer-{bank}", f"merchant-{bank}", 100) for bank in banks[1:]]
    else:
        legs = [(banks[i//2], f"ring-{i}", f"ring-{(i+1)%6}", 600 + i * 25) for i in range(6)]
        legs += [(bank, f"payer-{bank}", f"merchant-{bank}", 100) for bank in banks]
    return [{"transaction_id": f"synthetic-{name}-{i}", "institution_id": bank,
             "source_entity_token": source, "destination_entity_token": target,
             "timestamp": f"2026-10-17T10:{i*3:02d}:00Z", "amount": amount,
             "transaction_type": "transfer", "channel": "transfer"}
            for i, (bank, source, target, amount) in enumerate(legs)]


def prepare_bank_signals(transactions: list[dict], secret: str) -> list[dict]:
    """Score complete bank-local history and export only allowed coarse signals.

    This is a simulated boundary within one process, not organizational isolation.
    Caller-owned ledgers are never mutated or returned.
    """
    by_bank: dict[str, list[dict]] = defaultdict(list)
    for row in transactions:
        by_bank[row["institution_id"]].append(row)
    signals = []
    for bank, rows in sorted(by_bank.items()):
        scores = {item["transaction_id"]: item for item in score_transactions(rows)}
        for row in rows:
            reference = hmac.new(secret.encode(), ("signal:" + row["transaction_id"]).encode(), hashlib.sha256).hexdigest()[:24]
            signals.append(create_shared_signal(
                signal_id=f"sig-{reference}", institution_id=bank.lower(),
                source_entity_id=row["source_entity_token"],
                destination_entity_id=row["destination_entity_token"],
                timestamp=row["timestamp"], amount=row["amount"],
                local_risk_score=scores[row["transaction_id"]]["risk_score"],
                secret=secret, channel=row["channel"]))
    return sorted(signals, key=lambda item: item["signal_id"])


def demo_request(name: str = "ring") -> dict:
    secret = os.environ.get("FRAUDMESH_DEMO_SECRET", "synthetic-demo-only-not-a-production-key")
    if name == "common":
        demo = generate_demo_ledger()
        replay = BankLocalReplay()  # Request-local state; never shared across API clients.
        scores = [replay.score_new([row])[0] for row in demo["transactions"]]
        signals = []
        for bank in ("BANK_A", "BANK_B", "BANK_C"):
            local = [row for row in demo["transactions"] if row["institution_id"] == bank]
            ids = {row["transaction_id"] for row in local}
            references = {row["transaction_id"]: row["signal_id"] for row in demo["local_reference_map"] if row["institution_id"] == bank}
            signals.extend(transform_scored_bank(
                local, [row for row in scores if row["transaction_id"] in ids], references,
                transformer=create_shared_signal, validator=validate_shared_signals, secret=secret))
        return {"scenario_id": "synthetic-common", "shared_signals": signals}
    return {"scenario_id": f"synthetic-{name}",
            "shared_signals": prepare_bank_signals(demo_transactions(name), secret)}
