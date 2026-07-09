"""Tests for the visualization server graph loader."""

from __future__ import annotations

import json

import pytest

from litgraph.cli.config_manager import resolve_context
from litgraph.viz.server import _graph_payload
from tests.fixtures.extracted_fixtures import build_fixture_graph


def test_graph_payload_falls_back_to_graph_json_on_kuzu_lock(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)

    snapshot = {
        "nodes": [{"type": "Paper", "id": "snapshot_paper", "title": "Snapshot"}],
        "edges": [],
    }
    graph_path = ctx.cache_dir / "graph.json"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(json.dumps(snapshot), encoding="utf-8")

    class LockedStore:
        def export_graph_json(self):
            raise RuntimeError(
                "IO exception: Could not set lock on file : "
                f"{ctx.db_path} See the docs: https://docs.kuzudb.com/concurrency"
            )

        def close(self):
            return None

    monkeypatch.setattr("litgraph.viz.server._store_for", lambda *_args, **_kwargs: LockedStore())

    payload = _graph_payload(ctx)
    assert payload["nodes"][0]["id"] == "snapshot_paper"


def test_graph_payload_raises_when_locked_and_no_snapshot(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)

    class LockedStore:
        def export_graph_json(self):
            raise RuntimeError("IO exception: Could not set lock on file")

        def close(self):
            return None

    monkeypatch.setattr("litgraph.viz.server._store_for", lambda *_args, **_kwargs: LockedStore())

    with pytest.raises(FileNotFoundError, match="graph snapshot"):
        _graph_payload(ctx)
