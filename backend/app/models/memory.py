from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    memory_type: str = "raw"
    generation: int = 0
    agent_id: str | None = None
    session_id: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRead(BaseModel):
    memory_id: str
    display_id: str
    agent_id: str
    session_id: str | None = None
    source_id: str | None = None
    memory_type: str
    content: str
    generation: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class MemoryEdgeRead(BaseModel):
    edge_id: str
    parent_memory_id: str
    parent_display_id: str | None = None
    child_memory_id: str
    child_display_id: str | None = None
    relation_type: str
    declared_weight: float | None = None
    depth: int = 1


class LineageResponse(BaseModel):
    memory: MemoryRead
    ancestors: list[MemoryRead]
    edges: list[MemoryEdgeRead]
    max_depth: int
