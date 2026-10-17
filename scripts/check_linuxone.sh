#!/usr/bin/env bash
# Run from any directory after cloning the integration branch onto LinuxONE.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip check
mkdir -p output
python -B -m unittest discover -s tests -v 2>&1 | tee output/test-results.txt
python -B scripts/train_ml_baseline.py > output/ml-evaluation.json
python -B scripts/verify_runtime.py
python -B scripts/evaluate_collaboration.py
python -B scripts/benchmark_runtime.py --require-s390x
echo "Validation finished. Start the application with:"
echo "source .venv/bin/activate"
echo "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
