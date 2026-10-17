"""Write measured platform and synthetic scenario evidence without raw records."""
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudmesh.demo import demo_request
from fraudmesh.service import analyze_for_dashboard
from fraudmesh.analysis import analyze_signals


def main():
    results = []
    for name in ("common", "ring", "normal", "local"):
        start = perf_counter()
        request = demo_request(name)
        result = analyze_for_dashboard(request["shared_signals"], request["scenario_id"])
        component = analyze_signals(request["shared_signals"])
        results.append({"scenario": name, "signals": len(request["shared_signals"]),
                        "local_structural_findings": result["comparison"]["local_only"]["finding_count"],
                        "multi_bank_cases": len(result["collaborative_alerts"]),
                        "review_recommended": component["review_queue"]["combined_recommended"],
                        "bank_preparation_and_analysis_ms": round((perf_counter()-start)*1000, 3)})
    report = {"architecture": platform.machine(), "python": platform.python_version(),
              "system": platform.system(), "synthetic": True,
              "confidential_execution_verified": False, "scenarios": results,
              "measurement_scope": "One in-process run per synthetic scenario, including local ML; excludes HTTP and rendering. Not a throughput benchmark."}
    target = ROOT / "output" / "runtime_report.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report saved to {target}")


if __name__ == "__main__":
    main()
