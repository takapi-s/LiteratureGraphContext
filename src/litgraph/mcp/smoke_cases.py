"""MCP smoke-test case definitions for CLI and pytest."""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from litgraph.mcp.tool_service import MCPToolService


def fixture_smoke_cases() -> List[Dict[str, Any]]:
    """Fixed cases for pytest against the demo fixture graph."""
    pid = "mobility_gnn_2024"
    bysgnn = "bysgnn_2023"
    return [
        {"tool": "list_papers", "args": {}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "search_papers", "args": {"query": "GNN"}, "expect_keys": ["papers", "count"], "min_list": ("papers", 1)},
        {"tool": "summarize_paper", "args": {"paper_id": pid}, "expect_keys": ["title", "paper_id", "claims"], "no_error": True},
        {"tool": "compare_papers", "args": {"paper_ids": [pid, bysgnn]}, "expect_keys": ["papers", "markdown_table"], "no_error": True},
        {"tool": "find_limitations", "args": {"topic": "event"}, "expect_keys": ["limitations"], "no_error": True},
        {"tool": "find_limitations", "args": {"paper_id": bysgnn}, "expect_keys": ["limitations", "paper_id"], "no_error": True},
        {"tool": "explore_paper_graph", "args": {"paper_id": bysgnn, "hops": 1}, "expect_keys": ["nodes", "paper_id", "hops"], "no_error": True},
        {"tool": "explore_paper_graph", "args": {"paper_id": bysgnn, "hops": 2}, "expect_keys": ["nodes", "paper_id", "hops"], "no_error": True},
    ]


def deprecated_redirect_cases() -> List[Dict[str, Any]]:
    """Smoke cases for removed MCP tools that return redirect payloads."""
    return [
        {"tool": "get_paper_neighbors", "args": {"paper_id": "mobility_gnn_2024"}, "expect_keys": ["deprecated", "use_instead"]},
        {"tool": "expand_paper_graph", "args": {"paper_id": "mobility_gnn_2024", "hops": 2}, "expect_keys": ["deprecated", "use_instead"]},
        {"tool": "find_papers_by_method", "args": {"method": "GNN"}, "expect_keys": ["deprecated", "use_instead"]},
        {"tool": "get_evidence_for_claim", "args": {"claim_id": "claim_mobility_gnn_2024_000"}, "expect_keys": ["deprecated", "use_instead"]},
        {"tool": "list_jobs", "args": {}, "expect_keys": ["deprecated"]},
    ]


def project_smoke_cases(service: MCPToolService) -> List[Dict[str, Any]]:
    """Build smoke cases from the indexed papers in a real project."""
    papers = service.finder.list_papers()
    if not papers:
        return []

    primary = papers[0]
    pid = str(primary.get("paper_id") or "")
    pid2 = str(papers[1].get("paper_id") or pid) if len(papers) > 1 else pid
    title = str(primary.get("title") or "graph")
    search_query = title.split()[0] if title.split() else "graph"
    task = (primary.get("tasks") or ["prediction"])[0]

    cases: List[Dict[str, Any]] = [
        {"tool": "list_papers", "args": {}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "search_papers", "args": {"query": search_query}, "expect_keys": ["papers", "count"]},
        {"tool": "summarize_paper", "args": {"paper_id": pid}, "expect_keys": ["title", "paper_id"], "no_error": True},
        {"tool": "compare_papers", "args": {"paper_ids": [pid, pid2]}, "expect_keys": ["papers", "markdown_table"], "no_error": True},
        {"tool": "find_limitations", "args": {"topic": task}, "expect_keys": ["limitations"], "no_error": True},
        {"tool": "find_limitations", "args": {"paper_id": pid}, "expect_keys": ["limitations", "paper_id"], "no_error": True},
        {"tool": "explore_paper_graph", "args": {"paper_id": pid, "hops": 1}, "expect_keys": ["nodes", "paper_id", "hops"], "no_error": True},
        {"tool": "explore_paper_graph", "args": {"paper_id": pid, "hops": 2}, "expect_keys": ["nodes", "paper_id", "hops"], "no_error": True},
    ]
    return cases
