"""Tests for papers directory watching."""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from litgraph.cli.config_manager import resolve_context, save_papers_dir
from litgraph.cli.helpers import process_watch_changes, sync_papers_directory
from litgraph.core.watcher import PapersEventHandler, WatchOptions
from litgraph.graph.graph_builder import build_graph
from litgraph.query.paper_finder import PaperFinder
from litgraph.scanner.hash_cache import load_cache, scan_and_update
from litgraph.scanner.file_scanner import discover_papers
from litgraph.scanner.ignore import build_ignore_spec, should_ignore
from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _use_papers_dir(ctx, project_tmp):
    save_papers_dir(ctx, project_tmp / "papers")
    return project_tmp / "papers"


def test_should_ignore_litgraph_dir(project_tmp):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    ignore_spec, _ = build_ignore_spec(papers)
    litgraph_file = project_tmp / ".litgraph" / "config.yaml"
    assert should_ignore(litgraph_file, papers, ignore_spec)


def test_find_removed_files(project_tmp):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    md = papers / "gone.md"
    shutil.copy(FIXTURES_DIR / "sample_note.md", md)
    files = discover_papers(papers)
    scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    md.unlink()

    from litgraph.scanner.hash_cache import find_removed_files

    removed = find_removed_files(discover_papers(papers), ctx.files_cache_path, ctx.project_root)
    assert len(removed) == 1
    assert removed[0].name == "gone.md"
    assert "papers/gone.md" not in load_cache(ctx.files_cache_path)


def test_process_watch_parse_without_extract(project_tmp):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    md = papers / "new_paper.md"
    shutil.copy(FIXTURES_DIR / "sample_note.md", md)

    result = process_watch_changes(
        ctx,
        changed_paths=[md.resolve()],
        deleted_paths=[],
        auto_extract=False,
        auto_build=True,
    )

    assert result["parsed"] == 1
    assert result["paper_ids"] == ["new_paper"]
    assert result["pending_extract"] == ["new_paper"]
    assert (ctx.parsed_cache_dir / "new_paper.json").exists()
    assert not (ctx.extracted_cache_dir / "new_paper.json").exists()


def test_process_watch_delete_paper(project_tmp):
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    build_graph(ctx, FIXTURES)

    md = papers / "mobility_gnn_2024.md"
    shutil.copy(FIXTURES_DIR / "sample_note.md", md)
    scan_and_update(discover_papers(papers), ctx.files_cache_path, ctx.project_root)

    finder = PaperFinder(ctx.db_path)
    assert finder.get_paper("mobility_gnn_2024") is not None
    finder.store.close()

    result = process_watch_changes(
        ctx,
        changed_paths=[],
        deleted_paths=[md.resolve()],
        auto_build=False,
    )

    assert "mobility_gnn_2024" in result["removed_paper_ids"]
    assert not (ctx.parsed_cache_dir / "mobility_gnn_2024.json").exists()
    assert not (ctx.extracted_cache_dir / "mobility_gnn_2024.json").exists()

    finder2 = PaperFinder(ctx.db_path)
    assert finder2.get_paper("mobility_gnn_2024") is None
    finder2.store.close()


def test_watch_queues_changes_until_processing_finishes(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    ignore_spec, _ = build_ignore_spec(papers)
    handler = PapersEventHandler(ctx, WatchOptions(), papers, ignore_spec)

    batches: list[list[str]] = []
    first_batch_started = threading.Event()
    release_first_batch = threading.Event()

    def slow_process(_ctx, changed_paths, deleted_paths, **kwargs):
        batches.append([path.name for path in changed_paths])
        if len(batches) == 1:
            first_batch_started.set()
            assert release_first_batch.wait(timeout=5)
        return {
            "parsed": len(changed_paths),
            "paper_ids": [],
            "extracted": 0,
            "extract_skipped": 0,
            "pending_extract": [],
            "bib_updated": False,
            "removed_paper_ids": [],
            "papers_indexed": 0,
        }

    monkeypatch.setattr("litgraph.cli.helpers.process_watch_changes", slow_process)
    handler.start_worker()

    file_a = papers / "queued_a.md"
    file_b = papers / "queued_b.md"
    handler._queue(file_a.resolve(), deleted=False)
    assert first_batch_started.wait(timeout=5)

    handler._queue(file_b.resolve(), deleted=False)
    release_first_batch.set()

    deadline = time.time() + 5
    while len(batches) < 2 and time.time() < deadline:
        time.sleep(0.05)

    handler.stop_worker()
    assert batches[0] == ["queued_a.md"]
    assert batches[1] == ["queued_b.md"]


def test_process_watch_auto_extract_skips_confirm(project_tmp, monkeypatch):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    md = papers / "new_paper.md"
    shutil.copy(FIXTURES_DIR / "sample_note.md", md)

    confirm_calls: list[bool] = []

    def fake_confirm(_ctx, _provider, _sections, skip):
        confirm_calls.append(skip)
        return True

    def fake_extract(doc, provider_name, model=None):
        return {"paper_id": doc["paper_id"], "title": doc["paper_id"]}

    monkeypatch.setattr("litgraph.cli.helpers._confirm_external_api", fake_confirm)
    monkeypatch.setattr("litgraph.cli.helpers.extract_paper", fake_extract)
    monkeypatch.setattr("litgraph.cli.helpers.save_extraction", lambda path, extraction: None)

    result = process_watch_changes(
        ctx,
        changed_paths=[md.resolve()],
        deleted_paths=[],
        auto_extract=True,
        auto_build=False,
        skip_confirm=False,
    )

    assert result["extracted"] == 1
    assert confirm_calls == [True]


def test_sync_on_start_detects_new_file(project_tmp):
    ctx = resolve_context(project_tmp)
    papers = _use_papers_dir(ctx, project_tmp)
    md = papers / "sync_test.md"
    shutil.copy(FIXTURES_DIR / "sample_note.md", md)
    md = md.rename(papers / "sync_test.md")

    result = sync_papers_directory(ctx, auto_extract=False, auto_build=False)

    assert result["parsed"] == 1
    assert result["paper_ids"] == ["sync_test"]


def test_delete_paper_kuzu_store(project_tmp):
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    build_graph(ctx, FIXTURES)

    from litgraph.graph.kuzu_store import KuzuGraphStore

    store = KuzuGraphStore(ctx.db_path)
    store.delete_paper("mobility_gnn_2024")
    store.close()

    finder = PaperFinder(ctx.db_path)
    assert finder.get_paper("mobility_gnn_2024") is None
    gnn = finder.find_papers_by_method("GNN")
    assert not any(p.get("paper_id") == "mobility_gnn_2024" for p in gnn)
