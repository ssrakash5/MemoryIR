from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_cases(cases_dir: Path) -> list[dict]:
    cases = []
    for path in sorted(cases_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    cases.append(json.loads(line))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize the MemoryIR controlled evaluation suite.")
    parser.add_argument("--cases-dir", type=Path, default=Path(__file__).parent / "cases")
    args = parser.parse_args()
    cases = load_cases(args.cases_dir)
    by_type = Counter(case["scenario_type"] for case in cases)
    proxy_cases = [case for case in cases if len(case.get("derived_path", [])) > 1]
    print(json.dumps({
        "label": "controlled evaluation suite",
        "case_count": len(cases),
        "scenario_types": dict(by_type),
        "proxy_case_count": len(proxy_cases),
    }, indent=2))


if __name__ == "__main__":
    main()
