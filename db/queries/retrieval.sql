SELECT
    memory_id,
    content,
    memory_type,
    generation,
    metadata,
    embedding <-> $2::VECTOR AS distance
FROM memories
WHERE agent_id = $1
  AND embedding IS NOT NULL
ORDER BY embedding <-> $2::VECTOR
LIMIT $3;
