"""Tests for project root resolution (LITGRAPH_PROJECT_ROOT, parent walk)."""

from pathlib import Path

import pytest

from litgraph.cli import config_manager
from litgraph.cli.config_manager import (
    ProjectNotFoundError,
    init_project,
    resolve_context,
    resolve_project_root,
)
from litgraph.mcp.tool_service import MCPToolService


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


def test_home_litgraph_is_not_used_as_project(isolated_home: Path, monkeypatch):
    """~/.litgraph exists but must not be treated as a project during walk-up."""
    monkeypatch.delenv("LITGRAPH_PROJECT_ROOT", raising=False)
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    global_dir = isolated_home / ".litgraph"
    global_dir.mkdir(parents=True)
    (global_dir / "config.yaml").write_text("papers_dir: papers\n", encoding="utf-8")
    (global_dir / "graph.json").write_text("{}", encoding="utf-8")

    work = isolated_home / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    with pytest.raises(ProjectNotFoundError):
        resolve_project_root()


def test_no_project_raises_project_not_found(isolated_home: Path, monkeypatch):
    monkeypatch.delenv("LITGRAPH_PROJECT_ROOT", raising=False)
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    work = isolated_home / "empty"
    work.mkdir()
    monkeypatch.chdir(work)

    with pytest.raises(ProjectNotFoundError):
        resolve_project_root()


def test_env_root_without_config_raises(isolated_home: Path, monkeypatch):
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    uninit = isolated_home / "uninit"
    uninit.mkdir()
    monkeypatch.chdir(uninit)
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(uninit))

    with pytest.raises(ProjectNotFoundError) as exc_info:
        resolve_project_root()
    assert str(uninit) in str(exc_info.value)


def test_mcp_degrades_when_env_root_uninitialized(isolated_home: Path, monkeypatch):
    """Server must not crash at startup; tool calls return error + hint instead."""
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    uninit = isolated_home / "uninit"
    uninit.mkdir()
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(uninit))

    service = MCPToolService(cwd=uninit)
    assert service.finder is None
    result = service.handle_tool_call("list_papers", {})
    assert "error" in result
    assert "litgraph init" in result["hint"]
    service.close()


def test_mcp_watch_status_without_project(isolated_home: Path, monkeypatch):
    """watch status/stop must work even when project context init failed."""
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    uninit = isolated_home / "uninit"
    uninit.mkdir()
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(uninit))

    service = MCPToolService(cwd=uninit)
    result = service.handle_tool_call("watch_papers_directory", {"action": "status"})
    assert "running" in result
    assert "error" not in result
    service.close()


def test_mcp_watch_start_without_project_returns_error(isolated_home: Path, monkeypatch):
    """watch start must not raise AttributeError when ctx is None."""
    monkeypatch.setattr(config_manager, "GLOBAL_CONFIG_DIR", isolated_home / ".litgraph")
    uninit = isolated_home / "uninit"
    uninit.mkdir()
    monkeypatch.setenv("LITGRAPH_PROJECT_ROOT", str(uninit))

    service = MCPToolService(cwd=uninit)
    assert service.ctx is None
    result = service.handle_tool_call("watch_papers_directory", {"action": "start"})
    assert "error" in result
    assert "litgraph init" in result["hint"]
    service.close()


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ctx_helper_calls_resolve_context_not_itself(project_tmp: Path):
    """Regression: _ctx() must not recurse into itself."""
    from unittest.mock import MagicMock, patch

    from litgraph.cli import config_manager as cm
    from litgraph.cli.main import _ctx

    fake = MagicMock()
    fake.project_root = project_tmp.resolve()
    fake.config = {"papers_dir": "papers"}

    with patch.object(cm, "resolve_context", return_value=fake) as mock_resolve:
        ctx = _ctx(quiet=True)

    mock_resolve.assert_called_once_with(workspace_id=None)
    assert ctx.project_root == project_tmp.resolve()
