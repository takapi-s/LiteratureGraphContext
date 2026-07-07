"""Coordinate exclusive access to the embedded Kuzu database."""

from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

LITGRAPH_LOCK_COMMANDS: Set[str] = {"watch", "serve-mcp", "viz"}


@dataclass(frozen=True)
class LitgraphProcess:
    pid: int
    command: str
    cmdline: str


def project_root_for_db(db_path: Path) -> Path:
    """Return the project root for a standard `.litgraph/db/*.kuzu` path."""
    return db_path.resolve().parent.parent.parent


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def _read_cwd(pid: int) -> Optional[Path]:
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd")).resolve()
    except OSError:
        return None


def _read_env_var(pid: int, name: str) -> Optional[str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return None
    prefix = name.encode("utf-8") + b"="
    for entry in raw.split(b"\0"):
        if entry.startswith(prefix):
            return entry[len(prefix) :].decode("utf-8", errors="replace")
    return None


def _litgraph_subcommand(cmdline: str) -> Optional[str]:
    if "litgraph" not in cmdline:
        return None
    for command in LITGRAPH_LOCK_COMMANDS:
        if f"litgraph {command}" in cmdline:
            return command
    parts = cmdline.split()
    for index, part in enumerate(parts):
        if part.endswith("litgraph") or part == "litgraph":
            if index + 1 < len(parts):
                subcommand = parts[index + 1]
                if subcommand in LITGRAPH_LOCK_COMMANDS:
                    return subcommand
    return None


def _same_project(
    project_root: Path,
    db_path: Path,
    cmdline: str,
    cwd: Optional[Path],
    env_project_root: Optional[Path] = None,
) -> bool:
    project_str = str(project_root)
    db_str = str(db_path.resolve())
    if project_str in cmdline or db_str in cmdline:
        return True
    if env_project_root is not None and env_project_root.resolve() == project_root.resolve():
        return True
    if cwd is None:
        return False
    try:
        cwd.relative_to(project_root)
        return True
    except ValueError:
        return cwd == project_root


def find_conflicting_processes(
    db_path: Path,
    exclude_pid: Optional[int] = None,
) -> List[LitgraphProcess]:
    """Find long-running litgraph processes that may hold the Kuzu lock."""
    project_root = project_root_for_db(db_path)
    current_pid = exclude_pid if exclude_pid is not None else os.getpid()
    matches: List[LitgraphProcess] = []

    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return matches

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == current_pid:
            continue
        cmdline = _read_cmdline(pid)
        subcommand = _litgraph_subcommand(cmdline)
        if subcommand is None:
            continue
        cwd = _read_cwd(pid)
        env_root_raw = _read_env_var(pid, "LITGRAPH_PROJECT_ROOT")
        env_project_root = Path(env_root_raw).expanduser().resolve() if env_root_raw else None
        if _same_project(project_root, db_path, cmdline, cwd, env_project_root):
            matches.append(LitgraphProcess(pid=pid, command=subcommand, cmdline=cmdline))
    return matches


def release_db_lock(
    db_path: Path,
    exclude_pid: Optional[int] = None,
    wait_seconds: float = 1.5,
) -> List[LitgraphProcess]:
    """Stop sibling litgraph processes that hold the same Kuzu database lock."""
    stopped: List[LitgraphProcess] = []
    for proc in find_conflicting_processes(db_path, exclude_pid=exclude_pid):
        try:
            os.kill(proc.pid, signal.SIGTERM)
            stopped.append(proc)
        except OSError:
            continue
    if stopped:
        time.sleep(wait_seconds)
    return stopped
