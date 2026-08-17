from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from .. import db
from ..config import Settings


DEFAULT_AGENT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_SESSION_ID = "00000000-0000-0000-0000-000000000002"
DEFAULT_SOURCE_ID = "00000000-0000-0000-0000-000000000003"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def display_from_metadata(memory_id: str, metadata: dict[str, Any] | None) -> str:
    if metadata and metadata.get("display_id"):
        return str(metadata["display_id"])
    return memory_id[:8]


@dataclass
class MemoryRecord:
    memory_id: str
    agent_id: str
    session_id: str | None
    source_id: str | None
    memory_type: str
    content: str
    embedding: list[float] | None
    generation: int
    content_hash: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    @property
    def display_id(self) -> str:
        return display_from_metadata(self.memory_id, self.metadata)


@dataclass
class MemoryEdgeRecord:
    edge_id: str
    parent_memory_id: str
    child_memory_id: str
    relation_type: str
    declared_weight: float | None
    depth: int = 1


@dataclass
class RetrievedItemRecord:
    retrieval_id: str
    memory: MemoryRecord
    retrieval_rank: int
    vector_distance: float


@dataclass
class ClaimRecord:
    claim_id: str
    trace_id: str
    memory_id: str | None
    claim_type: str
    claimed_rank: int
    explanation: str


@dataclass
class TraceRecord:
    trace_id: str
    agent_id: str
    session_id: str | None
    user_query: str
    response_text: str | None = None
    decision_label: str | None = None
    model_id: str | None = None
    temperature: float = 0.0
    status: str = "running"
    started_at: str = field(default_factory=utc_now)
    completed_at: str | None = None


@dataclass
class InterventionRecord:
    intervention_id: str
    trace_id: str
    intervention_type: str
    target_memory_id: str | None
    target_depth: int
    baseline_decision: str | None
    counterfactual_decision: str | None
    baseline_response: str | None
    counterfactual_response: str | None
    decision_changed: bool
    semantic_delta: float | None
    effect_score: float | None
    latency_ms: int | None
    created_at: str = field(default_factory=utc_now)


@dataclass
class ConsolidationRecord:
    consolidation_id: str
    agent_id: str
    session_id: str | None
    output_memory_id: str
    model_id: str
    prompt_version: str
    input_count: int
    latency_ms: int | None
    created_at: str = field(default_factory=utc_now)


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.agents: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.sources: dict[str, dict[str, Any]] = {}
        self.memories: dict[str, MemoryRecord] = {}
        self.display_to_memory_id: dict[str, str] = {}
        self.edges: list[MemoryEdgeRecord] = []
        self.traces: dict[str, TraceRecord] = {}
        self.retrieval_items: dict[str, list[RetrievedItemRecord]] = {}
        self.trace_retrieval_ids: dict[str, list[str]] = {}
        self.claims: dict[str, list[ClaimRecord]] = {}
        self.interventions: dict[str, list[InterventionRecord]] = {}
        self.consolidations: dict[str, ConsolidationRecord] = {}
        self._next_label = 1
        self.ensure_default_agent("mock")

    def ensure_default_agent(self, model_id: str) -> tuple[str, str, str]:
        self.agents.setdefault(
            DEFAULT_AGENT_ID,
            {
                "agent_id": DEFAULT_AGENT_ID,
                "name": "MemoryIR Demo Agent",
                "description": "Hackathon demo agent for memory forensics.",
                "model_id": model_id,
            },
        )
        self.sessions.setdefault(
            DEFAULT_SESSION_ID,
            {
                "session_id": DEFAULT_SESSION_ID,
                "agent_id": DEFAULT_AGENT_ID,
                "title": "CockroachDB architecture demo",
            },
        )
        self.sources.setdefault(
            DEFAULT_SOURCE_ID,
            {
                "source_id": DEFAULT_SOURCE_ID,
                "source_type": "SYNTHETIC_EVAL",
                "source_name": "MemoryIR demo seed",
                "trust_label": "controlled",
            },
        )
        return DEFAULT_AGENT_ID, DEFAULT_SESSION_ID, DEFAULT_SOURCE_ID

    def _new_memory_id(self) -> str:
        return str(uuid.uuid4())

    def _assign_display_id(self, metadata: dict[str, Any]) -> dict[str, Any]:
        if metadata.get("display_id"):
            return metadata
        while f"M{self._next_label}" in self.display_to_memory_id:
            self._next_label += 1
        metadata = dict(metadata)
        metadata["display_id"] = f"M{self._next_label}"
        self._next_label += 1
        return metadata

    def seed_demo(self, provider: Any) -> dict[str, Any]:
        self.reset()
        agent_id, session_id, source_id = self.ensure_default_agent(provider.model_id)
        seed_rows = [
            (
                "00000000-0000-0000-0000-000000000101",
                "M1",
                "raw",
                0,
                "The team prefers PostgreSQL-compatible databases.",
            ),
            (
                "00000000-0000-0000-0000-000000000102",
                "M2",
                "raw",
                0,
                "The deployment must survive regional failures.",
            ),
            (
                "00000000-0000-0000-0000-000000000103",
                "M3",
                "raw",
                0,
                "The operations team wants a managed service.",
            ),
            (
                "00000000-0000-0000-0000-000000000107",
                "M7",
                "consolidated",
                1,
                "The application should use a managed, PostgreSQL-compatible database with multi-region resilience.",
            ),
            (
                "00000000-0000-0000-0000-000000000112",
                "M12",
                "raw",
                0,
                "The frontend team prefers TypeScript for the project.",
            ),
            (
                "00000000-0000-0000-0000-000000000116",
                "M16",
                "raw",
                0,
                "The finance team wants operational costs to stay predictable.",
            ),
        ]
        rank_bias = {"M7": 0.01, "M12": 0.02, "M16": 0.03}
        for memory_id, display_id, memory_type, generation, content in seed_rows:
            self.insert_memory(
                content=content,
                embedding=provider.embed(content),
                memory_type=memory_type,
                generation=generation,
                agent_id=agent_id,
                session_id=session_id,
                source_id=source_id,
                metadata={
                    "display_id": display_id,
                    "scenario": "cockroach_demo",
                    "demo_distance": rank_bias.get(display_id),
                    **(
                        {
                            "input_memory_ids": [
                                "00000000-0000-0000-0000-000000000101",
                                "00000000-0000-0000-0000-000000000102",
                                "00000000-0000-0000-0000-000000000103",
                            ]
                        }
                        if display_id == "M7"
                        else {}
                    ),
                },
                memory_id=memory_id,
            )
        for parent_id, weight in [
            ("00000000-0000-0000-0000-000000000101", 0.25),
            ("00000000-0000-0000-0000-000000000102", 0.50),
            ("00000000-0000-0000-0000-000000000103", 0.25),
        ]:
            self.insert_edge(
                parent_id,
                "00000000-0000-0000-0000-000000000107",
                relation_type="consolidated_from",
                declared_weight=weight,
            )
        consolidation_id = "00000000-0000-0000-0000-000000000207"
        self.consolidations[consolidation_id] = ConsolidationRecord(
            consolidation_id=consolidation_id,
            agent_id=agent_id,
            session_id=session_id,
            output_memory_id="00000000-0000-0000-0000-000000000107",
            model_id=provider.model_id,
            prompt_version="demo-seed-v1",
            input_count=3,
            latency_ms=0,
        )
        return {"agent_id": agent_id, "session_id": session_id, "memories": self.list_memories()}

    def resolve_memory_id(self, memory_id_or_display: str) -> str:
        if memory_id_or_display in self.memories:
            return memory_id_or_display
        if memory_id_or_display in self.display_to_memory_id:
            return self.display_to_memory_id[memory_id_or_display]
        raise KeyError(f"Unknown memory: {memory_id_or_display}")

    def insert_memory(
        self,
        *,
        content: str,
        embedding: list[float] | None,
        memory_type: str = "raw",
        generation: int = 0,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
    ) -> MemoryRecord:
        default_agent, default_session, default_source = self.ensure_default_agent("mock")
        metadata = self._assign_display_id(metadata or {})
        memory = MemoryRecord(
            memory_id=memory_id or self._new_memory_id(),
            agent_id=agent_id or default_agent,
            session_id=session_id if session_id is not None else default_session,
            source_id=source_id if source_id is not None else default_source,
            memory_type=memory_type,
            content=content,
            embedding=embedding,
            generation=generation,
            content_hash=content_hash(content),
            metadata=metadata,
            created_at=utc_now(),
        )
        self.memories[memory.memory_id] = memory
        self.display_to_memory_id[memory.display_id] = memory.memory_id
        return memory

    def list_memories(self, agent_id: str | None = None) -> list[MemoryRecord]:
        memories = list(self.memories.values())
        if agent_id:
            memories = [m for m in memories if m.agent_id == agent_id]
        return sorted(memories, key=lambda m: (m.created_at or "", m.display_id))

    def get_memory(self, memory_id_or_display: str) -> MemoryRecord:
        return self.memories[self.resolve_memory_id(memory_id_or_display)]

    def insert_edge(
        self,
        parent_memory_id: str,
        child_memory_id: str,
        *,
        relation_type: str,
        declared_weight: float | None = None,
    ) -> MemoryEdgeRecord:
        parent_id = self.resolve_memory_id(parent_memory_id)
        child_id = self.resolve_memory_id(child_memory_id)
        for edge in self.edges:
            if (
                edge.parent_memory_id == parent_id
                and edge.child_memory_id == child_id
                and edge.relation_type == relation_type
            ):
                return edge
        edge = MemoryEdgeRecord(
            edge_id=str(uuid.uuid4()),
            parent_memory_id=parent_id,
            child_memory_id=child_id,
            relation_type=relation_type,
            declared_weight=declared_weight,
        )
        self.edges.append(edge)
        return edge

    def list_edges(self) -> list[MemoryEdgeRecord]:
        return list(self.edges)

    def ancestry(self, memory_id_or_display: str) -> list[MemoryEdgeRecord]:
        target_id = self.resolve_memory_id(memory_id_or_display)
        out: list[MemoryEdgeRecord] = []
        stack: list[tuple[str, int]] = [(target_id, 1)]
        seen: set[tuple[str, str]] = set()
        while stack:
            child_id, depth = stack.pop()
            for edge in self.edges:
                if edge.child_memory_id != child_id:
                    continue
                key = (edge.parent_memory_id, edge.child_memory_id)
                if key in seen:
                    continue
                seen.add(key)
                out_edge = replace(edge, depth=depth)
                out.append(out_edge)
                stack.append((edge.parent_memory_id, depth + 1))
        return sorted(out, key=lambda e: (e.depth, self.get_memory(e.parent_memory_id).display_id))

    def vector_search(
        self,
        *,
        agent_id: str,
        embedding: list[float],
        top_k: int,
        exclude_memory_ids: set[str] | None = None,
        query_text: str = "",
    ) -> list[RetrievedItemRecord]:
        exclude = {self.resolve_memory_id(mid) for mid in (exclude_memory_ids or set())}
        scored: list[tuple[float, MemoryRecord]] = []
        for memory in self.list_memories(agent_id=agent_id):
            if memory.memory_id in exclude or memory.embedding is None:
                continue
            if query_text and "database architecture" in query_text.lower():
                demo_distance = memory.metadata.get("demo_distance")
                if demo_distance is not None:
                    scored.append((float(demo_distance), memory))
                    continue
            scored.append((_cosine_distance(embedding, memory.embedding), memory))
        scored.sort(key=lambda item: (item[0], item[1].display_id))
        retrieval_id = str(uuid.uuid4())
        return [
            RetrievedItemRecord(
                retrieval_id=retrieval_id,
                memory=memory,
                retrieval_rank=idx,
                vector_distance=round(distance, 6),
            )
            for idx, (distance, memory) in enumerate(scored[:top_k], start=1)
        ]

    def create_trace(
        self,
        *,
        agent_id: str,
        session_id: str | None,
        user_query: str,
        model_id: str,
        temperature: float = 0.0,
    ) -> TraceRecord:
        trace = TraceRecord(
            trace_id=str(uuid.uuid4()),
            agent_id=agent_id,
            session_id=session_id,
            user_query=user_query,
            model_id=model_id,
            temperature=temperature,
        )
        self.traces[trace.trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> TraceRecord:
        return self.traces[trace_id]

    def list_traces(self, *, limit: int = 50) -> list[TraceRecord]:
        traces = sorted(self.traces.values(), key=lambda trace: trace.started_at, reverse=True)
        return traces[:limit]

    def complete_trace(self, trace_id: str, *, response_text: str, decision_label: str) -> TraceRecord:
        trace = self.traces[trace_id]
        trace.response_text = response_text
        trace.decision_label = decision_label
        trace.status = "completed"
        trace.completed_at = utc_now()
        return trace

    def create_retrieval_run(
        self,
        *,
        trace_id: str,
        query_text: str,
        top_k: int,
        embedding_model: str,
        items: list[RetrievedItemRecord],
        latency_ms: int,
    ) -> str:
        retrieval_id = items[0].retrieval_id if items else str(uuid.uuid4())
        normalized = [
            replace(item, retrieval_id=retrieval_id)
            for item in items
        ]
        self.retrieval_items[retrieval_id] = normalized
        self.trace_retrieval_ids.setdefault(trace_id, []).append(retrieval_id)
        return retrieval_id

    def get_latest_retrieval_items(self, trace_id: str) -> list[RetrievedItemRecord]:
        ids = self.trace_retrieval_ids.get(trace_id, [])
        if not ids:
            return []
        return list(self.retrieval_items[ids[-1]])

    def get_latest_retrieval_items_bulk(self, trace_ids: list[str]) -> dict[str, list[RetrievedItemRecord]]:
        return {trace_id: self.get_latest_retrieval_items(trace_id) for trace_id in trace_ids}

    def create_claims(
        self,
        *,
        trace_id: str,
        claims: list[tuple[str | None, int, str]],
    ) -> list[ClaimRecord]:
        out: list[ClaimRecord] = []
        for memory_id, rank, explanation in claims:
            resolved = self.resolve_memory_id(memory_id) if memory_id else None
            out.append(
                ClaimRecord(
                    claim_id=str(uuid.uuid4()),
                    trace_id=trace_id,
                    memory_id=resolved,
                    claim_type="memory_attribution",
                    claimed_rank=rank,
                    explanation=explanation,
                )
            )
        self.claims[trace_id] = out
        return out

    def get_claims(self, trace_id: str) -> list[ClaimRecord]:
        return list(self.claims.get(trace_id, []))

    def get_claims_bulk(self, trace_ids: list[str]) -> dict[str, list[ClaimRecord]]:
        return {trace_id: list(self.claims.get(trace_id, [])) for trace_id in trace_ids}

    def create_intervention(
        self,
        *,
        trace_id: str,
        intervention_type: str,
        target_memory_id: str | None,
        target_depth: int,
        baseline_decision: str | None,
        counterfactual_decision: str | None,
        baseline_response: str | None,
        counterfactual_response: str | None,
        decision_changed: bool,
        semantic_delta: float | None,
        effect_score: float | None,
        latency_ms: int | None,
    ) -> InterventionRecord:
        resolved = self.resolve_memory_id(target_memory_id) if target_memory_id else None
        intervention = InterventionRecord(
            intervention_id=str(uuid.uuid4()),
            trace_id=trace_id,
            intervention_type=intervention_type,
            target_memory_id=resolved,
            target_depth=target_depth,
            baseline_decision=baseline_decision,
            counterfactual_decision=counterfactual_decision,
            baseline_response=baseline_response,
            counterfactual_response=counterfactual_response,
            decision_changed=decision_changed,
            semantic_delta=semantic_delta,
            effect_score=effect_score,
            latency_ms=latency_ms,
        )
        self.interventions.setdefault(trace_id, []).append(intervention)
        return intervention

    def list_interventions(self, trace_id: str) -> list[InterventionRecord]:
        return list(self.interventions.get(trace_id, []))

    def list_interventions_bulk(self, trace_ids: list[str]) -> dict[str, list[InterventionRecord]]:
        return {trace_id: list(self.interventions.get(trace_id, [])) for trace_id in trace_ids}

    def create_consolidation(
        self,
        *,
        agent_id: str,
        session_id: str | None,
        output_memory_id: str,
        model_id: str,
        prompt_version: str,
        input_count: int,
        latency_ms: int | None,
    ) -> ConsolidationRecord:
        consolidation = ConsolidationRecord(
            consolidation_id=str(uuid.uuid4()),
            agent_id=agent_id,
            session_id=session_id,
            output_memory_id=output_memory_id,
            model_id=model_id,
            prompt_version=prompt_version,
            input_count=input_count,
            latency_ms=latency_ms,
        )
        self.consolidations[consolidation.consolidation_id] = consolidation
        return consolidation

    def get_consolidation(self, consolidation_id: str) -> ConsolidationRecord:
        return self.consolidations[consolidation_id]


class DatabaseMemoryStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_default_agent(self, model_id: str) -> tuple[str, str, str]:
        with db.connect(self.settings) as conn:
            conn.execute(
                """
                INSERT INTO agents (agent_id, name, description, model_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (agent_id) DO UPDATE SET model_id=excluded.model_id
                """,
                (
                    DEFAULT_AGENT_ID,
                    "MemoryIR Demo Agent",
                    "Hackathon demo agent for memory forensics.",
                    model_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO sessions (session_id, agent_id, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO NOTHING
                """,
                (DEFAULT_SESSION_ID, DEFAULT_AGENT_ID, "CockroachDB architecture demo"),
            )
            conn.execute(
                """
                INSERT INTO memory_sources
                    (source_id, source_type, source_name, trust_label, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO NOTHING
                """,
                (
                    DEFAULT_SOURCE_ID,
                    "SYNTHETIC_EVAL",
                    "MemoryIR demo seed",
                    "controlled",
                    Json({"scenario": "cockroach_demo"}),
                ),
            )
        return DEFAULT_AGENT_ID, DEFAULT_SESSION_ID, DEFAULT_SOURCE_ID

    def seed_demo(self, provider: Any) -> dict[str, Any]:
        agent_id, session_id, source_id = self.ensure_default_agent(provider.model_id)
        rows = [
            ("00000000-0000-0000-0000-000000000101", "M1", "raw", 0, "The team prefers PostgreSQL-compatible databases.", None),
            ("00000000-0000-0000-0000-000000000102", "M2", "raw", 0, "The deployment must survive regional failures.", None),
            ("00000000-0000-0000-0000-000000000103", "M3", "raw", 0, "The operations team wants a managed service.", None),
            ("00000000-0000-0000-0000-000000000107", "M7", "consolidated", 1, "The application should use a managed, PostgreSQL-compatible database with multi-region resilience.", 0.01),
            ("00000000-0000-0000-0000-000000000112", "M12", "raw", 0, "The frontend team prefers TypeScript for the project.", 0.02),
            ("00000000-0000-0000-0000-000000000116", "M16", "raw", 0, "The finance team wants operational costs to stay predictable.", 0.03),
        ]
        for memory_id, display_id, memory_type, generation, content, demo_distance in rows:
            self.insert_memory(
                content=content,
                embedding=provider.embed(content),
                memory_type=memory_type,
                generation=generation,
                agent_id=agent_id,
                session_id=session_id,
                source_id=source_id,
                metadata={
                    "display_id": display_id,
                    "scenario": "cockroach_demo",
                    "demo_distance": demo_distance,
                    **(
                        {
                            "input_memory_ids": [
                                "00000000-0000-0000-0000-000000000101",
                                "00000000-0000-0000-0000-000000000102",
                                "00000000-0000-0000-0000-000000000103",
                            ]
                        }
                        if display_id == "M7"
                        else {}
                    ),
                },
                memory_id=memory_id,
            )
        for parent_id, weight in [
            ("00000000-0000-0000-0000-000000000101", 0.25),
            ("00000000-0000-0000-0000-000000000102", 0.50),
            ("00000000-0000-0000-0000-000000000103", 0.25),
        ]:
            self.insert_edge(
                parent_id,
                "00000000-0000-0000-0000-000000000107",
                relation_type="consolidated_from",
                declared_weight=weight,
            )
        return {"agent_id": agent_id, "session_id": session_id, "memories": self.list_memories()}

    def resolve_memory_id(self, memory_id_or_display: str) -> str:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                SELECT memory_id
                FROM memories
                WHERE memory_id::STRING = %s OR metadata->>'display_id' = %s
                LIMIT 1
                """,
                (memory_id_or_display, memory_id_or_display),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown memory: {memory_id_or_display}")
        return str(row["memory_id"])

    def _row_to_memory(self, row: dict[str, Any]) -> MemoryRecord:
        metadata = row.get("metadata") or {}
        embedding = row.get("embedding")
        return MemoryRecord(
            memory_id=str(row["memory_id"]),
            agent_id=str(row["agent_id"]),
            session_id=str(row["session_id"]) if row.get("session_id") else None,
            source_id=str(row["source_id"]) if row.get("source_id") else None,
            memory_type=row["memory_type"],
            content=row["content"],
            embedding=_embedding_to_list(embedding),
            generation=row["generation"],
            content_hash=row.get("content_hash"),
            metadata=metadata,
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
        )

    def insert_memory(
        self,
        *,
        content: str,
        embedding: list[float] | None,
        memory_type: str = "raw",
        generation: int = 0,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
    ) -> MemoryRecord:
        default_agent, default_session, default_source = self.ensure_default_agent("bedrock")
        metadata = metadata or {}
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO memories
                    (memory_id, agent_id, session_id, source_id, memory_type, content,
                     embedding, generation, content_hash, metadata)
                VALUES
                    (COALESCE(%s::UUID, gen_random_uuid()), %s, %s, %s, %s, %s,
                     %s::VECTOR, %s, %s, %s)
                ON CONFLICT (memory_id) DO UPDATE SET
                    content=excluded.content,
                    embedding=excluded.embedding,
                    generation=excluded.generation,
                    metadata=excluded.metadata
                RETURNING *
                """,
                (
                    memory_id,
                    agent_id or default_agent,
                    session_id if session_id is not None else default_session,
                    source_id if source_id is not None else default_source,
                    memory_type,
                    content,
                    _vector_literal(embedding),
                    generation,
                    content_hash(content),
                    Json(metadata),
                ),
            ).fetchone()
        return self._row_to_memory(row)

    def list_memories(self, agent_id: str | None = None) -> list[MemoryRecord]:
        where = "WHERE agent_id = %s" if agent_id else ""
        params = (agent_id,) if agent_id else ()
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                f"SELECT * FROM memories {where} ORDER BY created_at, metadata->>'display_id'",
                params,
            ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get_memory(self, memory_id_or_display: str) -> MemoryRecord:
        memory_id = self.resolve_memory_id(memory_id_or_display)
        with db.connect(self.settings) as conn:
            row = conn.execute("SELECT * FROM memories WHERE memory_id = %s", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown memory: {memory_id_or_display}")
        return self._row_to_memory(row)

    def insert_edge(
        self,
        parent_memory_id: str,
        child_memory_id: str,
        *,
        relation_type: str,
        declared_weight: float | None = None,
    ) -> MemoryEdgeRecord:
        parent_id = self.resolve_memory_id(parent_memory_id)
        child_id = self.resolve_memory_id(child_memory_id)
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO memory_edges
                    (parent_memory_id, child_memory_id, relation_type, declared_weight)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (parent_memory_id, child_memory_id, relation_type)
                DO UPDATE SET declared_weight=excluded.declared_weight
                RETURNING *
                """,
                (parent_id, child_id, relation_type, declared_weight),
            ).fetchone()
        return self._row_to_edge(row)

    def _row_to_edge(self, row: dict[str, Any], depth: int = 1) -> MemoryEdgeRecord:
        return MemoryEdgeRecord(
            edge_id=str(row["edge_id"]),
            parent_memory_id=str(row["parent_memory_id"]),
            child_memory_id=str(row["child_memory_id"]),
            relation_type=row["relation_type"],
            declared_weight=row.get("declared_weight"),
            depth=depth,
        )

    def list_edges(self) -> list[MemoryEdgeRecord]:
        with db.connect(self.settings) as conn:
            rows = conn.execute("SELECT * FROM memory_edges ORDER BY created_at").fetchall()
        return [self._row_to_edge(row) for row in rows]

    def ancestry(self, memory_id_or_display: str) -> list[MemoryEdgeRecord]:
        memory_id = self.resolve_memory_id(memory_id_or_display)
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                """
                WITH RECURSIVE ancestry AS (
                    SELECT edge_id, parent_memory_id, child_memory_id, relation_type,
                           declared_weight, 1 AS depth
                    FROM memory_edges
                    WHERE child_memory_id = %s
                    UNION ALL
                    SELECT e.edge_id, e.parent_memory_id, e.child_memory_id,
                           e.relation_type, e.declared_weight, a.depth + 1
                    FROM memory_edges e
                    JOIN ancestry a ON e.child_memory_id = a.parent_memory_id
                )
                SELECT * FROM ancestry ORDER BY depth
                """,
                (memory_id,),
            ).fetchall()
        return [self._row_to_edge(row, depth=row["depth"]) for row in rows]

    def vector_search(
        self,
        *,
        agent_id: str,
        embedding: list[float],
        top_k: int,
        exclude_memory_ids: set[str] | None = None,
        query_text: str = "",
    ) -> list[RetrievedItemRecord]:
        exclude = {self.resolve_memory_id(mid) for mid in (exclude_memory_ids or set())}
        limit = top_k + len(exclude)
        is_demo_query = "database architecture" in query_text.lower()
        if is_demo_query:
            sql = """
                SELECT *,
                    COALESCE((metadata->>'demo_distance')::FLOAT8, ((embedding <-> %s::VECTOR) + 10.0))
                    AS vector_distance
                FROM memories
                WHERE agent_id = %s AND embedding IS NOT NULL
                ORDER BY vector_distance
                LIMIT %s
                """
            params = (_vector_literal(embedding), agent_id, limit)
        else:
            sql = """
                SELECT *, embedding <-> %s::VECTOR AS vector_distance
                FROM memories
                WHERE agent_id = %s AND embedding IS NOT NULL
                ORDER BY embedding <-> %s::VECTOR
                LIMIT %s
                """
            params = (_vector_literal(embedding), agent_id, _vector_literal(embedding), limit)
        with db.connect(self.settings) as conn:
            rows = conn.execute(sql, params).fetchall()
        items = []
        retrieval_id = str(uuid.uuid4())
        for row in rows:
            memory = self._row_to_memory(row)
            if memory.memory_id in exclude:
                continue
            items.append(
                RetrievedItemRecord(
                    retrieval_id=retrieval_id,
                    memory=memory,
                    retrieval_rank=len(items) + 1,
                    vector_distance=float(row["vector_distance"]),
                )
            )
            if len(items) == top_k:
                break
        return items

    def create_trace(
        self,
        *,
        agent_id: str,
        session_id: str | None,
        user_query: str,
        model_id: str,
        temperature: float = 0.0,
    ) -> TraceRecord:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO traces (agent_id, session_id, user_query, model_id, temperature)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (agent_id, session_id, user_query, model_id, temperature),
            ).fetchone()
        return self._row_to_trace(row)

    def _row_to_trace(self, row: dict[str, Any]) -> TraceRecord:
        return TraceRecord(
            trace_id=str(row["trace_id"]),
            agent_id=str(row["agent_id"]),
            session_id=str(row["session_id"]) if row.get("session_id") else None,
            user_query=row["user_query"],
            response_text=row.get("response_text"),
            decision_label=row.get("decision_label"),
            model_id=row.get("model_id"),
            temperature=float(row.get("temperature") or 0.0),
            status=row.get("status", "running"),
            started_at=str(row.get("started_at")),
            completed_at=str(row.get("completed_at")) if row.get("completed_at") else None,
        )

    def get_trace(self, trace_id: str) -> TraceRecord:
        with db.connect(self.settings) as conn:
            row = conn.execute("SELECT * FROM traces WHERE trace_id = %s", (trace_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown trace: {trace_id}")
        return self._row_to_trace(row)

    def list_traces(self, *, limit: int = 50) -> list[TraceRecord]:
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM traces ORDER BY started_at DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [self._row_to_trace(row) for row in rows]

    def complete_trace(self, trace_id: str, *, response_text: str, decision_label: str) -> TraceRecord:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                UPDATE traces
                SET response_text=%s, decision_label=%s, status='completed', completed_at=now()
                WHERE trace_id=%s
                RETURNING *
                """,
                (response_text, decision_label, trace_id),
            ).fetchone()
        return self._row_to_trace(row)

    def create_retrieval_run(
        self,
        *,
        trace_id: str,
        query_text: str,
        top_k: int,
        embedding_model: str,
        items: list[RetrievedItemRecord],
        latency_ms: int,
    ) -> str:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO retrieval_runs (trace_id, query_text, top_k, embedding_model, latency_ms)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING retrieval_id
                """,
                (trace_id, query_text, top_k, embedding_model, latency_ms),
            ).fetchone()
            retrieval_id = str(row["retrieval_id"])
            for item in items:
                conn.execute(
                    """
                    INSERT INTO retrieval_items
                        (retrieval_id, memory_id, retrieval_rank, vector_distance)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (retrieval_id, memory_id) DO NOTHING
                    """,
                    (retrieval_id, item.memory.memory_id, item.retrieval_rank, item.vector_distance),
                )
        return retrieval_id

    def get_latest_retrieval_items(self, trace_id: str) -> list[RetrievedItemRecord]:
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                """
                SELECT
                    rr.retrieval_id,
                    ri.retrieval_rank,
                    ri.vector_distance,
                    m.*
                FROM retrieval_runs rr
                JOIN retrieval_items ri ON ri.retrieval_id = rr.retrieval_id
                JOIN memories m ON m.memory_id = ri.memory_id
                WHERE rr.trace_id = %s
                ORDER BY rr.started_at DESC, ri.retrieval_rank
                """,
                (trace_id,),
            ).fetchall()
        if not rows:
            return []
        latest_id = str(rows[0]["retrieval_id"])
        return [
            RetrievedItemRecord(
                retrieval_id=latest_id,
                memory=self._row_to_memory(row),
                retrieval_rank=row["retrieval_rank"],
                vector_distance=float(row["vector_distance"]),
            )
            for row in rows
            if str(row["retrieval_id"]) == latest_id
        ]

    def get_latest_retrieval_items_bulk(self, trace_ids: list[str]) -> dict[str, list[RetrievedItemRecord]]:
        if not trace_ids:
            return {}
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                """
                SELECT
                    rr.trace_id,
                    rr.retrieval_id,
                    rr.started_at,
                    ri.retrieval_rank,
                    ri.vector_distance,
                    m.*
                FROM retrieval_runs rr
                JOIN retrieval_items ri ON ri.retrieval_id = rr.retrieval_id
                JOIN memories m ON m.memory_id = ri.memory_id
                WHERE rr.trace_id = ANY(%s)
                ORDER BY rr.trace_id, rr.started_at DESC, ri.retrieval_rank
                """,
                (trace_ids,),
            ).fetchall()
        out: dict[str, list[RetrievedItemRecord]] = {trace_id: [] for trace_id in trace_ids}
        latest_id_by_trace: dict[str, str] = {}
        for row in rows:
            trace_id = str(row["trace_id"])
            retrieval_id = str(row["retrieval_id"])
            latest_id = latest_id_by_trace.setdefault(trace_id, retrieval_id)
            if retrieval_id != latest_id:
                continue
            out[trace_id].append(
                RetrievedItemRecord(
                    retrieval_id=retrieval_id,
                    memory=self._row_to_memory(row),
                    retrieval_rank=row["retrieval_rank"],
                    vector_distance=float(row["vector_distance"]),
                )
            )
        return out

    def create_claims(
        self,
        *,
        trace_id: str,
        claims: list[tuple[str | None, int, str]],
    ) -> list[ClaimRecord]:
        out: list[ClaimRecord] = []
        with db.connect(self.settings) as conn:
            for memory_id, rank, explanation in claims:
                resolved = self.resolve_memory_id(memory_id) if memory_id else None
                row = conn.execute(
                    """
                    INSERT INTO generation_claims
                        (trace_id, memory_id, claim_type, claimed_rank, explanation)
                    VALUES (%s, %s, 'memory_attribution', %s, %s)
                    RETURNING *
                    """,
                    (trace_id, resolved, rank, explanation),
                ).fetchone()
                out.append(self._row_to_claim(row))
        return out

    def _row_to_claim(self, row: dict[str, Any]) -> ClaimRecord:
        return ClaimRecord(
            claim_id=str(row["claim_id"]),
            trace_id=str(row["trace_id"]),
            memory_id=str(row["memory_id"]) if row.get("memory_id") else None,
            claim_type=row["claim_type"],
            claimed_rank=row.get("claimed_rank") or 0,
            explanation=row.get("explanation") or "",
        )

    def get_claims(self, trace_id: str) -> list[ClaimRecord]:
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM generation_claims WHERE trace_id = %s ORDER BY claimed_rank",
                (trace_id,),
            ).fetchall()
        return [self._row_to_claim(row) for row in rows]

    def get_claims_bulk(self, trace_ids: list[str]) -> dict[str, list[ClaimRecord]]:
        if not trace_ids:
            return {}
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM generation_claims WHERE trace_id = ANY(%s) ORDER BY trace_id, claimed_rank",
                (trace_ids,),
            ).fetchall()
        out: dict[str, list[ClaimRecord]] = {trace_id: [] for trace_id in trace_ids}
        for row in rows:
            out.setdefault(str(row["trace_id"]), []).append(self._row_to_claim(row))
        return out

    def create_intervention(
        self,
        *,
        trace_id: str,
        intervention_type: str,
        target_memory_id: str | None,
        target_depth: int,
        baseline_decision: str | None,
        counterfactual_decision: str | None,
        baseline_response: str | None,
        counterfactual_response: str | None,
        decision_changed: bool,
        semantic_delta: float | None,
        effect_score: float | None,
        latency_ms: int | None,
    ) -> InterventionRecord:
        resolved = self.resolve_memory_id(target_memory_id) if target_memory_id else None
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO intervention_runs
                    (trace_id, intervention_type, target_memory_id, target_depth,
                     baseline_decision, counterfactual_decision, baseline_response,
                     counterfactual_response, decision_changed, semantic_delta,
                     effect_score, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    trace_id,
                    intervention_type,
                    resolved,
                    target_depth,
                    baseline_decision,
                    counterfactual_decision,
                    baseline_response,
                    counterfactual_response,
                    decision_changed,
                    semantic_delta,
                    effect_score,
                    latency_ms,
                ),
            ).fetchone()
        return self._row_to_intervention(row)

    def _row_to_intervention(self, row: dict[str, Any]) -> InterventionRecord:
        return InterventionRecord(
            intervention_id=str(row["intervention_id"]),
            trace_id=str(row["trace_id"]),
            intervention_type=row["intervention_type"],
            target_memory_id=str(row["target_memory_id"]) if row.get("target_memory_id") else None,
            target_depth=row.get("target_depth") or 0,
            baseline_decision=row.get("baseline_decision"),
            counterfactual_decision=row.get("counterfactual_decision"),
            baseline_response=row.get("baseline_response"),
            counterfactual_response=row.get("counterfactual_response"),
            decision_changed=bool(row.get("decision_changed")),
            semantic_delta=row.get("semantic_delta"),
            effect_score=row.get("effect_score"),
            latency_ms=row.get("latency_ms"),
            created_at=str(row.get("created_at")),
        )

    def list_interventions(self, trace_id: str) -> list[InterventionRecord]:
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM intervention_runs WHERE trace_id = %s ORDER BY created_at",
                (trace_id,),
            ).fetchall()
        return [self._row_to_intervention(row) for row in rows]

    def list_interventions_bulk(self, trace_ids: list[str]) -> dict[str, list[InterventionRecord]]:
        if not trace_ids:
            return {}
        with db.connect(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM intervention_runs WHERE trace_id = ANY(%s) ORDER BY created_at",
                (trace_ids,),
            ).fetchall()
        out: dict[str, list[InterventionRecord]] = {trace_id: [] for trace_id in trace_ids}
        for row in rows:
            out.setdefault(str(row["trace_id"]), []).append(self._row_to_intervention(row))
        return out

    def create_consolidation(
        self,
        *,
        agent_id: str,
        session_id: str | None,
        output_memory_id: str,
        model_id: str,
        prompt_version: str,
        input_count: int,
        latency_ms: int | None,
    ) -> ConsolidationRecord:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO consolidation_runs
                    (agent_id, session_id, output_memory_id, model_id,
                     prompt_version, input_count, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (agent_id, session_id, output_memory_id, model_id, prompt_version, input_count, latency_ms),
            ).fetchone()
        return ConsolidationRecord(
            consolidation_id=str(row["consolidation_id"]),
            agent_id=str(row["agent_id"]),
            session_id=str(row["session_id"]) if row.get("session_id") else None,
            output_memory_id=str(row["output_memory_id"]),
            model_id=row["model_id"],
            prompt_version=row["prompt_version"],
            input_count=row["input_count"],
            latency_ms=row.get("latency_ms"),
            created_at=str(row.get("created_at")),
        )

    def get_consolidation(self, consolidation_id: str) -> ConsolidationRecord:
        with db.connect(self.settings) as conn:
            row = conn.execute(
                "SELECT * FROM consolidation_runs WHERE consolidation_id = %s",
                (consolidation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown consolidation: {consolidation_id}")
        return ConsolidationRecord(
            consolidation_id=str(row["consolidation_id"]),
            agent_id=str(row["agent_id"]),
            session_id=str(row["session_id"]) if row.get("session_id") else None,
            output_memory_id=str(row["output_memory_id"]),
            model_id=row["model_id"],
            prompt_version=row["prompt_version"],
            input_count=row["input_count"],
            latency_ms=row.get("latency_ms"),
            created_at=str(row.get("created_at")),
        )


def build_store(settings: Settings) -> InMemoryMemoryStore | DatabaseMemoryStore:
    if settings.database_backend == "cockroach":
        return DatabaseMemoryStore(settings)
    return InMemoryMemoryStore()


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    return 1.0 - (dot / (left_norm * right_norm))


def _vector_literal(embedding: list[float] | None) -> str | None:
    if embedding is None:
        return None
    return "[" + ",".join(f"{float(value):.9g}" for value in embedding) + "]"


def _embedding_to_list(embedding: Any) -> list[float] | None:
    if embedding is None:
        return None
    if isinstance(embedding, list):
        return [float(value) for value in embedding]
    if isinstance(embedding, tuple):
        return [float(value) for value in embedding]
    for method_name in ("to_list", "tolist"):
        method = getattr(embedding, method_name, None)
        if callable(method):
            return [float(value) for value in method()]
    return None


class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        self.latency_ms = 0
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.latency_ms = int((time.perf_counter() - self.start) * 1000)
