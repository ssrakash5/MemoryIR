WITH RECURSIVE ancestry AS (
    SELECT
        parent_memory_id,
        child_memory_id,
        relation_type,
        declared_weight,
        1 AS depth
    FROM memory_edges
    WHERE child_memory_id = $1

    UNION ALL

    SELECT
        e.parent_memory_id,
        e.child_memory_id,
        e.relation_type,
        e.declared_weight,
        a.depth + 1
    FROM memory_edges e
    JOIN ancestry a
      ON e.child_memory_id = a.parent_memory_id
)
SELECT *
FROM ancestry
ORDER BY depth, parent_memory_id;
