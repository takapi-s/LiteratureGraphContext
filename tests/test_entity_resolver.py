"""Tests for catalog-based entity resolution (no aliases)."""

from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.graph.entity_resolver import (
    EntityResolver,
    acronym_of,
    normalize_key,
    safe_merge,
)


def _resolver(*, disambiguation_enabled: bool = False) -> EntityResolver:
    return EntityResolver({
        "entity_resolution": {
            "auto_merge_threshold": 0.92,
            "candidate_threshold": 0.82,
            "disambiguation_enabled": disambiguation_enabled,
        },
    })


def test_normalize_key_strips_punctuation():
    assert normalize_key("Graph Convolutional Network (GCN)") == "graph convolutional network gcn"


def test_safe_merge_rejects_low_token_overlap():
    assert not safe_merge("stgcn", normalize_key("Graph Neural Network"))
    assert not safe_merge("bysgnn", normalize_key("Graph Neural Network"))


def test_safe_merge_accepts_synonym_variants():
    key_a = normalize_key("Graph Convolutional Network")
    key_b = normalize_key("graph convolutional networks")
    assert safe_merge(key_a, key_b)


def test_acronym_of_multi_word_name():
    assert acronym_of("Graph Neural Network") == "gnn"


def test_resolve_exact_match():
    catalog = EntityCatalog()
    catalog.add("method", "Graph Neural Network")
    resolver = _resolver()
    assert resolver.resolve("graph neural network", "method", catalog) == "Graph Neural Network"
    assert resolver.stats["resolved"] == 1


def test_resolve_gnn_acronym_to_full_name():
    catalog = EntityCatalog()
    catalog.add("method", "Graph Neural Network")
    resolver = _resolver()
    assert resolver.resolve("GNN", "method", catalog) == "Graph Neural Network"


def test_stgcn_not_merged_to_gnn():
    catalog = EntityCatalog()
    catalog.add("method", "Graph Neural Network")
    resolver = _resolver()
    assert resolver.resolve("STGCN", "method", catalog) == "STGCN"
    assert resolver.stats["new"] == 1


def test_fuzzy_merge_graph_convolutional_variants():
    catalog = EntityCatalog()
    catalog.add("method", "Graph Convolutional Network")
    resolver = _resolver()
    resolved = resolver.resolve("graph convolutional networks", "method", catalog)
    assert resolved == "Graph Convolutional Network"


def test_batch_catalog_ingest_unifies_gnn():
    catalog = EntityCatalog()
    resolver = _resolver()
    first = resolver.normalize_extraction(
        {"paper_id": "a", "methods": ["Graph Neural Network"], "tasks": [], "datasets": []},
        catalog,
    )
    catalog.ingest_extraction(first)
    second = resolver.normalize_extraction(
        {"paper_id": "b", "methods": ["GNN"], "tasks": [], "datasets": []},
        catalog,
    )
    assert second["methods"] == ["Graph Neural Network"]


def test_resolve_query_name_does_not_mutate_build_stats():
    catalog = EntityCatalog()
    catalog.add("method", "Graph Neural Network")
    resolver = _resolver()
    resolver.stats = {"resolved": 5, "disambiguated": 1, "new": 2}
    assert resolver.resolve_query_name("GNN", "method", catalog) == "Graph Neural Network"
    assert resolver.stats == {"resolved": 5, "disambiguated": 1, "new": 2}
