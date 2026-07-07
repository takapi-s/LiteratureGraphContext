import json

from litgraph.mcp.server import MCPServer


def test_mcp_tools_list(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_fixture_graph(resolve_context(project_tmp))

    server = MCPServer(project_tmp)
    resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "find_limitations" in names

    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "find_limitations", "arguments": {"topic": "event"}},
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert payload["limitations"]


def test_mcp_compare_papers(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_fixture_graph(resolve_context(project_tmp))

    server = MCPServer(project_tmp)
    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "compare_papers",
            "arguments": {"paper_ids": ["mobility_gnn_2024", "event_forecasting_2025"]},
        },
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert "markdown_table" in payload
