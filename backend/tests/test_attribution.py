from __future__ import annotations


def test_attribution_report_separates_claimed_measured_and_ground(services):
    trace_id, _, _ = services.query_engine.query(
        query="Which database architecture best satisfies the project requirements?",
        top_k=3,
    )
    services.intervention_engine.run(trace_id)

    report = services.attribution.report(trace_id)

    assert report.claimed_memories == ["M7", "M12"]
    assert report.retrieved_memories == ["M7", "M12", "M16"]
    assert report.influential_memories == ["M7"]
    assert report.causal_precision == 0.5
    assert report.causal_recall == 1.0
    assert report.ground_provenance[0]["path"] == ["M2", "M7", "Decision"]
