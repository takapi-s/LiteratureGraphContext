"""MCP tool dispatch service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.cli.config_manager import ResolvedContext, get_config_value, resolve_context
from litgraph.graph.graph_builder import _neo4j_config
from litgraph.mcp import tool_definitions
from litgraph.query.paper_finder import PaperFinder
from litgraph.utils.tool_limits import apply_response_token_limit, compact_tool_result, truncate_results


_DEPRECATED_REDIRECTS: Dict[str, Optional[str]] = {
    "get_paper_neighbors": "explore_paper_graph",
    "expand_paper_graph": "explore_paper_graph",
    "find_papers_by_method": "search_papers",
    "find_papers_by_task": "search_papers",
    "build_literature_matrix": "compare_papers",
    "get_evidence_for_claim": "summarize_paper",
    "generate_related_work_outline": None,
    "list_jobs": None,
    "check_job_status": None,
}

_DEPRECATION_MESSAGES: Dict[str, str] = {
    "get_paper_neighbors": "Use explore_paper_graph with hops=1 instead.",
    "expand_paper_graph": "Use explore_paper_graph with hops>=2 instead.",
    "find_papers_by_method": "Use search_papers for discovery, or litgraph query papers --method for exact lookup.",
    "find_papers_by_task": "Use search_papers for discovery, or litgraph query papers --task for exact lookup.",
    "build_literature_matrix": "Use compare_papers on search_papers results, or litgraph query matrix --topic.",
    "get_evidence_for_claim": "Use summarize_paper; claims include claim_id and evidence_text.",
    "generate_related_work_outline": "Draft related work in the connected agent using compare_papers and find_limitations.",
    "list_jobs": "Use litgraph jobs for background extract job listing.",
    "check_job_status": "Use litgraph jobs for background extract job status.",
}


class MCPToolService:
    """Shared tool execution logic for MCP transports."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.ctx: ResolvedContext = resolve_context(cwd)
        backend = str(get_config_value(self.ctx, "database", "LITGRAPH_DATABASE"))
        self.finder = PaperFinder(
            self.ctx.db_path,
            aliases_path=self.ctx.aliases_path,
            backend=backend,
            neo4j_config=_neo4j_config(self.ctx),
            read_only=True,
        )

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return list(tool_definitions.TOOLS.values())

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self._dispatch(name, args)
            if "error" not in result and "deprecated" not in result:
                result = compact_tool_result(name, result)
            return result
        except Exception as exc:
            return {"error": str(exc)}

    def _deprecated_response(self, name: str) -> Dict[str, Any]:
        use_instead = _DEPRECATED_REDIRECTS.get(name)
        payload: Dict[str, Any] = {
            "deprecated": True,
            "removed_tool": name,
            "message": _DEPRECATION_MESSAGES.get(name, f"Tool {name} was removed from MCP in v0.7."),
        }
        if use_instead:
            payload["use_instead"] = use_instead
        return payload

    def _dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name in _DEPRECATED_REDIRECTS:
            return self._deprecated_response(name)
        if name == "list_papers":
            return {"papers": truncate_results(self.finder.list_papers())}
        if name == "summarize_paper":
            return self.finder.summarize_paper(args["paper_id"])
        if name == "find_limitations":
            return truncate_results(
                self.finder.find_limitations(
                    topic=args.get("topic", ""),
                    paper_id=args.get("paper_id"),
                )
            )
        if name == "compare_papers":
            return self.finder.compare_papers(args["paper_ids"])
        if name == "search_papers":
            return truncate_results(
                self.finder.search_papers(
                    args["query"],
                    top_k=int(args.get("top_k", 10)),
                    center_paper_id=args.get("center_paper_id"),
                )
            )
        if name == "explore_paper_graph":
            return truncate_results(
                self.finder.explore_paper_graph(
                    args["paper_id"],
                    hops=int(args.get("hops", 1)),
                    relationships=args.get("relationships"),
                    include_summary=bool(args.get("include_summary", False)),
                )
            )
        return {"error": f"Unknown tool: {name}"}

    def format_tool_result(self, name: str, result: Dict[str, Any]) -> str:
        import json

        if "error" in result:
            return json.dumps(result, ensure_ascii=False, indent=2)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return apply_response_token_limit(name, text)

    def close(self) -> None:
        self.finder.close()
