"""MCP query handlers (delegates to MCPToolService)."""

from __future__ import annotations

from typing import Any, Dict, List

from litgraph.mcp.tool_service import MCPToolService
from litgraph.query.paper_finder import PaperFinder


def _service(finder: PaperFinder) -> MCPToolService:
    svc = MCPToolService()
    svc.finder = finder
    return svc


def handle_list_papers(finder: PaperFinder) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("list_papers", {})


def handle_summarize_paper(finder: PaperFinder, paper_id: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("summarize_paper", {"paper_id": paper_id})


def handle_find_papers_by_method(finder: PaperFinder, method: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("find_papers_by_method", {"method": method})


def handle_find_papers_by_task(finder: PaperFinder, task: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("find_papers_by_task", {"task": task})


def handle_find_limitations(finder: PaperFinder, topic: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("find_limitations", {"topic": topic})


def handle_get_evidence_for_claim(finder: PaperFinder, claim_id: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("get_evidence_for_claim", {"claim_id": claim_id})


def handle_compare_papers(finder: PaperFinder, paper_ids: List[str]) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("compare_papers", {"paper_ids": paper_ids})


def handle_build_literature_matrix(finder: PaperFinder, topic: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("build_literature_matrix", {"topic": topic})


def handle_find_research_gaps(finder: PaperFinder, topic: str, min_papers: int = 1) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("find_research_gaps", {"topic": topic, "min_papers": min_papers})


def handle_generate_related_work_outline(finder: PaperFinder, topic: str) -> Dict[str, Any]:
    return _service(finder).handle_tool_call("generate_related_work_outline", {"topic": topic})


def handle_check_job_status(job_id: str) -> Dict[str, Any]:
    return MCPToolService().handle_tool_call("check_job_status", {"job_id": job_id})


def handle_list_jobs() -> Dict[str, Any]:
    return MCPToolService().handle_tool_call("list_jobs", {})
