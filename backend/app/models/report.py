from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AttributionReport(BaseModel):
    trace_id: str
    decision: str | None
    claimed_memories: list[str] = Field(default_factory=list)
    retrieved_memories: list[str] = Field(default_factory=list)
    influential_memories: list[str] = Field(default_factory=list)
    claim_retrieval_precision: float
    causal_precision: float
    causal_recall: float
    proxy_citation_rate: float
    average_provenance_depth: float
    ground_provenance: list[dict[str, Any]] = Field(default_factory=list)
