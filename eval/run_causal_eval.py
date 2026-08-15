"""Run every controlled scenario in eval/cases/ through MemoryIR's real
attribution pipeline (query engine, intervention engine, attribution
engine) and print aggregate, reproducible causal-detection stats.

This is a thin CLI over app.services.causal_eval, the same module that
powers the live /api/evaluation endpoint, so the numbers shown here and
the numbers shown in the running product can never drift apart.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.causal_eval import run_suite


def main() -> None:
    cases_dir = Path(__file__).parent / "cases"
    suite = run_suite(cases_dir)
    print(json.dumps(
        {
            "total_cases": suite["case_count"],
            "overall_metrics": suite["metrics"],
            "naive_vs_memoryir": suite["comparison"],
            "by_scenario_type": suite["by_scenario_type"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
