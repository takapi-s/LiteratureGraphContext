"""MCP stdio server using the official MCP SDK."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from litgraph import __version__
from litgraph.cli.config_manager import load_env
from litgraph.mcp.tool_service import MCPToolService

INSTRUCTIONS = (
    "LiteratureGraphContext provides structured literature review over indexed paper PDFs. "
    "For ambiguous questions, call search_papers first to obtain paper_id and title, then use "
    "summarize_paper, compare_papers, find_limitations, or explore_paper_graph. "
    "Use explore_paper_graph with hops=1 for direct neighbors or hops>=2 for multi-hop lineage. "
    "Always cite paper_id, title, page, section, and evidence_text when answering."
)


class MCPServer:
    """Compatibility wrapper: exposes handle_request for tests and SDK run() for production."""

    def __init__(self, cwd: Path | None = None) -> None:
        load_env()
        self.service = MCPToolService(cwd)
        self.tools = self.service.tools

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.service.handle_tool_call(name, args)

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params") or {}

        if method == "initialize":
            return self._result(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "literature-graph-context", "version": __version__},
                "instructions": INSTRUCTIONS,
            })
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return self._result(req_id, {"tools": self.tools})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            result = self.handle_tool_call(name, args)
            text = self.service.format_tool_result(name, result)
            return self._result(req_id, {
                "content": [{"type": "text", "text": text}],
                "isError": "error" in result,
            })
        if method == "ping":
            return self._result(req_id, {})
        return self._error(req_id, -32601, f"Method not found: {method}")

    def _result(self, req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def run(self) -> None:
        """Run MCP server via official SDK stdio transport."""
        asyncio.run(_run_sdk_server(self.service))


async def _run_sdk_server(service: MCPToolService) -> None:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import ServerCapabilities, TextContent, ToolsCapability, Tool

    server = Server("literature-graph-context")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in service.tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}
        result = service.handle_tool_call(name, args)
        text = service.format_tool_result(name, result)
        if "error" in result:
            return [TextContent(type="text", text=text)]
        return [TextContent(type="text", text=text)]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="literature-graph-context",
                server_version=__version__,
                capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=False)),
                instructions=INSTRUCTIONS,
            ),
        )


def run_legacy_stdio(service: MCPServer) -> None:
    """Fallback hand-rolled stdio loop (used only if SDK import fails)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = service.handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
