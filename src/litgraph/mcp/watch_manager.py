"""MCP folder-watch subprocess manager."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class _WatchEntry:
    proc: subprocess.Popen
    papers_dir: str
    project_root: str


class WatchProcessManager:
    """Manage background ``litgraph watch`` subprocesses keyed by project root."""

    def __init__(self) -> None:
        self._watches: Dict[str, _WatchEntry] = {}

    @staticmethod
    def _project_key(project_root: Path) -> str:
        return str(project_root.resolve())

    def _prune_dead(self, key: str) -> None:
        entry = self._watches.get(key)
        if entry is not None and entry.proc.poll() is not None:
            del self._watches[key]

    def _prune_all_dead(self) -> None:
        for key in list(self._watches):
            self._prune_dead(key)

    def _entry_status(self, entry: _WatchEntry) -> Dict[str, Any]:
        running = entry.proc.poll() is None
        return {
            "running": running,
            "pid": entry.proc.pid if running else None,
            "papers_dir": entry.papers_dir,
            "project_root": entry.project_root,
        }

    def status(self, project_root: Optional[Path] = None) -> Dict[str, Any]:
        self._prune_all_dead()
        if project_root is not None:
            key = self._project_key(project_root)
            entry = self._watches.get(key)
            if entry is None:
                return {
                    "running": False,
                    "pid": None,
                    "papers_dir": None,
                    "project_root": key,
                }
            return self._entry_status(entry)

        watches = [self._entry_status(entry) for entry in self._watches.values()]
        return {
            "running": any(item["running"] for item in watches),
            "watches": watches,
        }

    def start(self, project_root: Path, papers_dir: Optional[Path] = None) -> Dict[str, Any]:
        key = self._project_key(project_root)
        self._prune_dead(key)
        target = (papers_dir or project_root / "papers").resolve()
        entry = self._watches.get(key)
        if entry is not None and entry.proc.poll() is None:
            if entry.papers_dir == str(target):
                return {"status": "already_running", **self.status(project_root)}
            self.stop(project_root)

        env = os.environ.copy()
        env["LITGRAPH_PROJECT_ROOT"] = key
        cmd = [
            sys.executable,
            "-m",
            "litgraph",
            "watch",
            str(target),
            "--sync-on-start",
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=key,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._watches[key] = _WatchEntry(
            proc=proc,
            papers_dir=str(target),
            project_root=key,
        )
        return {"status": "started", **self.status(project_root)}

    def stop(self, project_root: Optional[Path] = None) -> Dict[str, Any]:
        self._prune_all_dead()
        if project_root is not None:
            return self._stop_one(self._project_key(project_root))

        if not self._watches:
            return {"status": "not_running", "running": False, "stopped": 0}

        stopped = 0
        pids: list[int] = []
        for key in list(self._watches):
            result = self._stop_one(key)
            if result.get("status") == "stopped":
                stopped += 1
                if result.get("pid") is not None:
                    pids.append(int(result["pid"]))
        return {
            "status": "stopped" if stopped else "not_running",
            "running": False,
            "stopped": stopped,
            "pids": pids,
        }

    def _stop_one(self, key: str) -> Dict[str, Any]:
        entry = self._watches.get(key)
        if entry is None or entry.proc.poll() is not None:
            self._watches.pop(key, None)
            return {"status": "not_running", "running": False, "project_root": key}
        pid = entry.proc.pid
        try:
            entry.proc.send_signal(signal.SIGTERM)
            entry.proc.wait(timeout=10)
        except Exception:
            try:
                entry.proc.kill()
                entry.proc.wait(timeout=5)
            except Exception:
                pass
        finally:
            self._watches.pop(key, None)
        return {"status": "stopped", "pid": pid, "running": False, "project_root": key}


watch_manager = WatchProcessManager()
