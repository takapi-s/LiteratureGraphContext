import json
import os
from unittest.mock import MagicMock, patch

from litgraph.mcp.server import MCPServer


def test_mcp_explore_paper_graph(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_fixture_graph(resolve_context(project_tmp))

    server = MCPServer(project_tmp)
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/list",
        "params": {},
    })
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "explore_paper_graph" in names
    assert "get_paper_neighbors" not in names
    assert "generate_related_work_outline" not in names

    call = server.handle_request({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "explore_paper_graph",
            "arguments": {"paper_id": "mobility_gnn_2024", "hops": 1},
        },
    })
    payload = json.loads(call["result"]["content"][0]["text"])
    assert "nodes" in payload


def test_mcp_deprecated_related_work_outline(project_tmp, monkeypatch):
    monkeypatch.chdir(project_tmp)
    from litgraph.cli.config_manager import init_project, resolve_context
    from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    build_fixture_graph(resolve_context(project_tmp))

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
    assert payload.get("deprecated") is True


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


def test_resolve_user_id_from_api_key():
    from litgraph.integrations.zotero import resolve_user_id_from_api_key

    with patch("litgraph.integrations.zotero.httpx.Client") as mock_client:
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"userID": 98765, "key": "abc", "access": {}}
        resp.raise_for_status = MagicMock()
        instance.get.return_value = resp
        mock_client.return_value = instance

        assert resolve_user_id_from_api_key("test-key") == "98765"
        instance.get.assert_called()
        assert "/keys/current" in instance.get.call_args[0][0]


def test_resolve_credentials_ignores_username_and_fetches_id(monkeypatch):
    from litgraph.integrations import zotero as zmod

    monkeypatch.setenv("ZOTERO_USER_ID", "takapi-s")
    monkeypatch.setenv("ZOTERO_API_KEY", "secret-key")
    monkeypatch.setattr(zmod, "resolve_user_id_from_api_key", lambda _key: "424242")
    monkeypatch.setattr(zmod, "persist_zotero_user_id", lambda uid: None)

    uid, key = zmod._resolve_zotero_credentials()
    assert uid == "424242"
    assert key == "secret-key"
    assert os.environ["ZOTERO_USER_ID"] == "424242"


def test_resolve_credentials_key_only(monkeypatch):
    from litgraph.integrations import zotero as zmod

    monkeypatch.delenv("ZOTERO_USER_ID", raising=False)
    monkeypatch.setenv("ZOTERO_API_KEY", "secret-key")
    monkeypatch.setattr(zmod, "resolve_user_id_from_api_key", lambda _key: "111")

    uid, key = zmod._resolve_zotero_credentials()
    assert uid == "111"
    assert key == "secret-key"


def test_sync_zotero_with_pdfs_prints_progress(project_tmp, monkeypatch):
    from litgraph.cli.config_manager import init_project, resolve_context
    from litgraph.integrations import zotero as zmod

    init_project(project_tmp, papers_dir=str(project_tmp / "papers"))
    ctx = resolve_context(project_tmp)
    ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)
    (ctx.bib_cache_dir / "zotero_live.json").write_text(
        json.dumps([
            {
                "bib_key": "ABC",
                "zotero_key": "ABC",
                "title": "Progress Visible Paper",
                "doi": "10.1/test",
            }
        ]),
        encoding="utf-8",
    )

    logs: list[str] = []

    class _FakeConsole:
        def print(self, message: str) -> None:
            logs.append(str(message))

    class _Result:
        paper_id = "p_test"
        source_path = ".litgraph/ingest/default/zotero_ABC.pdf"
        errors: list = []
        skipped_extract = False

    class _Ctx:
        def ingest_from_bytes(self, *a, **k):
            assert k.get("show_progress") is True
            return _Result()

    monkeypatch.setattr(zmod, "_resolve_zotero_credentials", lambda **k: ("1", "key"))
    monkeypatch.setattr(
        zmod,
        "sync_zotero_library",
        lambda *a, **k: {"synced": 1, "last_version": 1},
    )
    monkeypatch.setattr(zmod, "fetch_pdf_for_item", lambda *a, **k: b"%PDF-1.4 fake")
    monkeypatch.setattr("rich.console.Console", lambda **k: _FakeConsole())
    monkeypatch.setattr("litgraph.context.LitgraphContext", lambda **k: _Ctx())
    monkeypatch.setattr(
        "litgraph.ingest.dedup.register_paper_identity",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "litgraph.cli.helpers.build_paper_graph",
        lambda *a, **k: {"papers_indexed": 1, "nodes": 1, "edges": 0},
    )

    result = zmod.sync_zotero_with_pdfs(ctx, build=True, show_progress=True)
    assert result["pdfs_ingested"] == 1
    joined = "\n".join(logs)
    assert "Fetching Zotero library" in joined
    assert "[1/1]" in joined
    assert "download PDF" in joined
    assert "Building graph" in joined


def test_resolve_remote_ingest_source_ref_arxiv_html() -> None:
    from litgraph.integrations.zotero import resolve_remote_ingest_source_ref

    entry = {
        "entry_type": "webpage",
        "url": "https://arxiv.org/html/2501.13956",
    }
    assert resolve_remote_ingest_source_ref(entry) == "arxiv://2501.13956"


def test_resolve_remote_ingest_source_ref_pdf_url() -> None:
    from litgraph.integrations.zotero import resolve_remote_ingest_source_ref

    entry = {
        "entry_type": "webpage",
        "url": "https://example.com/papers/demo.pdf",
    }
    assert resolve_remote_ingest_source_ref(entry) == "https://example.com/papers/demo.pdf"


def test_resolve_remote_ingest_source_ref_unsupported_webpage() -> None:
    from litgraph.integrations.zotero import resolve_remote_ingest_source_ref

    entry = {
        "entry_type": "webpage",
        "url": "https://example.com/blog/post",
    }
    assert resolve_remote_ingest_source_ref(entry) is None


def test_sync_zotero_with_pdfs_webpage_fallback(project_tmp, monkeypatch):
    from litgraph.cli.config_manager import init_project, resolve_context
    from litgraph.integrations import zotero as zmod

    init_project(project_tmp, papers_dir=str(project_tmp / "papers"))
    ctx = resolve_context(project_tmp)
    ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)
    (ctx.bib_cache_dir / "zotero_live.json").write_text(
        json.dumps([
            {
                "bib_key": "WEB1",
                "zotero_key": "WEB1",
                "entry_type": "webpage",
                "title": "Zep Paper",
                "url": "https://arxiv.org/html/2501.13956",
            }
        ]),
        encoding="utf-8",
    )

    class _Result:
        paper_id = "p_zep"
        source_path = ".litgraph/ingest/default/zotero_WEB1.pdf"
        errors: list = []
        skipped_extract = False

    class _Ctx:
        def ingest_from_bytes(self, *a, **k):
            return _Result()

    monkeypatch.setattr(zmod, "_resolve_zotero_credentials", lambda **k: ("1", "key"))
    monkeypatch.setattr(
        zmod,
        "sync_zotero_library",
        lambda *a, **k: {"synced": 1, "last_version": 1},
    )
    monkeypatch.setattr(zmod, "fetch_pdf_for_item", lambda *a, **k: None)
    monkeypatch.setattr(
        "litgraph.ingest.registry.resolve_ingest_payload",
        lambda ref: type("Payload", (), {"data": b"%PDF-1.4 zep", "filename": "2501.13956.pdf"})(),
    )
    monkeypatch.setattr("litgraph.context.LitgraphContext", lambda **k: _Ctx())
    monkeypatch.setattr(
        "litgraph.ingest.dedup.register_paper_identity",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "litgraph.cli.helpers.build_paper_graph",
        lambda *a, **k: {"papers_indexed": 1, "nodes": 1, "edges": 0},
    )

    result = zmod.sync_zotero_with_pdfs(ctx, build=True, show_progress=False)
    assert result["pdfs_ingested"] == 1
    assert result["pdfs_skipped"] == 0

