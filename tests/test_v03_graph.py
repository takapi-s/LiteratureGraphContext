import json

from litgraph.graph.graph_builder import build_graph
from litgraph.cli.config_manager import init_project, resolve_context
from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures


def test_graph_export_includes_edges(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    result = build_graph(ctx, FIXTURES)
    assert result["edges"] >= 0
    graph_path = project_tmp / ".litgraph" / "graph.json"
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert any(n["type"] == "Paper" for n in data["nodes"])


def test_full_compare(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_graph(ctx, FIXTURES)
    from litgraph.query.paper_finder import PaperFinder

    finder = PaperFinder(ctx.db_path, project_config=ctx.config)
    result = finder.compare_papers(["mobility_gnn_2024", "event_forecasting_2025"])
    assert "metric" in result["papers"][0]
    assert "difference" in result["papers"][0]
    assert "Contribution" in result["markdown_table"] or "contribution" in result["markdown_table"].lower()
