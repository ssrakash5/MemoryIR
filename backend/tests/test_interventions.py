from __future__ import annotations


def test_interventions_find_summary_and_ground_memory(services):
    trace_id, result, _ = services.query_engine.query(
        query="Which database architecture best satisfies the project requirements?",
        top_k=3,
    )
    assert result.decision == "COCKROACHDB"

    runs = services.intervention_engine.run(trace_id)
    direct = {
        services.store.get_memory(run.target_memory_id).display_id: run
        for run in runs
        if run.intervention_type == "RETRIEVED_MEMORY_ABLATION"
    }
    ancestor = {
        services.store.get_memory(run.target_memory_id).display_id: run
        for run in runs
        if run.intervention_type == "ANCESTOR_ABLATION"
    }

    assert direct["M7"].decision_changed is True
    assert direct["M7"].counterfactual_decision == "DYNAMODB"
    assert direct["M12"].decision_changed is False
    assert direct["M16"].decision_changed is False
    assert ancestor["M2"].decision_changed is True
    assert ancestor["M1"].decision_changed is False
    assert ancestor["M3"].decision_changed is False
