WITH latest_retrieval AS (
    SELECT retrieval_id
    FROM retrieval_runs
    WHERE trace_id = $1
    ORDER BY started_at DESC
    LIMIT 1
),
retrieved AS (
    SELECT
        ri.retrieval_rank,
        ri.vector_distance,
        m.memory_id,
        m.memory_type,
        m.generation,
        m.content,
        m.metadata
    FROM retrieval_items ri
    JOIN latest_retrieval lr ON lr.retrieval_id = ri.retrieval_id
    JOIN memories m ON m.memory_id = ri.memory_id
),
claimed AS (
    SELECT
        gc.claimed_rank,
        gc.claim_type,
        gc.explanation,
        m.memory_id,
        m.metadata
    FROM generation_claims gc
    LEFT JOIN memories m ON m.memory_id = gc.memory_id
    WHERE gc.trace_id = $1
),
interventions AS (
    SELECT
        intervention_type,
        target_memory_id,
        target_depth,
        baseline_decision,
        counterfactual_decision,
        decision_changed,
        effect_score
    FROM intervention_runs
    WHERE trace_id = $1
)
SELECT
    (SELECT row_to_json(t) FROM traces t WHERE t.trace_id = $1) AS trace,
    COALESCE((SELECT json_agg(r ORDER BY retrieval_rank) FROM retrieved r), '[]'::JSON) AS retrieved,
    COALESCE((SELECT json_agg(c ORDER BY claimed_rank) FROM claimed c), '[]'::JSON) AS claimed,
    COALESCE((SELECT json_agg(i) FROM interventions i), '[]'::JSON) AS interventions;
