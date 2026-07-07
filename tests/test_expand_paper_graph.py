"""Tests for multi-hop graph expansion."""

from litgraph.graph.graph_builder import build_graph
from litgraph.query.paper_finder import PaperFinder
from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures


def test_expand_paper_graph_shared_method(project_tmp):
    from litgraph.cli.config_manager import init_project, resolve_context

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_graph(ctx, FIXTURES)

    finder = PaperFinder(ctx.db_path)
    result = finder.expand_paper_graph("mobility_gnn_2024", hops=2, relationships=["SHARED_METHOD"])
    assert result["paper_id"] == "mobility_gnn_2024"
    assert result["count"] >= 0


def test_expand_paper_graph_unknown_paper(project_tmp):
    from litgraph.cli.config_manager import init_project, resolve_context

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_graph(ctx, FIXTURES)

    finder = PaperFinder(ctx.db_path)
    result = finder.expand_paper_graph("missing_paper")
    assert "error" in result
