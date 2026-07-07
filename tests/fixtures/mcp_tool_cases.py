"""Shared MCP tool test case definitions."""

from __future__ import annotations

from typing import Any, Dict, List

from tests.fixtures.extracted_fixtures import claim_id_for, primary_paper_id


def mcp_tool_cases() -> List[Dict[str, Any]]:
  pid = primary_paper_id()
  bysgnn = "bysgnn_2023"
  stgcn = "stgcn_2018"
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
      {"tool": "get_evidence_for_claim", "args": {"claim_id": claim_id_for(pid)}, "no_error": True},
      {"tool": "get_paper_neighbors", "args": {"paper_id": bysgnn}, "expect_keys": ["neighbors", "paper_id"], "no_error": True},
      {"tool": "expand_paper_graph", "args": {"paper_id": bysgnn, "hops": 1}, "expect_keys": ["papers", "paper_id"], "no_error": True},
      {"tool": "generate_related_work_outline", "args": {"topic": "GNN"}, "expect_keys": ["markdown_outline", "sections"], "no_error": True},
      {"tool": "list_jobs", "args": {}, "expect_keys": ["jobs"], "no_error": True},
      {"tool": "check_job_status", "args": {"job_id": "nonexistent-job"}, "allow_error": True},
  ]
