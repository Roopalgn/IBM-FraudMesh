"""Measure the actual host doing local ML, HMAC, graph analysis, and triage.

This is a small workload benchmark, not a cross-platform superiority claim.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import ssl
import statistics
import subprocess
import sys
from time import perf_counter
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudmesh.analysis import analyze_signals
from fraudmesh.demo import prepare_bank_signals
from fraudmesh.evaluation import KINDS, evaluation_case
from fraudmesh.ml_model import MODEL_VERSION
from fraudmesh.triage import POLICY_VERSION


def timing_summary(values):
    ordered = sorted(values)
    return {"median_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[min(len(ordered)-1, int(.95*len(ordered)))], 3),
            "max_ms": round(max(values), 3)}


def benchmark(iterations=90, http_url=None):
    durations, transactions = [], 0
    started = perf_counter()
    for i in range(iterations):
        rows, _ = evaluation_case(KINDS[i%len(KINDS)], i)
        tick = perf_counter()
        signals = prepare_bank_signals(rows, "synthetic-benchmark-only-key")
        analyze_signals(signals)
        durations.append((perf_counter()-tick)*1000)
        transactions += len(rows)
    elapsed = perf_counter()-started
    report = {"architecture": platform.machine(), "system": platform.system(),
              "python": platform.python_version(), "logical_cpus_visible": os.cpu_count(),
              "openssl": ssl.OPENSSL_VERSION, "hardware_crypto_acceleration_verified": False,
              "confidential_execution_verified": False,
              "model_version": MODEL_VERSION, "policy_version": POLICY_VERSION,
              "runtime_packages": {name: version(name) for name in ("fastapi", "pydantic", "networkx", "uvicorn")},
              "workload": {"analyses": iterations, "transactions": transactions,
                           "elapsed_seconds": round(elapsed, 6), "transactions_per_second": round(transactions/elapsed, 3),
                           **timing_summary(durations)},
              "scope": "Sequential synthetic bank-local ML, HMAC/coarsening, graph comparison, and review policy on this host; total throughput includes case generation. Excludes HTTP and journal unless separately measured."}
    try:
        report["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["tracked_changes_present"] = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.SubprocessError):
        report["git_commit"] = None
    if platform.system() == "Linux":
        import resource
        report["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if http_url:
        parsed = urlparse(http_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("HTTP benchmark requires a loopback HTTP URL without credentials")
        import httpx
        http_results = []
        with httpx.Client(base_url=http_url, timeout=30) as client:
            def request(index):
                tick = perf_counter()
                result = client.post("/analyze", json={"scenario_id": "synthetic-common"})
                result.raise_for_status()
                data = result.json()
                if data["summary"]["signals_processed"] != 21 or not data.get("audit"):
                    raise RuntimeError("Unexpected benchmark response")
                return (perf_counter()-tick)*1000
            request(0)  # Warmup excluded; its journal entry remains real.
            for concurrency in (1, 4):
                tick = perf_counter()
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    values = list(pool.map(request, range(20)))
                elapsed_http = perf_counter()-tick
                http_results.append({"concurrent_clients": concurrency, "requests": len(values),
                                     "requests_per_second": round(len(values)/elapsed_http, 3), **timing_summary(values)})
        report["http_workload"] = {"scope": "Loopback scenario-reference HTTP analysis including local preparation and journal persistence; excludes browser rendering", "results": http_results}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=90)
    parser.add_argument("--http-url")
    parser.add_argument("--require-s390x", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "platform-benchmark.json")
    args = parser.parse_args()
    if not 1 <= args.iterations <= 900:
        parser.error("iterations must be from 1 to 900")
    if args.require_s390x and platform.machine().lower() != "s390x":
        parser.error("This command requires the actual s390x host; current host is " + platform.machine())
    report = benchmark(args.iterations, args.http_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
