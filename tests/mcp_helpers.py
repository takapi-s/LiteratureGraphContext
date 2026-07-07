"""Helpers for MCP integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.mcp.server import MCPServer


def setup_mcp_project(project_tmp: Path, monkeypatch) -> MCPServer:
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_fixture_graph(resolve_context(project_tmp))
    return MCPServer(project_tmp)


def mcp_call(server: MCPServer, tool: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": args or {}},
    })
    assert response is not None
    text = response["result"]["content"][0]["text"]
    return json.loads(text)


def assert_tool_result(payload: Dict[str, Any], case: Dict[str, Any]) -> None:
    if case.get("allow_error"):
        return
    if case.get("no_error"):
        assert "error" not in payload, payload.get("error")
    for key in case.get("expect_keys", []):
        assert key in payload, f"missing key {key} in {payload.keys()}"
    min_list = case.get("min_list")
    if min_list:
        field, minimum = min_list
        assert len(payload.get(field, [])) >= minimum
