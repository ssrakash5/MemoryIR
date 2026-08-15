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


class TraceSummary(BaseModel):
    trace_id: str
    user_query: str
    decision: str | None = None
    status: str
    started_at: str
    completed_at: str | None = None
    guarded: bool
    flagged: bool
    causal_precision: float | None = None
    causal_recall: float | None = None
    proxy_citation_rate: float | None = None
    ground_path: str | None = None


class DashboardSummary(BaseModel):
    total_actions: int
    guarded_actions: int
    flagged_actions: int
    avg_causal_precision: float | None = None
    avg_proxy_citation_rate: float | None = None
    recent: list[TraceSummary] = Field(default_factory=list)
