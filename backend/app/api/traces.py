from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import AttributionReport
from ..services.container import Services

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{trace_id}/report", response_model=AttributionReport)
def get_report(trace_id: str, services: Services = Depends(get_services)) -> AttributionReport:
    try:
        return services.attribution.report(trace_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
