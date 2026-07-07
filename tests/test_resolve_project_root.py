"""Tests for project root resolution (LITGRAPH_PROJECT_ROOT, parent walk)."""

from pathlib import Path

import pytest

from litgraph.cli.config_manager import init_project, resolve_context, resolve_project_root


def test_resolve_project_root_from_env(project_tmp: Path, monkeypatch):
    subdir = project_tmp / "subdir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    init_project(project_tmp)
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(project_tmp))

    root = resolve_project_root()
    assert root == project_tmp.resolve()


def test_resolve_project_root_walks_up_to_litgraph(project_tmp: Path, monkeypatch):
    monkeypatch.delenv("LITGRAPH_PROJECT_ROOT", raising=False)
    init_project(project_tmp)
    subdir = project_tmp / "docs" / "nested"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    root = resolve_project_root()
    assert root == project_tmp.resolve()


def test_resolve_project_root_explicit_cwd_overrides_env(project_tmp: Path, monkeypatch, tmp_path: Path):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(other))

    root = resolve_project_root(project_tmp)
    assert root == project_tmp.resolve()


def test_resolve_context_uses_env_for_mcp_like_startup(project_tmp: Path, monkeypatch):
    init_project(project_tmp)
    monkeypatch.chdir(Path.home())
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(project_tmp))

    ctx = resolve_context()
    assert ctx.project_root == project_tmp.resolve()
    assert ctx.litgraph_dir == project_tmp / ".litgraph"
