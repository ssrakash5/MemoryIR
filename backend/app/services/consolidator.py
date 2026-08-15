from __future__ import annotations

from .llm import ModelProvider
from .memory_store import Timer


class Consolidator:
    def __init__(self, store: object, provider: ModelProvider) -> None:
        self.store = store
        self.provider = provider

    def consolidate(
        self,
        *,
        memory_ids: list[str],
        agent_id: str | None = None,
        session_id: str | None = None,
    ):
        parents = [self.store.get_memory(memory_id) for memory_id in memory_ids]
        if not parents:
            raise ValueError("At least one memory is required.")
        resolved_agent_id = agent_id or parents[0].agent_id
        resolved_session_id = session_id if session_id is not None else parents[0].session_id
        with Timer() as timer:
            content = self.provider.consolidate(parents)
            embedding = self.provider.embed(content)
        generation = max(memory.generation for memory in parents) + 1
        output = self.store.insert_memory(
            content=content,
            embedding=embedding,
            memory_type="consolidated",
            generation=generation,
            agent_id=resolved_agent_id,
            session_id=resolved_session_id,
            source_id=parents[0].source_id,
            metadata={"input_memory_ids": [memory.memory_id for memory in parents]},
        )
        for index, parent in enumerate(parents, start=1):
            self.store.insert_edge(
                parent.memory_id,
                output.memory_id,
                relation_type="consolidated_from",
                declared_weight=round(1.0 / len(parents), 4),
            )
        consolidation = self.store.create_consolidation(
            agent_id=resolved_agent_id,
            session_id=resolved_session_id,
            output_memory_id=output.memory_id,
            model_id=self.provider.model_id,
            prompt_version="consolidation-v1",
            input_count=len(parents),
            latency_ms=timer.latency_ms,
        )
        return consolidation, output
