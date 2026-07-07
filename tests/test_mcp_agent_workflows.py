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


def test_task_search_then_compare(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    found = mcp_call(server, "find_papers_by_task", {"task": "mobility prediction"})
    ids = [p["paper_id"] for p in found["papers"]]
    assert ids
    compare = mcp_call(server, "compare_papers", {"paper_ids": ids[:2]})
    assert "markdown_table" in compare
    assert compare["papers"]


def test_method_search_then_neighbors(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    found = mcp_call(server, "find_papers_by_method", {"method": "GNN"})
    assert found["papers"]
    paper_id = found["papers"][0]["paper_id"]
    neighbors = mcp_call(server, "get_paper_neighbors", {"paper_id": paper_id})
    assert "neighbors" in neighbors


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
    outline = mcp_call(server, "generate_related_work_outline", {"topic": "GNN"})
    assert outline.get("sections")
    limits = mcp_call(server, "find_limitations", {"topic": "graph"})
    assert "limitations" in limits
