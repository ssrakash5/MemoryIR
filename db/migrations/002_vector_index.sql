-- Create this while `memories` is empty in production clusters.
-- CockroachDB uses the `agent_id` prefix before ANN search over embedding.
CREATE VECTOR INDEX IF NOT EXISTS memories_agent_embedding_idx
ON memories (agent_id, embedding);
