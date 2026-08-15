from __future__ import annotations

from dataclasses import replace

from .generator import QueryEngine
from .llm import ModelProvider
from .memory_store import MemoryRecord, Timer


class InterventionEngine:
    def __init__(self, store: object, provider: ModelProvider, query_engine: QueryEngine) -> None:
        self.store = store
        self.provider = provider
        self.query_engine = query_engine

    def run(self, trace_id: str, *, force: bool = False):
        existing = self.store.list_interventions(trace_id)
        if existing and not force:
            return existing

        trace = self.store.get_trace(trace_id)
        retrieved_items = self.store.get_latest_retrieval_items(trace_id)
        retrieved_memories = [item.memory for item in retrieved_items]
        created = []

        for item in retrieved_items:
            target = item.memory
            counterfactual_context = [
                memory for memory in retrieved_memories if memory.memory_id != target.memory_id
            ]
            with Timer() as timer:
                result = self.query_engine.generate_with_memories(
                    query=trace.user_query,
                    memories=counterfactual_context,
                )
            changed = result.decision != trace.decision_label
            created.append(
                self.store.create_intervention(
                    trace_id=trace_id,
                    intervention_type="RETRIEVED_MEMORY_ABLATION",
                    target_memory_id=target.memory_id,
                    target_depth=0,
                    baseline_decision=trace.decision_label,
                    counterfactual_decision=result.decision,
                    baseline_response=trace.response_text,
                    counterfactual_response=result.response_text,
                    decision_changed=changed,
                    semantic_delta=1.0 if changed else 0.0,
                    effect_score=1.0 if changed else 0.0,
                    latency_ms=timer.latency_ms,
                )
            )
            if changed:
                created.extend(self._run_ancestor_interventions(trace, target, retrieved_memories))

        return created

    def _run_ancestor_interventions(
        self,
        trace,
        influential_memory: MemoryRecord,
        retrieved_memories: list[MemoryRecord],
    ):
        direct_edges = [
            edge
            for edge in self.store.ancestry(influential_memory.memory_id)
            if edge.child_memory_id == influential_memory.memory_id and edge.depth == 1
        ]
        created = []
        for edge in direct_edges:
            ancestor = self.store.get_memory(edge.parent_memory_id)
            sibling_parents = [
                self.store.get_memory(other.parent_memory_id)
                for other in direct_edges
                if other.parent_memory_id != ancestor.memory_id
            ]
            replacement = self._recomputed_memory(influential_memory, sibling_parents, ancestor)
            counterfactual_context = [
                replacement if memory.memory_id == influential_memory.memory_id else memory
                for memory in retrieved_memories
            ]
            with Timer() as timer:
                result = self.query_engine.generate_with_memories(
                    query=trace.user_query,
                    memories=counterfactual_context,
                )
            changed = result.decision != trace.decision_label
            created.append(
                self.store.create_intervention(
                    trace_id=trace.trace_id,
                    intervention_type="ANCESTOR_ABLATION",
                    target_memory_id=ancestor.memory_id,
                    target_depth=edge.depth,
                    baseline_decision=trace.decision_label,
                    counterfactual_decision=result.decision,
                    baseline_response=trace.response_text,
                    counterfactual_response=result.response_text,
                    decision_changed=changed,
                    semantic_delta=1.0 if changed else 0.0,
                    effect_score=1.0 if changed else 0.0,
                    latency_ms=timer.latency_ms,
                )
            )
        return created

    def _recomputed_memory(
        self,
        original: MemoryRecord,
        remaining_parents: list[MemoryRecord],
        removed_parent: MemoryRecord,
    ) -> MemoryRecord:
        if remaining_parents:
            content = self.provider.consolidate(remaining_parents)
        else:
            content = "No derived memory remains after removing the only parent."
        return replace(
            original,
            content=content,
            embedding=self.provider.embed(content),
            metadata={
                **original.metadata,
                "counterfactual_without": removed_parent.memory_id,
                "counterfactual_without_display_id": removed_parent.display_id,
            },
        )
