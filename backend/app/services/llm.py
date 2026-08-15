from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from ..config import Settings
from .memory_store import MemoryRecord


@dataclass(frozen=True)
class MemoryAttribution:
    memory_id: str
    importance: int
    reason: str


@dataclass(frozen=True)
class GenerationResult:
    answer: str
    decision: str
    response_text: str
    memory_attribution: list[MemoryAttribution]


VALID_DECISIONS = {
    "COCKROACHDB",
    "DYNAMODB",
    "POSTGRES",
    "APPROVE",
    "REJECT",
    "OPTION_A",
    "OPTION_B",
    "OPTION_C",
    "BLUE_GREEN",
}


class ModelProvider(Protocol):
    model_id: str
    embedding_model_id: str

    def embed(self, text: str) -> list[float]:
        ...

    def consolidate(self, memories: list[MemoryRecord]) -> str:
        ...

    def generate(self, *, query: str, memories: list[MemoryRecord]) -> GenerationResult:
        ...


class MockProvider:
    model_id = "mock-memoryir-v1"
    embedding_model_id = "mock-keyword-256"

    def embed(self, text: str) -> list[float]:
        lower = text.lower()
        vector = [0.0] * 256
        keyword_groups = [
            (0, ["database", "postgresql", "cockroachdb", "architecture"]),
            (1, ["region", "regional", "multi-region", "resilience", "failures"]),
            (2, ["managed", "operations", "service"]),
            (3, ["typescript", "frontend"]),
            (4, ["finance", "cost", "costs", "predictable"]),
            (5, ["project", "team", "requirements", "satisfies"]),
            (6, ["application should use", "best satisfies", "which database architecture"]),
        ]
        for index, terms in keyword_groups:
            vector[index] = float(sum(1 for term in terms if term in lower))
        for token in re.findall(r"[a-z0-9]+", lower):
            bucket = 16 + (sum(ord(ch) for ch in token) % 200)
            vector[bucket] += 0.05
        return vector

    def consolidate(self, memories: list[MemoryRecord]) -> str:
        text = " ".join(memory.content.lower() for memory in memories)
        has_regional = any(term in text for term in ["regional", "multi-region", "resilience"])
        has_postgres = "postgres" in text or "postgresql-compatible" in text
        has_managed = "managed" in text or "operations" in text
        if has_regional:
            parts = ["multi-region resilience"]
            if has_postgres:
                parts.insert(0, "PostgreSQL-compatible")
            if has_managed:
                parts.insert(0, "managed")
            return f"The application should use a {', '.join(parts)} database architecture."
        if has_postgres and has_managed:
            return "The application should use a managed PostgreSQL-compatible database service."
        if has_postgres:
            return "The application should keep PostgreSQL compatibility as a design constraint."
        if has_managed:
            return "The application should prefer a managed service to reduce operations work."
        return "The application should use the consolidated project requirements as decision context."

    def generate(self, *, query: str, memories: list[MemoryRecord]) -> GenerationResult:
        context = "\n".join(memory.content.lower() for memory in memories)
        display = {memory.display_id: memory for memory in memories}
        m7 = display.get("M7")
        has_decisive_summary = m7 is not None and any(
            term in m7.content.lower()
            for term in ["multi-region", "regional failure", "regional failures", "resilience"]
        )
        has_regional_summary = any(
            memory.memory_type in {"consolidated", "derived", "synthetic"}
            and any(term in memory.content.lower() for term in ["multi-region", "regional", "resilience"])
            for memory in memories
        )

        if has_decisive_summary or has_regional_summary:
            decision = "COCKROACHDB"
            answer = "CockroachDB"
            response = (
                "CockroachDB best fits the project because the retrieved memory combines "
                "managed operations with regional-failure resilience."
            )
        elif "managed" in context or "operations" in context:
            decision = "DYNAMODB"
            answer = "DynamoDB"
            response = (
                "DynamoDB is the fallback because the remaining context emphasizes managed "
                "operations but no longer establishes multi-region SQL resilience."
            )
        elif "postgres" in context:
            decision = "POSTGRES"
            answer = "PostgreSQL"
            response = "PostgreSQL fits the compatibility preference, but no resilience constraint was retrieved."
        else:
            decision = "DYNAMODB"
            answer = "DynamoDB"
            response = "DynamoDB is the default managed option from the available context."

        claims: list[MemoryAttribution] = []
        if m7 is not None:
            claims.append(
                MemoryAttribution(
                    memory_id=m7.memory_id,
                    importance=1,
                    reason="Consolidated database architecture requirement.",
                )
            )
        distractor = display.get("M12")
        if distractor is not None:
            claims.append(
                MemoryAttribution(
                    memory_id=distractor.memory_id,
                    importance=2,
                    reason="Project implementation context.",
                )
            )
        if not claims and memories:
            claims.append(
                MemoryAttribution(
                    memory_id=memories[0].memory_id,
                    importance=1,
                    reason="Highest-ranked retrieved context.",
                )
            )

        return GenerationResult(
            answer=answer,
            decision=decision,
            response_text=response,
            memory_attribution=claims,
        )


class BedrockProvider:
    def __init__(self, settings: Settings) -> None:
        import truststore

        truststore.inject_into_ssl()
        import boto3

        self.settings = settings
        self.model_id = settings.bedrock_agent_model_id
        self.embedding_model_id = settings.bedrock_embed_model_id
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def embed(self, text: str) -> list[float]:
        body = {
            "inputText": text,
            "dimensions": 256,
            "normalize": True,
        }
        response = self._client.invoke_model(
            modelId=self.embedding_model_id,
            body=json.dumps(body).encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        data = json.loads(response["body"].read())
        return [float(value) for value in data["embedding"]]

    def consolidate(self, memories: list[MemoryRecord]) -> str:
        bullets = "\n".join(f"- {memory.content}" for memory in memories)
        prompt = (
            "Summarize these persistent memories into one concise derived memory. "
            "Preserve decision-relevant constraints, especially deployment, database, "
            "and operational requirements.\n\n"
            f"{bullets}\n\nOutput only the derived memory."
        )
        return self._converse_text(prompt, max_tokens=220)

    def generate(self, *, query: str, memories: list[MemoryRecord]) -> GenerationResult:
        context = "\n".join(
            f"{memory.display_id} ({memory.memory_id}): {memory.content}" for memory in memories
        )
        prompt = (
            "You are a deterministic decision agent. Use only the retrieved memories. "
            "Return JSON with keys answer, decision, and memory_attribution. "
            "decision must be one of COCKROACHDB, DYNAMODB, POSTGRES, APPROVE, REJECT, OPTION_A, OPTION_B, OPTION_C, BLUE_GREEN. "
            "If the retrieved memories require PostgreSQL compatibility plus multi-region, regional-failure, failover, "
            "or resilience requirements, decision must be COCKROACHDB rather than POSTGRES. "
            "memory_attribution is a list of objects with memory_id, importance, and reason.\n\n"
            f"User query: {query}\n\nRetrieved memories:\n{context}"
        )
        raw = self._converse_text(prompt, max_tokens=self.settings.bedrock_max_tokens)
        data = _json_object(raw)
        claims = [
            MemoryAttribution(
                memory_id=item["memory_id"],
                importance=int(item.get("importance", index + 1)),
                reason=item.get("reason", "Claimed by model."),
            )
            for index, item in enumerate(data.get("memory_attribution", []))
            if item.get("memory_id")
        ]
        answer = data.get("answer") or data.get("decision") or raw
        decision = data.get("decision") or str(answer).upper()
        decision, answer = _normalize_decision(str(decision), str(answer), memories)
        if not claims and memories:
            claims.append(
                MemoryAttribution(
                    memory_id=memories[0].memory_id,
                    importance=1,
                    reason="Highest-ranked retrieved context.",
                )
            )
        return GenerationResult(
            answer=str(answer),
            decision=decision,
            response_text=str(answer),
            memory_attribution=claims,
        )

    def _converse_text(self, prompt: str, *, max_tokens: int) -> str:
        response = self._client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": max_tokens},
        )
        content = response["output"]["message"]["content"]
        return "".join(part.get("text", "") for part in content).strip()


def make_provider(settings: Settings) -> ModelProvider:
    if settings.provider.lower() == "bedrock":
        return BedrockProvider(settings)
    return MockProvider()


def _normalize_decision(
    decision: str, answer: str, memories: list[MemoryRecord]
) -> tuple[str, str]:
    label = re.sub(r"[^A-Z0-9]+", "_", decision.upper()).strip("_")
    if label in {"COCKROACH", "COCKROACH_DB"}:
        label = "COCKROACHDB"
    elif label in {"POSTGRESQL", "POSTGRES_SQL"}:
        label = "POSTGRES"

    if label == "POSTGRES" and _requires_cockroachdb(memories):
        label = "COCKROACHDB"
        if "cockroach" not in answer.lower():
            answer = (
                answer.rstrip().rstrip(".")
                + ". CockroachDB is the concrete fit for PostgreSQL-compatible multi-region resilience."
            )

    if label not in VALID_DECISIONS:
        for candidate in VALID_DECISIONS:
            if candidate in label:
                label = candidate
                break
    return label, answer


def _requires_cockroachdb(memories: list[MemoryRecord]) -> bool:
    for memory in memories:
        text = memory.content.lower()
        has_sql_compatibility = "postgres" in text or "sql" in text
        has_resilience = any(
            term in text
            for term in [
                "multi-region",
                "regional failure",
                "regional failures",
                "failover",
                "resilience",
            ]
        )
        if has_sql_compatibility and has_resilience:
            return True
    return False


def _json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
