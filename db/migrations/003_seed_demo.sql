-- Deterministic demo rows for the MemoryIR three-minute walkthrough.
-- Embeddings are intentionally left NULL here because the runtime provider
-- should write model-specific 256-dimension vectors via `/api/demo/reset`.

INSERT INTO agents (agent_id, name, description, model_id)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'MemoryIR Demo Agent',
    'Hackathon demo agent for persistent-memory forensics.',
    'mock'
) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO sessions (session_id, agent_id, title)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'CockroachDB architecture demo'
) ON CONFLICT (session_id) DO NOTHING;

INSERT INTO memory_sources (source_id, source_type, source_name, trust_label, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    'SYNTHETIC_EVAL',
    'MemoryIR demo seed',
    'controlled',
    '{"scenario":"cockroach_demo"}'
) ON CONFLICT (source_id) DO NOTHING;

INSERT INTO memories
    (memory_id, agent_id, session_id, source_id, memory_type, content, embedding, generation, content_hash, metadata)
VALUES
    ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'raw', 'The team prefers PostgreSQL-compatible databases.', NULL, 0, 'demo-m1', '{"display_id":"M1"}'),
    ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'raw', 'The deployment must survive regional failures.', NULL, 0, 'demo-m2', '{"display_id":"M2"}'),
    ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'raw', 'The operations team wants a managed service.', NULL, 0, 'demo-m3', '{"display_id":"M3"}'),
    ('00000000-0000-0000-0000-000000000107', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'consolidated', 'The application should use a managed, PostgreSQL-compatible database with multi-region resilience.', NULL, 1, 'demo-m7', '{"display_id":"M7","input_memory_ids":["00000000-0000-0000-0000-000000000101","00000000-0000-0000-0000-000000000102","00000000-0000-0000-0000-000000000103"]}'),
    ('00000000-0000-0000-0000-000000000112', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'raw', 'The frontend team prefers TypeScript for the project.', NULL, 0, 'demo-m12', '{"display_id":"M12"}'),
    ('00000000-0000-0000-0000-000000000116', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'raw', 'The finance team wants operational costs to stay predictable.', NULL, 0, 'demo-m16', '{"display_id":"M16"}')
ON CONFLICT (memory_id) DO NOTHING;

INSERT INTO memory_edges (parent_memory_id, child_memory_id, relation_type, declared_weight)
VALUES
    ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000107', 'consolidated_from', 0.25),
    ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000107', 'consolidated_from', 0.50),
    ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000107', 'consolidated_from', 0.25)
ON CONFLICT (parent_memory_id, child_memory_id, relation_type) DO NOTHING;

INSERT INTO consolidation_runs
    (consolidation_id, agent_id, session_id, output_memory_id, model_id, prompt_version, input_count, latency_ms)
VALUES (
    '00000000-0000-0000-0000-000000000207',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000107',
    'mock',
    'demo-seed-v1',
    3,
    0
) ON CONFLICT (consolidation_id) DO NOTHING;
