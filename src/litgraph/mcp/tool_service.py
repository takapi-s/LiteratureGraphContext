"""MCP tool dispatch service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.cli.config_manager import ResolvedContext, get_config_value, resolve_context
from litgraph.cli.helpers import check_job_status, list_jobs
from litgraph.graph.graph_builder import _neo4j_config
from litgraph.mcp import tool_definitions
from litgraph.query.paper_finder import PaperFinder
from litgraph.utils.tool_limits import apply_response_token_limit, compact_tool_result, truncate_results


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
        )

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return list(tool_definitions.TOOLS.values())

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self._dispatch(name, args)
            if "error" not in result:
                result = compact_tool_result(name, result)
            return result
        except Exception as exc:
            return {"error": str(exc)}

    def _dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "list_papers":
            return {"papers": truncate_results(self.finder.list_papers())}
        if name == "summarize_paper":
            return self.finder.summarize_paper(args["paper_id"])
        if name == "find_papers_by_method":
            return {"papers": truncate_results(self.finder.find_papers_by_method(args["method"]))}
        if name == "find_papers_by_task":
            return {"papers": truncate_results(self.finder.find_papers_by_task(args["task"]))}
        if name == "find_limitations":
            return truncate_results(
                self.finder.find_limitations(
                    topic=args.get("topic", ""),
                    paper_id=args.get("paper_id"),
                )
            )
        if name == "get_evidence_for_claim":
            return self.finder.get_evidence_for_claim(args["claim_id"])
        if name == "compare_papers":
            return self.finder.compare_papers(args["paper_ids"])
        if name == "build_literature_matrix":
            return truncate_results(self.finder.build_literature_matrix(args["topic"]))
        if name == "get_paper_neighbors":
            return truncate_results(
                self.finder.get_paper_neighbors(
                    args["paper_id"],
                    relationships=args.get("relationships"),
                    include_summary=bool(args.get("include_summary", False)),
                )
            )
        if name == "search_papers":
            return truncate_results(
                self.finder.search_papers(
                    args["query"],
                    top_k=int(args.get("top_k", 10)),
                    center_paper_id=args.get("center_paper_id"),
                )
            )
        if name == "expand_paper_graph":
            return truncate_results(
                self.finder.expand_paper_graph(
                    args["paper_id"],
                    hops=int(args.get("hops", 2)),
                    relationships=args.get("relationships"),
                    include_summary=bool(args.get("include_summary", False)),
                )
            )
        if name == "generate_related_work_outline":
            return self.finder.related_work_outline(args["topic"])
        if name == "check_job_status":
            return check_job_status(args["job_id"])
        if name == "list_jobs":
            return {"jobs": list_jobs()}
        return {"error": f"Unknown tool: {name}"}

    def format_tool_result(self, name: str, result: Dict[str, Any]) -> str:
        import json

        if "error" in result:
            return json.dumps(result, ensure_ascii=False, indent=2)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return apply_response_token_limit(name, text)

    def close(self) -> None:
        self.finder.close()
