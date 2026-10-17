"""Local hash-linked analysis journal. Not externally anchored or admin-proof."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL, event_hash TEXT NOT NULL)")
    return db


def record_analysis(path: Path, signals: list[dict], response: dict, scenario_id: str) -> dict:
    with closing(_connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        last = db.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        payload = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "scenario_id": scenario_id,
                   "input_sha256": digest(signals), "output_sha256": digest(response),
                   "signals_processed": len(signals), "policy_version": (response.get("review_queue") or {}).get("policy_version"),
                   "previous_hash": last[0] if last else "0"*64}
        event_hash = digest(payload)
        cursor = db.execute("INSERT INTO events(payload,event_hash) VALUES (?,?)", (json.dumps(payload, sort_keys=True), event_hash))
    return {"event_sequence": cursor.lastrowid, "event_hash": event_hash,
            "scope": "Local hash-linked journal; no external anchor, sender authentication, or administrator protection"}


def verify_journal(path: Path) -> dict:
    if not path.exists():
        return {"valid": True, "events": 0, "scope": "No analysis journal exists yet"}
    previous, count = "0"*64, 0
    with closing(_connect(path)) as db:
        for seq, serialized, event_hash in db.execute("SELECT seq,payload,event_hash FROM events ORDER BY seq"):
            try:
                payload = json.loads(serialized)
                valid = seq == count+1 and payload["previous_hash"] == previous and digest(payload) == event_hash
            except (ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                return {"valid": False, "events_checked": count, "first_invalid_sequence": seq}
            previous, count = event_hash, count+1
    return {"valid": True, "events": count, "head_hash": previous,
            "scope": "Detects inconsistent local edits; truncation or full-chain rewriting requires an external anchor to detect"}
