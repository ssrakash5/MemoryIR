from __future__ import annotations

from ..models import (
    ClaimedMemory,
    InterventionRead,
    MemoryEdgeRead,
    MemoryRead,
    RetrievedMemory,
)
from .memory_store import (
    ClaimRecord,
    InterventionRecord,
    MemoryEdgeRecord,
    MemoryRecord,
    RetrievedItemRecord,
)


def memory_to_read(memory: MemoryRecord) -> MemoryRead:
    return MemoryRead(
        memory_id=memory.memory_id,
        display_id=memory.display_id,
        agent_id=memory.agent_id,
        session_id=memory.session_id,
        source_id=memory.source_id,
        memory_type=memory.memory_type,
        content=memory.content,
        generation=memory.generation,
        metadata=memory.metadata,
        created_at=memory.created_at,
    )


def edge_to_read(edge: MemoryEdgeRecord, store: object) -> MemoryEdgeRead:
    parent_display = None
    child_display = None
    try:
        parent_display = store.get_memory(edge.parent_memory_id).display_id
        child_display = store.get_memory(edge.child_memory_id).display_id
    except Exception:
        pass
    return MemoryEdgeRead(
        edge_id=edge.edge_id,
        parent_memory_id=edge.parent_memory_id,
        parent_display_id=parent_display,
        child_memory_id=edge.child_memory_id,
        child_display_id=child_display,
        relation_type=edge.relation_type,
        declared_weight=edge.declared_weight,
        depth=edge.depth,
    )


def retrieved_to_read(item: RetrievedItemRecord) -> RetrievedMemory:
    base = memory_to_read(item.memory).model_dump()
    return RetrievedMemory(
        **base,
        retrieval_rank=item.retrieval_rank,
        vector_distance=item.vector_distance,
    )


def claim_to_read(claim: ClaimRecord, store: object) -> ClaimedMemory:
    display_id = claim.memory_id or "unknown"
    if claim.memory_id:
        try:
            display_id = store.get_memory(claim.memory_id).display_id
        except Exception:
            pass
    return ClaimedMemory(
        memory_id=claim.memory_id or "",
        display_id=display_id,
        claim_type=claim.claim_type,
        claimed_rank=claim.claimed_rank,
        explanation=claim.explanation,
    )


def intervention_to_read(intervention: InterventionRecord, store: object) -> InterventionRead:
    display_id = None
    if intervention.target_memory_id:
        try:
            display_id = store.get_memory(intervention.target_memory_id).display_id
        except Exception:
            display_id = intervention.target_memory_id[:8]
    return InterventionRead(
        intervention_id=intervention.intervention_id,
        trace_id=intervention.trace_id,
        intervention_type=intervention.intervention_type,
        target_memory_id=intervention.target_memory_id,
        target_display_id=display_id,
        target_depth=intervention.target_depth,
        baseline_decision=intervention.baseline_decision,
        counterfactual_decision=intervention.counterfactual_decision,
        baseline_response=intervention.baseline_response,
        counterfactual_response=intervention.counterfactual_response,
        decision_changed=intervention.decision_changed,
        semantic_delta=intervention.semantic_delta,
        effect_score=intervention.effect_score,
        latency_ms=intervention.latency_ms,
    )
