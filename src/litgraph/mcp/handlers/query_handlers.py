"""MCP query handlers."""

from __future__ import annotations

from typing import Any, Dict, List

from litgraph.query.paper_finder import PaperFinder
from litgraph.utils.tool_limits import truncate_results


def handle_list_papers(finder: PaperFinder) -> Dict[str, Any]:
    return {"papers": truncate_results(finder.list_papers())}


def handle_summarize_paper(finder: PaperFinder, paper_id: str) -> Dict[str, Any]:
    return finder.summarize_paper(paper_id)


def handle_find_papers_by_method(finder: PaperFinder, method: str) -> Dict[str, Any]:
    return {"papers": truncate_results(finder.find_papers_by_method(method))}


def handle_find_papers_by_task(finder: PaperFinder, task: str) -> Dict[str, Any]:
    return {"papers": truncate_results(finder.find_papers_by_task(task))}


def handle_find_limitations(finder: PaperFinder, topic: str) -> Dict[str, Any]:
    return truncate_results(finder.find_limitations(topic))


def handle_get_evidence_for_claim(finder: PaperFinder, claim_id: str) -> Dict[str, Any]:
    return finder.get_evidence_for_claim(claim_id)


def handle_compare_papers(finder: PaperFinder, paper_ids: List[str]) -> Dict[str, Any]:
    return finder.compare_papers(paper_ids)
