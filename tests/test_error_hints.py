"""v0.8 (I06): registry-based ID resolution, did_you_mean, and actionable hints."""

from __future__ import annotations

import json
from pathlib import Path

from litgraph.cli.config_manager import resolve_context
from litgraph.query.paper_finder import PaperFinder
from litgraph.utils.paper_identity import resolve_paper_id_from_registry
from litgraph.utils.paper_registry import save_registry
from tests.fixtures.extracted_fixtures import build_fixture_graph, write_fixtures


def _build_project(project_tmp: Path) -> PaperFinder:
    ctx = resolve_context(project_tmp)
    write_fixtures(ctx.extracted_cache_dir)
    build_fixture_graph(ctx)
    return PaperFinder(ctx.db_path, project_config=ctx.config)


def _write_registry(litgraph_dir: Path, source_path: str, paper_id: str) -> None:
    save_registry(litgraph_dir, {
        source_path: {"paper_id": paper_id, "content_hash": "", "assigned_at": ""},
    })


def test_registry_resolves_stem_filename_and_path(tmp_path: Path):
    litgraph_dir = tmp_path / ".litgraph"
    litgraph_dir.mkdir()
    _write_registry(litgraph_dir, "papers/mobility_gnn_2024.pdf", "p_uuid_1")

    assert resolve_paper_id_from_registry(litgraph_dir, "mobility_gnn_2024") == "p_uuid_1"
    assert resolve_paper_id_from_registry(litgraph_dir, "mobility_gnn_2024.pdf") == "p_uuid_1"
    assert resolve_paper_id_from_registry(litgraph_dir, "papers/mobility_gnn_2024.pdf") == "p_uuid_1"
    assert resolve_paper_id_from_registry(litgraph_dir, "papers\\mobility_gnn_2024.pdf") == "p_uuid_1"
    assert resolve_paper_id_from_registry(litgraph_dir, "unknown") is None
    assert resolve_paper_id_from_registry(litgraph_dir, "") is None


def test_finder_resolves_paper_id_via_registry(project_tmp: Path, monkeypatch):
    monkeypatch.chdir(project_tmp)
    finder = _build_project(project_tmp)
    # Registry maps a source file to the fixture paper id.
    _write_registry(
        project_tmp / ".litgraph",
        "papers/my_mobility_paper.pdf",
        "mobility_gnn_2024",
    )
    result = finder.summarize_paper("my_mobility_paper")
    assert result.get("paper_id") == "mobility_gnn_2024"
    finder.close()


def test_paper_not_found_includes_hint_and_did_you_mean(project_tmp: Path, monkeypatch):
    monkeypatch.chdir(project_tmp)
    finder = _build_project(project_tmp)
    result = finder.summarize_paper("mobility_gnn_224")  # typo
    assert "error" in result
    assert "search_papers" in result["hint"]
    assert any(
        d["paper_id"] == "mobility_gnn_2024" for d in result["did_you_mean"]
    )
    finder.close()


def test_paper_not_found_empty_db_hints_pipeline(project_tmp: Path, monkeypatch):
    monkeypatch.chdir(project_tmp)
    ctx = resolve_context(project_tmp)
    finder = PaperFinder(ctx.db_path, project_config=ctx.config)
    result = finder.summarize_paper("anything")
    assert "error" in result
    assert "litgraph scan" in result["hint"]
    finder.close()


def test_compare_papers_reports_missing_ids(project_tmp: Path, monkeypatch):
    monkeypatch.chdir(project_tmp)
    finder = _build_project(project_tmp)
    result = finder.compare_papers(["mobility_gnn_2024", "nonexistent_paper"])
    assert result["papers"]
    assert result["missing_ids"] == ["nonexistent_paper"]
    assert "search_papers" in result["hint"]
    finder.close()


def test_compare_papers_all_found_has_no_missing(project_tmp: Path, monkeypatch):
    monkeypatch.chdir(project_tmp)
    finder = _build_project(project_tmp)
    result = finder.compare_papers(["mobility_gnn_2024", "event_forecasting_2025"])
    assert "missing_ids" not in result
    assert "error" not in result
    finder.close()
