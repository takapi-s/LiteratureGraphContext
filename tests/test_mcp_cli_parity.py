"""MCP vs direct PaperFinder parity tests."""

import json

from litgraph.mcp.tool_service import MCPToolService
from tests.mcp_helpers import setup_mcp_project


def test_mcp_matches_finder_for_summarize(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    pid = "mobility_gnn_2024"
    mcp_result = server.handle_tool_call("summarize_paper", {"paper_id": pid})
    finder_result = server.service.finder.summarize_paper(pid)
    assert mcp_result.get("paper_id") == finder_result.get("paper_id")
    assert mcp_result.get("title") == finder_result.get("title")


def test_mcp_formatted_result_not_empty(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    result = server.handle_tool_call("compare_papers", {"paper_ids": ["mobility_gnn_2024", "bysgnn_2023"]})
    text = server.service.format_tool_result("compare_papers", result)
    payload = json.loads(text)
    assert payload.get("papers")
    assert payload.get("markdown_table")
    assert "_truncated" not in text or len(text) > 100
