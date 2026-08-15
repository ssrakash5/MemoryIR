from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import LineageResponse, MemoryCreate, MemoryRead
from ..services.container import Services
from ..services.serializers import edge_to_read, memory_to_read

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryRead)
def create_memory(payload: MemoryCreate, services: Services = Depends(get_services)) -> MemoryRead:
    agent_id, session_id, source_id = services.store.ensure_default_agent(services.provider.model_id)
    memory = services.store.insert_memory(
        content=payload.content,
        embedding=services.provider.embed(payload.content),
        memory_type=payload.memory_type,
        generation=payload.generation,
        agent_id=payload.agent_id or agent_id,
        session_id=payload.session_id if payload.session_id is not None else session_id,
        source_id=payload.source_id if payload.source_id is not None else source_id,
        metadata=payload.metadata,
    )
    return memory_to_read(memory)


@router.get("", response_model=list[MemoryRead])
def list_memories(services: Services = Depends(get_services)) -> list[MemoryRead]:
    return [memory_to_read(memory) for memory in services.store.list_memories()]


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, services: Services = Depends(get_services)) -> MemoryRead:
    try:
        return memory_to_read(services.store.get_memory(memory_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{memory_id}/lineage", response_model=LineageResponse)
def get_lineage(memory_id: str, services: Services = Depends(get_services)) -> LineageResponse:
    try:
        memory = services.store.get_memory(memory_id)
        edges = services.store.ancestry(memory.memory_id)
        ancestor_ids = []
        for edge in edges:
            if edge.parent_memory_id not in ancestor_ids:
                ancestor_ids.append(edge.parent_memory_id)
        ancestors = [services.store.get_memory(ancestor_id) for ancestor_id in ancestor_ids]
        return LineageResponse(
            memory=memory_to_read(memory),
            ancestors=[memory_to_read(ancestor) for ancestor in ancestors],
            edges=[edge_to_read(edge, services.store) for edge in edges],
            max_depth=max([edge.depth for edge in edges], default=0),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
