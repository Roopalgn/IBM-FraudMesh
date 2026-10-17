"""Generate LOCAL artifacts for one shared demo, using actual embedded ML scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fraudmesh.ml_demo import DEMO_SEED, generate_demo_ledger
from fraudmesh.ml_model import MODEL_VERSION
from fraudmesh.ml_replay import BankLocalReplay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Local-only scratch directory, never an API publication directory")
    parser.add_argument("--seed", type=int, default=DEMO_SEED)
    args = parser.parse_args()
    demo = generate_demo_ledger(args.seed)
    replay = BankLocalReplay()
    scores = [replay.score_new([row])[0] for row in demo["transactions"]]
    banks = {bank: {"transactions": [row for row in demo["transactions"] if row["institution_id"] == bank],
                    "scores": [score for row, score in zip(demo["transactions"], scores)
                               if row["institution_id"] == bank]}
             for bank in ("BANK_A", "BANK_B", "BANK_C")}
    target = args.output_dir / "local_only"
    target.mkdir(parents=True, exist_ok=True)
    artifacts = {"transactions.json": demo["transactions"], "evaluation_truth.json": demo["evaluation_truth"],
                 "reference_map.json": demo["local_reference_map"], "bank_scores.json": banks,
                 "manifest.json": {"seed": args.seed, "data_kind": demo["data_kind"],
                                   "transactions": len(scores), "model_version": MODEL_VERSION,
                                   "warning": "All files are local/evaluation only. Use Person 3's transformer for shared signals."}}
    for name, value in artifacts.items():
        (target / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifacts["manifest.json"], indent=2))


if __name__ == "__main__":
    main()
