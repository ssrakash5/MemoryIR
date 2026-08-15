from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import InterventionRead
from ..services.container import Services
from ..services.serializers import intervention_to_read

router = APIRouter(tags=["interventions"])


@router.post("/traces/{trace_id}/interventions", response_model=list[InterventionRead])
def run_interventions(
    trace_id: str,
    force: bool = False,
    services: Services = Depends(get_services),
) -> list[InterventionRead]:
    try:
        interventions = services.intervention_engine.run(trace_id, force=force)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [intervention_to_read(intervention, services.store) for intervention in interventions]


@router.get("/traces/{trace_id}/interventions", response_model=list[InterventionRead])
def list_interventions(
    trace_id: str,
    services: Services = Depends(get_services),
) -> list[InterventionRead]:
    try:
        interventions = services.store.list_interventions(trace_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [intervention_to_read(intervention, services.store) for intervention in interventions]
