from __future__ import annotations

from ..models import AttributionReport


class AttributionEngine:
    def __init__(self, store: object) -> None:
        self.store = store

    def report(self, trace_id: str) -> AttributionReport:
        trace = self.store.get_trace(trace_id)
        retrieved_items = self.store.get_latest_retrieval_items(trace_id)
        claims = self.store.get_claims(trace_id)
        interventions = self.store.list_interventions(trace_id)

        retrieved_ids = [item.memory.memory_id for item in retrieved_items]
        retrieved_display = [item.memory.display_id for item in retrieved_items]
        claimed_ids = [claim.memory_id for claim in claims if claim.memory_id]
        claimed_display = [
            self.store.get_memory(memory_id).display_id
            for memory_id in claimed_ids
        ]
        influential_ids = [
            intervention.target_memory_id
            for intervention in interventions
            if intervention.intervention_type == "RETRIEVED_MEMORY_ABLATION"
            and intervention.decision_changed
            and intervention.target_memory_id
        ]
        influential_display = [
            self.store.get_memory(memory_id).display_id
            for memory_id in influential_ids
        ]
        ground = self._ground_provenance(influential_ids, interventions)
        proxy_count = 0
        for claimed_id in claimed_ids:
            if any(item["retrieved_memory_id"] == claimed_id for item in ground):
                proxy_count += 1

        return AttributionReport(
            trace_id=trace_id,
            decision=trace.decision_label,
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

    def _ground_provenance(self, influential_ids: list[str], interventions) -> list[dict]:
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
                lineage_edges = self.store.ancestry(influential_id)
                matching = [
                    edge for edge in lineage_edges if edge.parent_memory_id == ancestor_id
                ]
                if not matching:
                    continue
                edge = sorted(matching, key=lambda item: item.depth)[0]
                influential = self.store.get_memory(influential_id)
                ancestor = self.store.get_memory(ancestor_id)
                out.append(
                    {
                        "retrieved": influential.display_id,
                        "retrieved_memory_id": influential.memory_id,
                        "ancestor": ancestor.display_id,
                        "ancestor_memory_id": ancestor.memory_id,
                        "depth": edge.depth,
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
