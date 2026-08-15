CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    description STRING,
    model_id STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    title STRING,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type STRING NOT NULL,
    source_name STRING,
    source_uri STRING,
    trust_label STRING NOT NULL DEFAULT 'unknown',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),
    source_id UUID REFERENCES memory_sources(source_id),
    memory_type STRING NOT NULL,
    content STRING NOT NULL,
    embedding VECTOR(256),
    generation INT NOT NULL DEFAULT 0,
    content_hash STRING,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_memory_id UUID NOT NULL REFERENCES memories(memory_id),
    child_memory_id UUID NOT NULL REFERENCES memories(memory_id),
    relation_type STRING NOT NULL,
    declared_weight FLOAT8,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(parent_memory_id, child_memory_id, relation_type)
);

CREATE TABLE IF NOT EXISTS consolidation_runs (
    consolidation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),
    output_memory_id UUID NOT NULL REFERENCES memories(memory_id),
    model_id STRING NOT NULL,
    prompt_version STRING NOT NULL,
    input_count INT NOT NULL,
    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),
    user_query STRING NOT NULL,
    response_text STRING,
    decision_label STRING,
    model_id STRING,
    temperature FLOAT8,
    status STRING NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS retrieval_runs (
    retrieval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES traces(trace_id),
    query_text STRING NOT NULL,
    top_k INT NOT NULL,
    embedding_model STRING,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms INT
);

CREATE TABLE IF NOT EXISTS retrieval_items (
    retrieval_id UUID NOT NULL REFERENCES retrieval_runs(retrieval_id),
    memory_id UUID NOT NULL REFERENCES memories(memory_id),
    retrieval_rank INT NOT NULL,
    vector_distance FLOAT8 NOT NULL,
    PRIMARY KEY (retrieval_id, memory_id)
);

CREATE TABLE IF NOT EXISTS generation_claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES traces(trace_id),
    memory_id UUID REFERENCES memories(memory_id),
    claim_type STRING NOT NULL,
    claimed_rank INT,
    explanation STRING,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS intervention_runs (
    intervention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES traces(trace_id),
    intervention_type STRING NOT NULL,
    target_memory_id UUID REFERENCES memories(memory_id),
    target_depth INT DEFAULT 0,
    baseline_decision STRING,
    counterfactual_decision STRING,
    baseline_response STRING,
    counterfactual_response STRING,
    decision_changed BOOL,
    semantic_delta FLOAT8,
    effect_score FLOAT8,
    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memories_agent_idx ON memories(agent_id);
CREATE INDEX IF NOT EXISTS memory_edges_child_idx ON memory_edges(child_memory_id);
CREATE INDEX IF NOT EXISTS memory_edges_parent_idx ON memory_edges(parent_memory_id);
CREATE INDEX IF NOT EXISTS retrieval_runs_trace_idx ON retrieval_runs(trace_id);
CREATE INDEX IF NOT EXISTS generation_claims_trace_idx ON generation_claims(trace_id);
CREATE INDEX IF NOT EXISTS intervention_runs_trace_idx ON intervention_runs(trace_id);
