from __future__ import annotations


def test_demo_retrieval_orders_controlled_trace_memories(services):
    agent_id, _, _ = services.store.ensure_default_agent(services.provider.model_id)
    query = "Which database architecture best satisfies the project requirements?"
    retrieved = services.store.vector_search(
        agent_id=agent_id,
        embedding=services.provider.embed(query),
        top_k=3,
        query_text=query,
    )

    assert [item.memory.display_id for item in retrieved] == ["M7", "M12", "M16"]
