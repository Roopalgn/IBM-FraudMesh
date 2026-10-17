"""One original, deterministic, small synthetic local ledger for all workstreams.

Opaque entity strings are NOT verified HMAC tokens. Truth/references are separate
bank-local/evaluation artifacts. Never send this whole package to /analyze.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

DEMO_SEED = 20261017


def generate_demo_ledger(seed: int = DEMO_SEED) -> dict:
    rng = random.Random(seed)
    origin = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
    events = []

    def add(minute, bank, source, destination, amount, truth, group):
        events.append({"minute": minute, "bank": bank, "source": source,
                       "destination": destination, "amount": amount,
                       "truth": truth, "group": group})

    # Ordinary disconnected payments create no fake coordinated cycles.
    for index in range(9):
        add(index * 2, ("BANK_A", "BANK_B", "BANK_C")[index % 3],
            f"entity_{100 + index}", f"entity_{200 + index}",
            round(rng.uniform(40, 800), 2), 0, "background")
    # Legitimate payroll burst: useful structural/local-risk hard negative.
    for index in range(6):
        add(20 + index, "BANK_A", "entity_040", f"entity_{50 + index}",
            round(rng.uniform(300, 1600), 2), 0, "legitimate_burst")
    # Repeated three-bank cycle. Same identity is recipient then sender.
    for index in range(6):
        leg = index % 3
        add(30 + index * 2, ("BANK_A", "BANK_B", "BANK_C")[leg],
            f"entity_{10 + leg:03d}", f"entity_{10 + (leg + 1) % 3:03d}",
            round(rng.uniform(650, 950), 2), 1, "suspicious_cycle")
    ledger, truth, references = [], [], []
    for index, event in enumerate(sorted(events, key=lambda row: row["minute"]), 1):
        transaction_id = f"TX-{index:03d}"
        ledger.append({"transaction_id": transaction_id, "institution_id": event["bank"],
                       "timestamp": (origin + timedelta(minutes=event["minute"])).isoformat().replace("+00:00", "Z"),
                       "source_entity_token": event["source"], "destination_entity_token": event["destination"],
                       "amount": event["amount"], "transaction_type": "transfer", "channel": "online"})
        truth.append({"transaction_id": transaction_id, "fraud_label": event["truth"],
                      "scenario_label": event["group"]})
        # Separate random references, not copies/hashes/encodings of raw IDs.
        references.append({"institution_id": event["bank"], "transaction_id": transaction_id,
                           "signal_id": f"sig-{rng.getrandbits(128):032x}"})
    return {"seed": seed, "data_kind": "synthetic controlled demonstration, not held-out evaluation",
            "transactions": ledger, "evaluation_truth": truth,
            "local_reference_map": references}
