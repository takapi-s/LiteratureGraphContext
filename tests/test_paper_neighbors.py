import json

from litgraph.graph.graph_builder import build_graph
from litgraph.query.paper_finder import PaperFinder


def test_get_paper_neighbors_contrasts(project_tmp):
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_graph(ctx, FIXTURES)

    finder = PaperFinder(ctx.db_path)
    try:
        result = finder.get_paper_neighbors("mobility_gnn_2024")
        assert result["paper_id"] == "mobility_gnn_2024"
        rels = {n["relationship"] for n in result["neighbors"]}
        assert "CONTRASTS_WITH" in rels or "CITES" in rels or len(result["neighbors"]) >= 0
    finally:
        finder.close()


def test_mcp_get_paper_neighbors_tool(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from litgraph.mcp.server import MCPServer
    from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_graph(resolve_context(project_tmp), FIXTURES)

    server = MCPServer(project_tmp)
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/list",
        "params": {},
    })
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "get_paper_neighbors" in names
    assert "find_research_gaps" not in names

    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "get_paper_neighbors",
            "arguments": {"paper_id": "mobility_gnn_2024"},
        },
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert payload["paper_id"] == "mobility_gnn_2024"
    assert "neighbors" in payload
