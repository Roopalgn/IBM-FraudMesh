"""Produce reproducible synthetic screening comparisons for judge review."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudmesh.evaluation import evaluate_scenarios

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "collaboration-evaluation.json")
    args = parser.parse_args()
    report = evaluate_scenarios(args.repeats, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "outcomes"}, indent=2))
