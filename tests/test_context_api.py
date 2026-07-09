"""Tests for LitgraphContext programmatic API."""

from __future__ import annotations

from pathlib import Path

import pytest

from litgraph.cli.config_manager import init_project
from litgraph.context import LitgraphContext


@pytest.fixture
def api_project(tmp_path: Path) -> Path:
    init_project(tmp_path, papers_dir="papers")
    (tmp_path / "papers").mkdir()
    return tmp_path


def test_litgraph_context_resolves_project(api_project: Path) -> None:
    ctx = LitgraphContext(project_root=api_project, load_env_files=False)
    assert ctx.project_root == api_project.resolve()
    assert ctx.workspace_id == "default"
    assert ctx.litgraph_dir.is_dir()


def test_ingest_from_path_pdf(api_project: Path) -> None:
    fixture = Path(__file__).resolve().parents[1] / "examples" / "papers" / "event_forecasting_2025.pdf"
    if not fixture.exists():
        pytest.skip("example PDF missing")
    dest = api_project / "papers" / "event_forecasting_2025.pdf"
    dest.write_bytes(fixture.read_bytes())
    ctx = LitgraphContext(project_root=api_project, load_env_files=False)
    result = ctx.ingest_from_path(dest, extract=False, build=False)
    assert result.parsed is True
    assert result.paper_id.startswith("p_")


def test_ingest_from_bytes(api_project: Path) -> None:
    data = b"%PDF-1.4 minimal"
    ctx = LitgraphContext(project_root=api_project, load_env_files=False)
    with pytest.raises(Exception):
        # Invalid PDF should fail parse gracefully or skip extract
        ctx.ingest_from_bytes(data, filename="bad.pdf", extract=False, build=False)


def test_workspace_id_reserved(api_project: Path) -> None:
    ctx = LitgraphContext(project_root=api_project, workspace_id="lab-a", load_env_files=False)
    assert ctx.workspace_id == "lab-a"
    assert "lab-a" in str(ctx.ctx.cache_dir)


def test_litgraph_context_custom_cache_dir_creates_subdirs(
    api_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(api_project)
    custom_cache = tmp_path / "custom_cache"
    ctx = LitgraphContext(project_root=None, load_env_files=False, cache_dir=custom_cache)
    assert (custom_cache / "parsed").is_dir()
    assert (custom_cache / "extracted").is_dir()
    assert (custom_cache / "bib").is_dir()
    assert ctx.ctx.cache_dir == custom_cache.resolve()
