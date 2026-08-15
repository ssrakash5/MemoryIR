from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .memory import MemoryRead


class RetrievedMemory(MemoryRead):
    retrieval_rank: int
    vector_distance: float


class ClaimedMemory(BaseModel):
    memory_id: str
    display_id: str
    claim_type: str = "memory_attribution"
    claimed_rank: int
    explanation: str


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 5
    agent_id: str | None = None


class QueryResponse(BaseModel):
    trace_id: str
    answer: str
    decision: str
    retrieved: list[RetrievedMemory]
    claimed: list[ClaimedMemory]


class ConsolidationRequest(BaseModel):
    memory_ids: list[str] = Field(min_length=1)
    agent_id: str | None = None
    session_id: str | None = None


class ConsolidationResponse(BaseModel):
    consolidation_id: str
    output_memory_id: str
    display_id: str
    content: str
    generation: int


class InterventionRead(BaseModel):
    intervention_id: str
    trace_id: str
    intervention_type: str
    target_memory_id: str | None = None
    target_display_id: str | None = None
    target_depth: int = 0
    baseline_decision: str | None = None
    counterfactual_decision: str | None = None
    baseline_response: str | None = None
    counterfactual_response: str | None = None
    decision_changed: bool = False
    semantic_delta: float | None = None
    effect_score: float | None = None
    latency_ms: int | None = None


class ForensicRequest(BaseModel):
    question: str = "Why was the decision made?"


class ForensicResponse(BaseModel):
    trace_id: str
    question: str
    answer: str
    mcp_calls: list[dict[str, Any]]
    mode: str
