from __future__ import annotations

from .llm import GenerationResult, ModelProvider
from .memory_store import DEFAULT_AGENT_ID, DEFAULT_SESSION_ID, MemoryRecord, Timer


class QueryEngine:
    def __init__(self, store: object, provider: ModelProvider) -> None:
        self.store = store
        self.provider = provider

    def query(self, *, query: str, top_k: int, agent_id: str | None = None):
        resolved_agent_id, default_session_id, _ = self.store.ensure_default_agent(self.provider.model_id)
        resolved_agent_id = agent_id or resolved_agent_id or DEFAULT_AGENT_ID
        trace = self.store.create_trace(
            agent_id=resolved_agent_id,
            session_id=default_session_id or DEFAULT_SESSION_ID,
            user_query=query,
            model_id=self.provider.model_id,
            temperature=0.0,
        )
        with Timer() as timer:
            query_embedding = self.provider.embed(query)
            retrieved = self.store.vector_search(
                agent_id=resolved_agent_id,
                embedding=query_embedding,
                top_k=top_k,
                query_text=query,
            )
        self.store.create_retrieval_run(
            trace_id=trace.trace_id,
            query_text=query,
            top_k=top_k,
            embedding_model=self.provider.embedding_model_id,
            items=retrieved,
            latency_ms=timer.latency_ms,
        )
        result = self.generate_with_memories(query=query, memories=[item.memory for item in retrieved])
        self.store.create_claims(
            trace_id=trace.trace_id,
            claims=[
                (claim.memory_id, claim.importance, claim.reason)
                for claim in result.memory_attribution
            ],
        )
        self.store.complete_trace(
            trace.trace_id,
            response_text=result.response_text,
            decision_label=result.decision,
        )
        return trace.trace_id, result, retrieved

    def generate_with_memories(self, *, query: str, memories: list[MemoryRecord]) -> GenerationResult:
        return self.provider.generate(query=query, memories=memories)
