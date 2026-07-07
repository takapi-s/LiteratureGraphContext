"""Contract tests for all MCP tools."""

import pytest

from litgraph.mcp.tool_definitions import TOOLS
from tests.fixtures.mcp_tool_cases import mcp_tool_cases
from tests.mcp_helpers import assert_tool_result, mcp_call, setup_mcp_project


@pytest.mark.parametrize("case", mcp_tool_cases(), ids=lambda c: c["tool"] + (f"_{c['args']}" if c.get("args") else ""))
def test_mcp_tool_contract(project_tmp, monkeypatch, case):
    server = setup_mcp_project(project_tmp, monkeypatch)
    payload = mcp_call(server, case["tool"], case["args"])
    assert_tool_result(payload, case)


def test_mcp_tools_list_matches_definitions(project_tmp, monkeypatch):
    server = setup_mcp_project(project_tmp, monkeypatch)
    resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == set(TOOLS.keys())
