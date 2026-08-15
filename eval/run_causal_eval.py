"""Run every controlled scenario in eval/cases/ through MemoryIR's real
attribution pipeline (query engine, intervention engine, attribution
engine) and report aggregate, reproducible causal-detection stats.

Each case only supplies structure (derived_path, causal_ground_memory,
claimed_memory, expected_decision). This script builds an isolated
in-memory scenario per case from that structure and drives it through the
same production classes the live backend uses -- no shortcuts, no
hand-authored output.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.attribution import AttributionEngine
from app.services.generator import QueryEngine
from app.services.interventions import InterventionEngine
from app.services.llm import GenerationResult, MemoryAttribution
from app.services.memory_store import InMemoryMemoryStore

from run_eval import load_cases

ANCHOR = [1.0, 0.0, 0.0]
FAR_A = [0.0, 1.0, 0.0]
FAR_B = [0.0, 0.0, 1.0]


class ScenarioProvider:
    """Marker-based stand-in for a real LLM/embedding provider.

    Decision logic is a single rule: is the case's unique marker string
    still present in the memories the agent was actually given? This is
    the same shape as the shipped MockProvider (keyword presence drives
    the decision) generalized to arbitrary cases instead of one hardcoded
    scenario.
    """

    model_id = "eval-harness-v1"
    embedding_model_id = "eval-harness-embed"

    def __init__(self, marker: str, expected_decision: str, claimed_display: str) -> None:
        self.marker = marker
        self.expected_decision = expected_decision
        self.alt_decision = f"ALT_{expected_decision}"
        self.claimed_display = claimed_display

    def embed(self, text: str) -> list[float]:
        return ANCHOR

    def consolidate(self, memories: list) -> str:
        if not memories:
            return "No derived memory remains after removing the only parent."
        return " | ".join(memory.content for memory in memories)

    def generate(self, *, query: str, memories: list) -> GenerationResult:
        combined = " ".join(memory.content for memory in memories)
        decision = self.expected_decision if self.marker in combined else self.alt_decision
        claims = []
        for memory in memories:
            if memory.display_id == self.claimed_display:
                claims.append(
                    MemoryAttribution(
                        memory_id=memory.memory_id,
                        importance=1,
                        reason="Consolidated summary cited as reason.",
                    )
                )
        return GenerationResult(
            answer=decision,
            decision=decision,
            response_text=f"Decision: {decision}",
            memory_attribution=claims,
        )


def run_case(case: dict) -> dict:
    marker = f"MARK[{case['case_id']}]"
    derived_path = case["derived_path"]
    ground_display = derived_path[0]
    claimed_display = case["claimed_memory"]

    store = InMemoryMemoryStore()
    provider = ScenarioProvider(marker, case["expected_decision"], claimed_display)

    if len(derived_path) == 1:
        top = store.insert_memory(
            content=f"Direct policy memory ({marker}) answering: {case['query']}",
            embedding=ANCHOR,
            memory_type="raw",
            generation=0,
            metadata={"display_id": derived_path[0]},
        )
    else:
        prev = store.insert_memory(
            content=f"Ground policy memory ({marker}) answering: {case['query']}",
            embedding=None,
            memory_type="raw",
            generation=0,
            metadata={"display_id": derived_path[0]},
        )
        for depth, display_id in enumerate(derived_path[1:], start=1):
            is_top = display_id == derived_path[-1]
            content = provider.consolidate([prev])
            node = store.insert_memory(
                content=content,
                embedding=ANCHOR if is_top else None,
                memory_type="consolidated",
                generation=depth,
                metadata={"display_id": display_id},
            )
            store.insert_edge(prev.memory_id, node.memory_id, relation_type="consolidated_from")
            prev = node
        top = prev

    store.insert_memory(
        content=f"Unrelated distractor context for {case['case_id']}, item A.",
        embedding=FAR_A,
        memory_type="raw",
        generation=0,
    )
    store.insert_memory(
        content=f"Unrelated distractor context for {case['case_id']}, item B.",
        embedding=FAR_B,
        memory_type="raw",
        generation=0,
    )

    query_engine = QueryEngine(store, provider)
    intervention_engine = InterventionEngine(store, provider, query_engine)
    attribution = AttributionEngine(store)

    trace_id, result, retrieved = query_engine.query(query=case["query"], top_k=3)
    intervention_engine.run(trace_id)
    report = attribution.report(trace_id)

    ancestor_hit = None
    if report.ground_provenance:
        entry = report.ground_provenance[0]
        ancestor_hit = entry["ancestor"]

    return {
        "case_id": case["case_id"],
        "scenario_type": case["scenario_type"],
        "decision_correct": report.decision == case["expected_decision"],
        "causal_precision": report.causal_precision,
        "causal_recall": report.causal_recall,
        "proxy_citation_rate": report.proxy_citation_rate,
        "expected_ground_ancestor": ground_display if len(derived_path) > 1 else None,
        "found_ancestor": ancestor_hit,
        "found_true_root": (ancestor_hit == ground_display) if len(derived_path) > 1 else None,
        "chain_length": len(derived_path) - 1,
    }


def main() -> None:
    cases_dir = Path(__file__).parent / "cases"
    cases = load_cases(cases_dir)
    results = [run_case(case) for case in cases]

    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_type[row["scenario_type"]].append(row)

    summary = {"total_cases": len(results), "by_scenario_type": {}}
    for scenario_type, rows in sorted(by_type.items()):
        decision_correct = sum(r["decision_correct"] for r in rows)
        avg_precision = round(sum(r["causal_precision"] for r in rows) / len(rows), 4)
        avg_recall = round(sum(r["causal_recall"] for r in rows) / len(rows), 4)
        avg_proxy_rate = round(sum(r["proxy_citation_rate"] for r in rows) / len(rows), 4)
        root_eligible = [r for r in rows if r["expected_ground_ancestor"] is not None]
        found_true_root = sum(1 for r in root_eligible if r["found_true_root"])
        summary["by_scenario_type"][scenario_type] = {
            "case_count": len(rows),
            "decision_correct": f"{decision_correct}/{len(rows)}",
            "avg_causal_precision": avg_precision,
            "avg_causal_recall": avg_recall,
            "avg_proxy_citation_rate": avg_proxy_rate,
            "chain_length": rows[0]["chain_length"],
            "found_true_root_ancestor": (
                f"{found_true_root}/{len(root_eligible)}" if root_eligible else "n/a (no derivation)"
            ),
        }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
