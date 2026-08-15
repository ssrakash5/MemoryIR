"""Real, reproducible causal-attribution benchmark.

Loads the structured scenarios in eval/cases/ and drives every one through
the actual production pipeline (QueryEngine, InterventionEngine,
AttributionEngine). Nothing here is a hand-authored number -- every value
returned by `run_suite()` comes from executing the real code path.

Shared by the standalone CLI (eval/run_causal_eval.py) and the live
/api/evaluation endpoint, so the UI and the reproducible script can never
drift apart.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .attribution import AttributionEngine
from .generator import QueryEngine
from .interventions import InterventionEngine
from .llm import GenerationResult, MemoryAttribution
from .memory_store import InMemoryMemoryStore

ANCHOR = [1.0, 0.0, 0.0]
FAR_A = [0.0, 1.0, 0.0]
FAR_B = [0.0, 0.0, 1.0]


class ScenarioProvider:
    """Marker-based stand-in provider: the decision flips exactly when the
    case's unique marker string is no longer present in the memories the
    agent was given. Same shape as the shipped MockProvider's keyword-driven
    decision rule, generalized to arbitrary structured cases.
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
        claims = [
            MemoryAttribution(
                memory_id=memory.memory_id,
                importance=1,
                reason="Consolidated summary cited as reason.",
            )
            for memory in memories
            if memory.display_id == self.claimed_display
        ]
        return GenerationResult(
            answer=decision,
            decision=decision,
            response_text=f"Decision: {decision}",
            memory_attribution=claims,
        )


def load_cases(cases_dir: Path) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(cases_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    cases.append(json.loads(line))
    return cases


def run_case(case: dict[str, Any]) -> dict[str, Any]:
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
    interventions = intervention_engine.run(trace_id)
    report = attribution.report(trace_id)

    ancestor_hit = None
    if report.ground_provenance:
        ancestor_hit = report.ground_provenance[0]["ancestor"]

    is_derived = len(derived_path) > 1
    memoryir_belief = ancestor_hit if (is_derived and ancestor_hit) else claimed_display
    memoryir_correct = memoryir_belief == ground_display
    naive_correct = claimed_display == ground_display

    retrieved_ablations = [i for i in interventions if i.intervention_type == "RETRIEVED_MEMORY_ABLATION"]
    flips = sum(1 for i in retrieved_ablations if i.decision_changed)
    latencies = [i.latency_ms for i in interventions if i.latency_ms is not None]

    return {
        "case_id": case["case_id"],
        "scenario_type": case["scenario_type"],
        "decision_correct": report.decision == case["expected_decision"],
        "causal_precision": report.causal_precision,
        "causal_recall": report.causal_recall,
        "proxy_citation_rate": report.proxy_citation_rate,
        "average_provenance_depth": report.average_provenance_depth,
        "expected_ground_ancestor": ground_display if is_derived else None,
        "found_ancestor": ancestor_hit,
        "found_true_root": (ancestor_hit == ground_display) if is_derived else None,
        "naive_correct": naive_correct,
        "memoryir_correct": memoryir_correct,
        "chain_length": len(derived_path) - 1,
        "ablation_flip_count": flips,
        "ablation_count": len(retrieved_ablations),
        "latencies_ms": latencies,
    }


def run_suite(cases_dir: Path) -> dict[str, Any]:
    cases = load_cases(cases_dir)
    results = [run_case(case) for case in cases]

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        by_type[row["scenario_type"]].append(row)

    by_scenario_type = {}
    for scenario_type, rows in sorted(by_type.items()):
        root_eligible = [r for r in rows if r["expected_ground_ancestor"] is not None]
        found_true_root = sum(1 for r in root_eligible if r["found_true_root"])
        by_scenario_type[scenario_type] = {
            "case_count": len(rows),
            "decision_correct": f"{sum(r['decision_correct'] for r in rows)}/{len(rows)}",
            "avg_causal_precision": _avg([r["causal_precision"] for r in rows]),
            "avg_causal_recall": _avg([r["causal_recall"] for r in rows]),
            "avg_proxy_citation_rate": _avg([r["proxy_citation_rate"] for r in rows]),
            "chain_length": rows[0]["chain_length"],
            "found_true_root_ancestor": (
                f"{found_true_root}/{len(root_eligible)}" if root_eligible else "n/a (no derivation)"
            ),
        }

    all_latencies = [ms for row in results for ms in row["latencies_ms"]]
    total_ablations = sum(row["ablation_count"] for row in results)
    total_flips = sum(row["ablation_flip_count"] for row in results)
    naive_correct = sum(1 for row in results if row["naive_correct"])
    memoryir_correct = sum(1 for row in results if row["memoryir_correct"])

    metrics = {
        "causal_precision": _avg([r["causal_precision"] for r in results]),
        "causal_recall": _avg([r["causal_recall"] for r in results]),
        "proxy_citation_rate": _avg([r["proxy_citation_rate"] for r in results]),
        "average_provenance_depth": _avg([r["average_provenance_depth"] for r in results]),
        "decision_flip_rate": round(total_flips / total_ablations, 4) if total_ablations else 0.0,
        "intervention_latency_ms": round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else 0.0,
    }

    comparison = [
        {
            "method": "Naive citation (agent's claimed memory)",
            "causal_precision": round(naive_correct / len(results), 4) if results else 0.0,
            "causal_recall": round(naive_correct / len(results), 4) if results else 0.0,
        },
        {
            "method": "MemoryIR (ground-traced provenance)",
            "causal_precision": round(memoryir_correct / len(results), 4) if results else 0.0,
            "causal_recall": round(memoryir_correct / len(results), 4) if results else 0.0,
        },
    ]

    return {
        "label": "controlled causal-attribution benchmark",
        "case_count": len(results),
        "scenario_types": sorted(by_type.keys()),
        "metrics": metrics,
        "comparison": comparison,
        "by_scenario_type": by_scenario_type,
        "cases": cases[:8],
    }


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
