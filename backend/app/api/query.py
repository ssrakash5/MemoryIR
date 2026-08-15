from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_services
from ..models import ClaimedMemory, QueryRequest, QueryResponse
from ..services.container import Services
from ..services.serializers import retrieved_to_read

router = APIRouter(tags=["agent"])


@router.post("/query", response_model=QueryResponse)
def query_agent(payload: QueryRequest, services: Services = Depends(get_services)) -> QueryResponse:
    trace_id, result, retrieved = services.query_engine.query(
        query=payload.query,
        top_k=payload.top_k,
        agent_id=payload.agent_id,
    )
    claimed = []
    for claim in result.memory_attribution:
        memory = services.store.get_memory(claim.memory_id)
        claimed.append(
            ClaimedMemory(
                memory_id=memory.memory_id,
                display_id=memory.display_id,
                claimed_rank=claim.importance,
                explanation=claim.reason,
            )
        )
    return QueryResponse(
        trace_id=trace_id,
        answer=result.answer,
        decision=result.decision,
        retrieved=[retrieved_to_read(item) for item in retrieved],
        claimed=claimed,
    )
