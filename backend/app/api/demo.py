from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..deps import get_services
from ..services.container import Services
from ..services.serializers import memory_to_read

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset")
def reset_demo(services: Services = Depends(get_services)) -> dict[str, Any]:
    result = services.store.seed_demo(services.provider)
    return {
        "agent_id": result["agent_id"],
        "session_id": result["session_id"],
        "memories": [memory_to_read(memory).model_dump() for memory in result["memories"]],
    }
