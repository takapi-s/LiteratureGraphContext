"""Tests for MCP watch process manager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from litgraph.cli.config_manager import init_project
from litgraph.mcp.watch_manager import WatchProcessManager


class _FakeProc:
    def __init__(self, pid: int = 1234) -> None:
        self.pid = pid
        self._alive = True

    def poll(self):
        return None if self._alive else 0

    def send_signal(self, _sig) -> None:
        self._alive = False

    def wait(self, timeout=None) -> int:
        self._alive = False
        return 0

    def kill(self) -> None:
        self._alive = False


@pytest.fixture
def manager() -> WatchProcessManager:
    return WatchProcessManager()


def test_start_tracks_multiple_projects_independently(manager: WatchProcessManager, tmp_path: Path) -> None:
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    init_project(project_a, papers_dir="papers")
    init_project(project_b, papers_dir="papers")
    (project_a / "papers").mkdir(parents=True, exist_ok=True)
    (project_b / "papers").mkdir(parents=True, exist_ok=True)

    proc_a = _FakeProc(pid=1001)
    proc_b = _FakeProc(pid=1002)

    with patch("litgraph.mcp.watch_manager.subprocess.Popen", side_effect=[proc_a, proc_b]) as popen:
        result_a = manager.start(project_a)
        result_b = manager.start(project_b)

    assert result_a["status"] == "started"
    assert result_a["running"] is True
    assert result_a["project_root"] == str(project_a.resolve())
    assert result_b["status"] == "started"
    assert result_b["running"] is True
    assert result_b["project_root"] == str(project_b.resolve())
    assert popen.call_count == 2

    status_a = manager.status(project_a)
    status_b = manager.status(project_b)
    assert status_a["pid"] == 1001
    assert status_b["pid"] == 1002


def test_start_same_project_twice_returns_already_running(manager: WatchProcessManager, tmp_path: Path) -> None:
    project = tmp_path / "project"
    init_project(project, papers_dir="papers")
    (project / "papers").mkdir(parents=True, exist_ok=True)
    proc = _FakeProc(pid=2001)

    with patch("litgraph.mcp.watch_manager.subprocess.Popen", return_value=proc) as popen:
        first = manager.start(project)
        second = manager.start(project)

    assert first["status"] == "started"
    assert second["status"] == "already_running"
    assert popen.call_count == 1


def test_stop_scoped_to_project_leaves_other_watches_running(
    manager: WatchProcessManager, tmp_path: Path
) -> None:
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    init_project(project_a, papers_dir="papers")
    init_project(project_b, papers_dir="papers")
    (project_a / "papers").mkdir(parents=True, exist_ok=True)
    (project_b / "papers").mkdir(parents=True, exist_ok=True)

    proc_a = _FakeProc(pid=3001)
    proc_b = _FakeProc(pid=3002)

    with patch("litgraph.mcp.watch_manager.subprocess.Popen", side_effect=[proc_a, proc_b]):
        manager.start(project_a)
        manager.start(project_b)

    stopped = manager.stop(project_a)
    assert stopped["status"] == "stopped"
    assert manager.status(project_a)["running"] is False
    assert manager.status(project_b)["running"] is True


def test_status_without_project_lists_all_watches(manager: WatchProcessManager, tmp_path: Path) -> None:
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    init_project(project_a, papers_dir="papers")
    init_project(project_b, papers_dir="papers")
    (project_a / "papers").mkdir(parents=True, exist_ok=True)
    (project_b / "papers").mkdir(parents=True, exist_ok=True)

    with patch("litgraph.mcp.watch_manager.subprocess.Popen", side_effect=[_FakeProc(4001), _FakeProc(4002)]):
        manager.start(project_a)
        manager.start(project_b)

    status = manager.status()
    assert status["running"] is True
    assert len(status["watches"]) == 2
