"""MCP smoke-test case definitions for CLI and pytest."""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from litgraph.mcp.tool_service import MCPToolService


def fixture_smoke_cases() -> List[Dict[str, Any]]:
    """Fixed cases for pytest against the demo fixture graph."""
    from litgraph.utils.ids import claim_id

    pid = "mobility_gnn_2024"
    bysgnn = "bysgnn_2023"
    return [
        {"tool": "list_papers", "args": {}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "search_papers", "args": {"query": "GNN"}, "expect_keys": ["papers", "count"], "min_list": ("papers", 1)},
        {"tool": "find_papers_by_method", "args": {"method": "Graph Neural Network"}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "find_papers_by_task", "args": {"task": "mobility prediction"}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "summarize_paper", "args": {"paper_id": pid}, "expect_keys": ["title", "paper_id"], "no_error": True},
        {"tool": "compare_papers", "args": {"paper_ids": [pid, bysgnn]}, "expect_keys": ["papers", "markdown_table"], "no_error": True},
        {"tool": "build_literature_matrix", "args": {"topic": "GNN"}, "expect_keys": ["papers", "topic"], "no_error": True},
        {"tool": "find_limitations", "args": {"topic": "event"}, "expect_keys": ["limitations"], "no_error": True},
        {"tool": "find_limitations", "args": {"paper_id": bysgnn}, "expect_keys": ["limitations", "paper_id"], "no_error": True},
        {"tool": "get_evidence_for_claim", "args": {"claim_id": claim_id(pid, 0)}, "no_error": True},
        {"tool": "get_paper_neighbors", "args": {"paper_id": bysgnn}, "expect_keys": ["neighbors", "paper_id"], "no_error": True},
        {"tool": "expand_paper_graph", "args": {"paper_id": bysgnn, "hops": 1}, "expect_keys": ["papers", "paper_id"], "no_error": True},
        {"tool": "generate_related_work_outline", "args": {"topic": "GNN"}, "expect_keys": ["markdown_outline", "sections"], "no_error": True},
        {"tool": "list_jobs", "args": {}, "expect_keys": ["jobs"], "no_error": True},
        {"tool": "check_job_status", "args": {"job_id": "nonexistent-job"}, "allow_error": True},
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
    method = (primary.get("methods") or ["Graph Neural Network"])[0]
    task = (primary.get("tasks") or ["prediction"])[0]

    summary = service.finder.summarize_paper(pid)
    claim_id_value = None
    for claim in summary.get("claims") or []:
        if isinstance(claim, dict) and claim.get("claim_id"):
            claim_id_value = claim["claim_id"]
            break
    if not claim_id_value:
        claim_id_value = f"claim_{pid}_000"

    cases: List[Dict[str, Any]] = [
        {"tool": "list_papers", "args": {}, "expect_keys": ["papers"], "min_list": ("papers", 1)},
        {"tool": "search_papers", "args": {"query": search_query}, "expect_keys": ["papers", "count"]},
        {"tool": "find_papers_by_method", "args": {"method": method}, "expect_keys": ["papers"]},
        {"tool": "find_papers_by_task", "args": {"task": task}, "expect_keys": ["papers"]},
        {"tool": "summarize_paper", "args": {"paper_id": pid}, "expect_keys": ["title", "paper_id"], "no_error": True},
        {"tool": "compare_papers", "args": {"paper_ids": [pid, pid2]}, "expect_keys": ["papers", "markdown_table"], "no_error": True},
        {"tool": "build_literature_matrix", "args": {"topic": search_query}, "expect_keys": ["papers", "topic"], "no_error": True},
        {"tool": "find_limitations", "args": {"topic": task}, "expect_keys": ["limitations"], "no_error": True},
        {"tool": "find_limitations", "args": {"paper_id": pid}, "expect_keys": ["limitations", "paper_id"], "no_error": True},
        {"tool": "get_paper_neighbors", "args": {"paper_id": pid}, "expect_keys": ["neighbors", "paper_id"], "no_error": True},
        {"tool": "expand_paper_graph", "args": {"paper_id": pid, "hops": 1}, "expect_keys": ["papers", "paper_id"], "no_error": True},
        {"tool": "generate_related_work_outline", "args": {"topic": search_query}, "expect_keys": ["markdown_outline", "sections"], "no_error": True},
        {"tool": "list_jobs", "args": {}, "expect_keys": ["jobs"], "no_error": True},
        {"tool": "check_job_status", "args": {"job_id": "nonexistent-job"}, "allow_error": True},
    ]
    if "error" not in summary and (summary.get("claims") or []):
        cases.insert(9, {
            "tool": "get_evidence_for_claim",
            "args": {"claim_id": claim_id_value},
            "no_error": True,
        })
    return cases
