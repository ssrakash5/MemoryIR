from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import ConsolidationRequest, ConsolidationResponse
from ..services.container import Services

router = APIRouter(prefix="/consolidations", tags=["consolidations"])


@router.post("", response_model=ConsolidationResponse)
def create_consolidation(
    payload: ConsolidationRequest,
    services: Services = Depends(get_services),
) -> ConsolidationResponse:
    try:
        consolidation, output = services.consolidator.consolidate(
            memory_ids=payload.memory_ids,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConsolidationResponse(
        consolidation_id=consolidation.consolidation_id,
        output_memory_id=output.memory_id,
        display_id=output.display_id,
        content=output.content,
        generation=output.generation,
    )


@router.get("/{consolidation_id}", response_model=ConsolidationResponse)
def get_consolidation(
    consolidation_id: str,
    services: Services = Depends(get_services),
) -> ConsolidationResponse:
    try:
        consolidation = services.store.get_consolidation(consolidation_id)
        output = services.store.get_memory(consolidation.output_memory_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConsolidationResponse(
        consolidation_id=consolidation.consolidation_id,
        output_memory_id=output.memory_id,
        display_id=output.display_id,
        content=output.content,
        generation=output.generation,
    )
