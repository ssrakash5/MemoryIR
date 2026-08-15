from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import ForensicRequest, ForensicResponse
from ..services.container import Services

router = APIRouter(prefix="/forensics", tags=["forensics"])


@router.post("/{trace_id}", response_model=ForensicResponse)
def investigate_trace(
    trace_id: str,
    payload: ForensicRequest,
    services: Services = Depends(get_services),
) -> ForensicResponse:
    try:
        return services.investigator.investigate(trace_id, payload.question)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
