from __future__ import annotations


def test_lineage_finds_demo_ground_ancestors(services):
    edges = services.store.ancestry("M7")
    parents = {services.store.get_memory(edge.parent_memory_id).display_id for edge in edges}

    assert parents == {"M1", "M2", "M3"}
    assert max(edge.depth for edge in edges) == 1
