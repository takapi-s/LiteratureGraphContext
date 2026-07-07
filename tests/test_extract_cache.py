"""Tests for extract cache skip behavior."""

from __future__ import annotations

import json
import os
import time

from litgraph.cli.config_manager import resolve_context
from litgraph.cli.helpers import extract_paper_ids, extract_papers
from tests.fixtures.extracted_fixtures import FIXTURES


def _write_parsed(ctx, paper_id: str, sections: int = 2) -> None:
    doc = {
        "paper_id": paper_id,
        "sections": [{"name": f"Section {i}", "text": "content"} for i in range(sections)],
    }
    path = ctx.parsed_cache_dir / f"{paper_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _write_extracted(ctx, paper_id: str) -> None:
    path = ctx.extracted_cache_dir / f"{paper_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(FIXTURES[0]), encoding="utf-8")


def test_extract_skips_already_extracted(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    _write_parsed(ctx, "paper_a")
    _write_parsed(ctx, "paper_b")
    _write_extracted(ctx, "paper_a")

    calls: list[str] = []

    def fake_extract(doc, provider_name, model=None):
        calls.append(doc["paper_id"])
        return {"paper_id": doc["paper_id"], "title": doc["paper_id"]}

    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = extract_papers(ctx, skip_confirm=True)

    assert result["extracted"] == 1
    assert result["skipped"] == 1
    assert result["paper_ids"] == ["paper_b"]
    assert calls == ["paper_b"]


def test_extract_force_reextracts_all(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    _write_parsed(ctx, "paper_a")
    _write_parsed(ctx, "paper_b")
    _write_extracted(ctx, "paper_a")
    _write_extracted(ctx, "paper_b")

    calls: list[str] = []

    def fake_extract(doc, provider_name, model=None):
        calls.append(doc["paper_id"])
        return {"paper_id": doc["paper_id"], "title": doc["paper_id"]}

    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = extract_papers(ctx, skip_confirm=True, force=True)

    assert result["extracted"] == 2
    assert result["skipped"] == 0
    assert set(calls) == {"paper_a", "paper_b"}


def test_extract_reextracts_when_parsed_is_newer(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    _write_extracted(ctx, "paper_a")
    _write_parsed(ctx, "paper_a")
    parsed_path = ctx.parsed_cache_dir / "paper_a.json"
    extracted_path = ctx.extracted_cache_dir / "paper_a.json"
    old = time.time() - 60
    os.utime(extracted_path, (old, old))
    os.utime(parsed_path, (time.time(), time.time()))

    calls: list[str] = []

    def fake_extract(doc, provider_name, model=None):
        calls.append(doc["paper_id"])
        return {"paper_id": doc["paper_id"], "title": doc["paper_id"]}

    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = extract_papers(ctx, skip_confirm=True)

    assert result["extracted"] == 1
    assert result["skipped"] == 0
    assert calls == ["paper_a"]


def test_extract_paper_ids_skips_cached(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    _write_parsed(ctx, "paper_a")
    _write_parsed(ctx, "paper_b")
    _write_extracted(ctx, "paper_a")

    calls: list[str] = []

    def fake_extract(doc, provider_name, model=None):
        calls.append(doc["paper_id"])
        return {"paper_id": doc["paper_id"], "title": doc["paper_id"]}

    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = extract_paper_ids(ctx, ["paper_a", "paper_b"], skip_confirm=True)

    assert result["extracted"] == 1
    assert result["skipped"] == 1
    assert calls == ["paper_b"]


def test_extract_continues_after_failure_and_retries(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    _write_parsed(ctx, "paper_a")
    _write_parsed(ctx, "paper_b")
    _write_parsed(ctx, "paper_c")

    calls: dict[str, int] = {}

    def fake_extract(doc, provider_name, model=None):
        paper_id = doc["paper_id"]
        calls[paper_id] = calls.get(paper_id, 0) + 1
        if paper_id == "paper_b":
            raise ValueError("validation failed")
        return {"paper_id": paper_id, "title": paper_id}

    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = extract_papers(ctx, skip_confirm=True)

    assert result["extracted"] == 2
    assert result["paper_ids"] == ["paper_a", "paper_c"]
    assert len(result["failed"]) == 1
    assert result["failed"][0]["paper_id"] == "paper_b"
    assert calls["paper_b"] == 3
    assert calls["paper_a"] == 1
    assert calls["paper_c"] == 1
