"""MCP stdio server."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from litgraph.cli.config_manager import load_env, resolve_context
from litgraph.mcp import tool_definitions
from litgraph.mcp.handlers import query_handlers
from litgraph.query.paper_finder import PaperFinder

INSTRUCTIONS = (
    "LiteratureGraphContext provides structured literature review over indexed paper PDFs. "
    "Always cite paper_id, title, page, section, and evidence_text when answering."
)


class MCPServer:
    def __init__(self, cwd: Path | None = None) -> None:
        load_env()
        self.ctx = resolve_context(cwd)
        self.finder = PaperFinder(self.ctx.db_path)
        self.tools = list(tool_definitions.TOOLS.values())

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params") or {}

        if method == "initialize":
            return self._result(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "literature-graph-context", "version": "0.1.0"},
                "instructions": INSTRUCTIONS,
            })

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            return self._result(req_id, {"tools": self.tools})

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            content = self.handle_tool_call(name, args)
            return self._result(req_id, {
                "content": [{"type": "text", "text": json.dumps(content, ensure_ascii=False, indent=2)}],
                "isError": "error" in content,
            })

        if method == "ping":
            return self._result(req_id, {})

        return self._error(req_id, -32601, f"Method not found: {method}")

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if name == "list_papers":
                return query_handlers.handle_list_papers(self.finder)
            if name == "summarize_paper":
                return query_handlers.handle_summarize_paper(self.finder, args["paper_id"])
            if name == "find_papers_by_method":
                return query_handlers.handle_find_papers_by_method(self.finder, args["method"])
            if name == "find_papers_by_task":
                return query_handlers.handle_find_papers_by_task(self.finder, args["task"])
            if name == "find_limitations":
                return query_handlers.handle_find_limitations(self.finder, args["topic"])
            if name == "get_evidence_for_claim":
                return query_handlers.handle_get_evidence_for_claim(self.finder, args["claim_id"])
            if name == "compare_papers":
                return query_handlers.handle_compare_papers(self.finder, args["paper_ids"])
            return {"error": f"Unknown tool: {name}"}
        except Exception as exc:
            return {"error": str(exc)}

    def _result(self, req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def run(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = self.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
