from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..config import Settings
from .causal_eval import load_cases, run_suite


class EvaluationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def summary(self) -> dict[str, Any]:
        cases_dir = self.settings.repo_root / "eval" / "cases"
        if not cases_dir.exists():
            return {
                "label": "controlled causal-attribution benchmark",
                "case_count": 0,
                "scenario_types": [],
                "metrics": {},
                "comparison": [],
                "cases": [],
            }
        return _run_suite_cached(str(cases_dir))

    def load_cases(self) -> list[dict[str, Any]]:
        cases_dir = self.settings.repo_root / "eval" / "cases"
        if not cases_dir.exists():
            return []
        return load_cases(cases_dir)


@lru_cache(maxsize=1)
def _run_suite_cached(cases_dir: str) -> dict[str, Any]:
    from pathlib import Path

    return run_suite(Path(cases_dir))
