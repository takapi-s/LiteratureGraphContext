import json
from unittest.mock import MagicMock, patch

from litgraph.mcp.server import MCPServer


def test_mcp_find_research_gaps(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures
    from litgraph.graph.graph_builder import build_graph

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
    assert "find_research_gaps" in names
    assert "generate_related_work_outline" in names

    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "find_research_gaps",
            "arguments": {"topic": "event"},
        },
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert "gaps" in payload


def test_mcp_related_work_outline(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures
    from litgraph.graph.graph_builder import build_graph

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_graph(resolve_context(project_tmp), FIXTURES)

    server = MCPServer(project_tmp)
    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "generate_related_work_outline",
            "arguments": {"topic": "GNN"},
        },
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert "markdown_outline" in payload


def test_zotero_sync_mock(project_tmp):
    from litgraph.integrations.zotero import sync_zotero_library

    mock_items = [
        {
            "data": {
                "key": "ABC123",
                "title": "Test Paper",
                "itemType": "journalArticle",
                "creators": [{"creatorType": "author", "firstName": "A", "lastName": "B"}],
                "date": "2024",
                "DOI": "10.1/test",
                "version": 100,
            }
        }
    ]
    with patch("litgraph.integrations.zotero.httpx.Client") as mock_client:
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        resp = MagicMock()
        resp.json.return_value = mock_items
        resp.raise_for_status = MagicMock()
        instance.get.return_value = resp
        mock_client.return_value = instance

        bib_dir = project_tmp / ".litgraph" / "cache" / "bib"
        result = sync_zotero_library(
            bib_dir,
            user_id="12345",
            api_key="test-key",
            full_sync=True,
        )
    assert result["synced"] == 1
    assert (bib_dir / "zotero_live.json").exists()
