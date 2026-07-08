"""Agent-style MCP workflow tests."""

import pytest

from tests.mcp_helpers import mcp_call, setup_mcp_project


def test_ambiguous_search_then_summarize(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    search = mcp_call(server, "search_papers", {"query": "graph neural network"})
    assert search["count"] >= 1
    paper_id = search["papers"][0]["paper_id"]
    assert search["papers"][0].get("title")
    summary = mcp_call(server, "summarize_paper", {"paper_id": paper_id})
    assert "error" not in summary
    assert summary.get("title")
    assert "claims" in summary


def test_search_then_compare(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    found = mcp_call(server, "search_papers", {"query": "mobility prediction"})
    ids = [p["paper_id"] for p in found["papers"]]
    assert ids
    compare = mcp_call(server, "compare_papers", {"paper_ids": ids[:2]})
    assert "markdown_table" in compare
    assert compare["papers"]


def test_search_then_explore_graph(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    found = mcp_call(server, "search_papers", {"query": "GNN"})
    assert found["papers"]
    paper_id = found["papers"][0]["paper_id"]
    graph = mcp_call(server, "explore_paper_graph", {"paper_id": paper_id, "hops": 1})
    assert "nodes" in graph
    assert graph["hops"] == 1


def test_list_papers_id_consistency(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    listed = mcp_call(server, "list_papers")
    for paper in listed["papers"]:
        pid = paper["paper_id"]
        summary = mcp_call(server, "summarize_paper", {"paper_id": pid})
        assert "error" not in summary, f"summarize failed for {pid}: {summary}"


@pytest.mark.parametrize("query", ["GNN", "graph neural network", "mobility", "traffic forecasting"])
def test_ambiguous_query_variations(project_tmp, monkeypatch, query):
    server = setup_mcp_project(project_tmp, monkeypatch)
    result = mcp_call(server, "search_papers", {"query": query, "top_k": 5})
    assert "count" in result
    assert result["count"] >= 0
    for paper in result.get("papers", []):
        assert paper.get("paper_id")
        assert paper.get("title")


def test_full_literature_review_chain(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    search = mcp_call(server, "search_papers", {"query": "GNN"})
    ids = [p["paper_id"] for p in search["papers"][:3]]
    assert ids
    compare = mcp_call(server, "compare_papers", {"paper_ids": ids})
    assert "error" not in compare
    limits = mcp_call(server, "find_limitations", {"topic": "graph"})
    assert "limitations" in limits
    graph = mcp_call(server, "explore_paper_graph", {"paper_id": ids[0], "hops": 2})
    assert "nodes" in graph


def test_deprecated_tool_redirect(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    payload = mcp_call(server, "get_paper_neighbors", {"paper_id": "mobility_gnn_2024"})
    assert payload.get("deprecated") is True
    assert payload.get("use_instead") == "explore_paper_graph"
