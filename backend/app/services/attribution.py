from __future__ import annotations

from collections import defaultdict

from ..models import AttributionReport


class AttributionEngine:
    def __init__(self, store: object) -> None:
        self.store = store

    def report(self, trace_id: str) -> AttributionReport:
        trace = self.store.get_trace(trace_id)
        retrieved_items = self.store.get_latest_retrieval_items(trace_id)
        claims = self.store.get_claims(trace_id)
        interventions = self.store.list_interventions(trace_id)
        memories_by_id = {item.memory.memory_id: item.memory for item in retrieved_items}
        for claim in claims:
            if claim.memory_id and claim.memory_id not in memories_by_id:
                memories_by_id[claim.memory_id] = self.store.get_memory(claim.memory_id)
        for intervention in interventions:
            if intervention.target_memory_id and intervention.target_memory_id not in memories_by_id:
                memories_by_id[intervention.target_memory_id] = self.store.get_memory(intervention.target_memory_id)
        children_to_parents: dict[str, list[str]] = defaultdict(list)
        for edge in self.store.list_edges():
            children_to_parents[edge.child_memory_id].append(edge.parent_memory_id)
        return self._compute_report(
            trace_id, trace.decision_label, retrieved_items, claims, interventions, memories_by_id, children_to_parents
        )

    def report_bulk(
        self,
        traces: list,
        interventions_by_trace: dict[str, list],
    ) -> dict[str, AttributionReport]:
        """Same computation as report(), but for many traces at once using
        pre-batched queries. Calling report() once per trace on a remote
        database means N+1 round trips; a dashboard covering dozens of
        traces makes that the dominant cost of the page. This fetches
        retrieval items, claims, all memories, and all edges once each,
        regardless of how many traces are being summarized.
        """
        guarded_ids = [trace.trace_id for trace in traces if interventions_by_trace.get(trace.trace_id)]
        if not guarded_ids:
            return {}
        retrieval_by_trace = self.store.get_latest_retrieval_items_bulk(guarded_ids)
        claims_by_trace = self.store.get_claims_bulk(guarded_ids)
        memories_by_id = {memory.memory_id: memory for memory in self.store.list_memories()}
        children_to_parents: dict[str, list[str]] = defaultdict(list)
        for edge in self.store.list_edges():
            children_to_parents[edge.child_memory_id].append(edge.parent_memory_id)

        reports: dict[str, AttributionReport] = {}
        for trace in traces:
            if trace.trace_id not in guarded_ids:
                continue
            reports[trace.trace_id] = self._compute_report(
                trace.trace_id,
                trace.decision_label,
                retrieval_by_trace.get(trace.trace_id, []),
                claims_by_trace.get(trace.trace_id, []),
                interventions_by_trace.get(trace.trace_id, []),
                memories_by_id,
                children_to_parents,
            )
        return reports

    def _compute_report(
        self,
        trace_id: str,
        decision: str | None,
        retrieved_items,
        claims,
        interventions,
        memories_by_id: dict,
        children_to_parents: dict[str, list[str]],
    ) -> AttributionReport:
        def display_of(memory_id: str) -> str:
            memory = memories_by_id.get(memory_id)
            return memory.display_id if memory else memory_id[:8]

        retrieved_ids = [item.memory.memory_id for item in retrieved_items]
        retrieved_display = [item.memory.display_id for item in retrieved_items]
        claimed_ids = [claim.memory_id for claim in claims if claim.memory_id]
        claimed_display = [display_of(memory_id) for memory_id in claimed_ids]
        influential_ids = [
            intervention.target_memory_id
            for intervention in interventions
            if intervention.intervention_type == "RETRIEVED_MEMORY_ABLATION"
            and intervention.decision_changed
            and intervention.target_memory_id
        ]
        influential_display = [display_of(memory_id) for memory_id in influential_ids]

        ground = self._ground_provenance(influential_ids, interventions, memories_by_id, children_to_parents)
        proxy_count = 0
        for claimed_id in claimed_ids:
            if any(item["retrieved_memory_id"] == claimed_id for item in ground):
                proxy_count += 1

        return AttributionReport(
            trace_id=trace_id,
            decision=decision,
            claimed_memories=claimed_display,
            retrieved_memories=retrieved_display,
            influential_memories=influential_display,
            claim_retrieval_precision=_ratio(len(set(claimed_ids) & set(retrieved_ids)), len(claimed_ids)),
            causal_precision=_ratio(len(set(claimed_ids) & set(influential_ids)), len(claimed_ids)),
            causal_recall=_ratio(len(set(claimed_ids) & set(influential_ids)), len(influential_ids)),
            proxy_citation_rate=_ratio(proxy_count, len(claimed_ids)),
            average_provenance_depth=_average([item["depth"] for item in ground]),
            ground_provenance=ground,
        )

    def _ground_provenance(
        self,
        influential_ids: list[str],
        interventions,
        memories_by_id: dict,
        children_to_parents: dict[str, list[str]],
    ) -> list[dict]:
        out = []
        ancestor_interventions = [
            intervention
            for intervention in interventions
            if intervention.intervention_type == "ANCESTOR_ABLATION"
            and intervention.decision_changed
            and intervention.target_memory_id
        ]
        for ancestor_run in ancestor_interventions:
            ancestor_id = ancestor_run.target_memory_id
            for influential_id in influential_ids:
                if ancestor_id not in children_to_parents.get(influential_id, []):
                    continue
                influential = memories_by_id.get(influential_id)
                ancestor = memories_by_id.get(ancestor_id)
                if influential is None or ancestor is None:
                    continue
                out.append(
                    {
                        "retrieved": influential.display_id,
                        "retrieved_memory_id": influential.memory_id,
                        "ancestor": ancestor.display_id,
                        "ancestor_memory_id": ancestor.memory_id,
                        "depth": 1,
                        "decision_changed": True,
                        "path": [ancestor.display_id, influential.display_id, "Decision"],
                    }
                )
        return out


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
