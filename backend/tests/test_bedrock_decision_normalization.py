from app.services.llm import _normalize_decision
from app.services.memory_store import MemoryRecord


def memory(content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id="m1",
        agent_id="a1",
        session_id="s1",
        source_id="src1",
        memory_type="consolidated",
        content=content,
        embedding=None,
        generation=1,
        content_hash=None,
        metadata={"display_id": "M1"},
    )


def test_postgres_with_regional_resilience_maps_to_cockroachdb() -> None:
    decision, answer = _normalize_decision(
        "POSTGRES",
        "Use a managed PostgreSQL-compatible database.",
        [
            memory(
                "The application should use a managed, PostgreSQL-compatible "
                "database with multi-region resilience."
            )
        ],
    )

    assert decision == "COCKROACHDB"
    assert "CockroachDB" in answer


def test_plain_postgres_compatibility_stays_postgres() -> None:
    decision, _ = _normalize_decision(
        "POSTGRES",
        "Use PostgreSQL.",
        [memory("The application should keep PostgreSQL compatibility as a design constraint.")],
    )

    assert decision == "POSTGRES"
