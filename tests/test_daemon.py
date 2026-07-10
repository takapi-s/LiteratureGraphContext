"""Tests for daemon settings and incremental Zotero sync."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from litgraph.daemon.runtime import DaemonRuntime
from litgraph.daemon.server import create_daemon_app
from litgraph.daemon.state import DaemonSettings, load_daemon_settings, save_daemon_settings
from litgraph.integrations.zotero import (
    get_ingested_versions,
    record_ingested_version,
    should_skip_ingested_item,
    sync_zotero_with_pdfs,
)


def test_should_skip_ingested_item_when_version_matches():
    entry = {"zotero_key": "ABC", "zotero_version": 42}
    ingested = {"ABC": 42}
    assert should_skip_ingested_item("ABC", entry, ingested) is True
    assert should_skip_ingested_item("ABC", entry, {"ABC": 41}) is False


def test_record_ingested_version_persists(project_tmp):
    from litgraph.cli.config_manager import resolve_context

    ctx = resolve_context(project_tmp)
    bib_dir = ctx.bib_cache_dir
    bib_dir.mkdir(parents=True, exist_ok=True)
    entry = {"zotero_key": "ITEM1", "zotero_version": 7}
    record_ingested_version(bib_dir, "ITEM1", entry)
    assert get_ingested_versions(bib_dir)["ITEM1"] == 7


def test_daemon_settings_roundtrip(project_tmp):
    from litgraph.cli.config_manager import resolve_context

    ctx = resolve_context(project_tmp)
    settings = DaemonSettings(
        extract_mode="manual",
        zotero_interval_sec=1200,
        zotero_enabled=True,
    )
    save_daemon_settings(ctx, settings)
    loaded = load_daemon_settings(resolve_context(project_tmp))
    assert loaded.extract_mode == "manual"
    assert loaded.zotero_interval_sec == 1200
    assert loaded.zotero_enabled is True


def test_sync_zotero_with_pdfs_skips_unchanged_versions(project_tmp):
    from litgraph.cli.config_manager import resolve_context

    ctx = resolve_context(project_tmp)
    bib_dir = ctx.bib_cache_dir
    bib_dir.mkdir(parents=True, exist_ok=True)
    (bib_dir / "zotero_live.json").write_text(
        json.dumps(
            [
                {
                    "bib_key": "ABC",
                    "zotero_key": "ABC",
                    "title": "Cached",
                    "zotero_version": 10,
                }
            ]
        ),
        encoding="utf-8",
    )
    record_ingested_version(bib_dir, "ABC", {"zotero_version": 10})

    with patch("litgraph.integrations.zotero._resolve_zotero_credentials", return_value=("1", "key")):
        with patch("litgraph.integrations.zotero.sync_zotero_library") as mock_bib:
            mock_bib.return_value = {"synced": 1, "last_version": 10}
            with patch("litgraph.integrations.zotero.fetch_pdf_for_item") as mock_pdf:
                result = sync_zotero_with_pdfs(
                    ctx,
                    changed_only=True,
                    extract=False,
                    build=False,
                    show_progress=False,
                )

    assert result["pdfs_version_skipped"] == 1
    assert result["pdfs_ingested"] == 0
    mock_pdf.assert_not_called()


def test_manual_extract_mode_scheduler_uses_extract_flag(project_tmp):
    from litgraph.cli.config_manager import resolve_context

    ctx = resolve_context(project_tmp)
    runtime = DaemonRuntime(ctx)
    runtime.settings.extract_mode = "manual"

    with patch("litgraph.integrations.zotero.sync_zotero_with_pdfs") as mock_sync:
        mock_sync.return_value = {"pdfs_ingested": 0, "pdf_errors": []}
        runtime.scheduler._run_zotero_sync()
        mock_sync.assert_called_once()
        assert mock_sync.call_args.kwargs["extract"] is False


def test_daemon_settings_and_extract_api(project_tmp, monkeypatch):
    from litgraph.cli.config_manager import resolve_context

    ctx = resolve_context(project_tmp)
    runtime = DaemonRuntime(ctx)

    @asynccontextmanager
    async def _noop_mcp_lifespan(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr("litgraph.daemon.server.mcp_http_lifespan", _noop_mcp_lifespan)
    monkeypatch.setattr("litgraph.daemon.server.register_mcp_http_route", lambda *_a, **_k: None)
    monkeypatch.setattr("litgraph.daemon.server.list_pending_extract", lambda _ctx: ["p_pending"])
    monkeypatch.setattr(runtime.scheduler, "start", lambda: None)
    monkeypatch.setattr(runtime, "start_folder_watch", lambda: None)
    runtime.shutdown = lambda: None

    app = create_daemon_app(runtime)
    with TestClient(app) as client:
        res = client.get("/api/daemon/settings")
        assert res.status_code == 200
        assert res.json()["extract_mode"] == "manual"

        res = client.put(
            "/api/daemon/settings",
            json={"extract_mode": "auto", "zotero_interval_sec": 900},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["extract_mode"] == "auto"
        assert body["zotero_interval_sec"] == 900

        res = client.get("/api/daemon/status")
        assert res.status_code == 200
        assert "p_pending" in res.json()["pending_extract"]

        with patch.object(runtime.scheduler, "trigger_extract", return_value={"extracted": 1}) as mock_extract:
            res = client.post("/api/daemon/extract", json={})
            assert res.status_code == 200
            assert res.json()["extracted"] == 1
            mock_extract.assert_called_once()
