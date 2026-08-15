from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..deps import get_services
from ..services.container import Services

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("")
def evaluation_summary(services: Services = Depends(get_services)) -> dict[str, Any]:
    return services.evaluation.summary()
