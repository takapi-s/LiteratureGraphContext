"""Tests for hybrid paper search."""

from litgraph.query.paper_finder import PaperFinder
from litgraph.query.rrf import rrf
from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures


def test_rrf_merges_ranked_lists():
    merged = rrf([["a", "b"], ["b", "c"]])
    ids = [item for item, _ in merged]
    assert ids[0] == "b"


def test_search_papers_finds_gnn(project_tmp):
    from litgraph.cli.config_manager import init_project, resolve_context

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)

    finder = PaperFinder(ctx.db_path)
    result = finder.search_papers("GNN", top_k=5)
    assert result["count"] >= 1
    ids = {p["paper_id"] for p in result["papers"]}
    assert "mobility_gnn_2024" in ids
    assert all(p.get("title") for p in result["papers"])


def test_search_papers_empty_query(project_tmp):
    from litgraph.cli.config_manager import init_project, resolve_context

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)

    finder = PaperFinder(ctx.db_path)
    result = finder.search_papers("")
    assert result["papers"] == []
