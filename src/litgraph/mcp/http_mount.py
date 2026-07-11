"""Mount Streamable HTTP MCP on a shared FastAPI application."""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Optional

from litgraph import __version__
from litgraph.mcp.tool_service import MCPToolService

INSTRUCTIONS = (
    "LiteratureGraphContext provides structured literature review over indexed paper PDFs. "
    "For ambiguous questions, call search_papers first to obtain paper_id and title, then use "
    "summarize_paper, compare_papers, find_limitations, or explore_paper_graph. "
    "Use explore_paper_graph with hops=1 for direct neighbors or hops>=2 for multi-hop lineage. "
    "Always cite paper_id, title, page, section, and evidence_text when answering."
)


@asynccontextmanager
async def mcp_http_lifespan(
    service: MCPToolService,
    *,
    before_shutdown: Optional[Callable[[], None]] = None,
) -> AsyncIterator[None]:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.streamable_http import StreamableHTTPServerTransport
    from mcp.types import ServerCapabilities, TextContent, Tool, ToolsCapability

    transport = StreamableHTTPServerTransport(mcp_session_id=None, is_json_response_enabled=True)
    mcp_server = Server("literature-graph-context")

    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
            for t in service.tools
        ]

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        args = arguments or {}
        result = service.handle_tool_call(name, args)
        text = service.format_tool_result(name, result)
        return [TextContent(type="text", text=text)]

    async with transport.connect() as (read_stream, write_stream):
        run_task = asyncio.create_task(
            mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="literature-graph-context",
                    server_version=__version__,
                    capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=False)),
                    instructions=INSTRUCTIONS,
                ),
            )
        )
        try:
            yield transport
        finally:
            run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await run_task
            if before_shutdown is not None:
                before_shutdown()


class _MCPASGIApp:
    """Raw ASGI wrapper so FastAPI does not DI-parse or double-send the response."""

    def __init__(self, transport_holder: list) -> None:
        self._holder = transport_holder

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            return
        if not self._holder:
            from starlette.responses import JSONResponse

            await JSONResponse({"detail": "MCP transport not ready"}, status_code=503)(
                scope, receive, send
            )
            return
        await self._holder[0].handle_request(scope, receive, send)


def register_mcp_http_route(app, transport_holder: list) -> None:
    """Register ``/mcp`` for Streamable HTTP via a raw ASGI route.

    A FastAPI endpoint with a function-local ``Request`` import returns HTTP 422
    under ``from __future__ import annotations`` (``request`` is treated as a
    query param). Returning ``None`` after writing via ``request._send`` also
    double-sends the response. A Starlette ASGI class avoids both issues.
    """
    from starlette.routing import Route

    app.router.routes.insert(
        0,
        Route("/mcp", endpoint=_MCPASGIApp(transport_holder), methods=["GET", "POST", "DELETE"]),
    )
