"""Daemon configuration and runtime status persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml

from litgraph.cli.config_manager import ResolvedContext, save_config_value

ExtractMode = Literal["auto", "manual"]

DEFAULT_DAEMON_CONFIG: Dict[str, Any] = {
    "http_host": "127.0.0.1",
    "http_port": 8766,
    "zotero_enabled": True,
    "zotero_interval_sec": 1800,
    "extract_mode": "manual",
    "watch_folder": False,
    "watch_auto_extract": False,
}


@dataclass
class DaemonSettings:
    http_host: str = "127.0.0.1"
    http_port: int = 8766
    zotero_enabled: bool = True
    zotero_interval_sec: int = 1800
    extract_mode: ExtractMode = "manual"
    watch_folder: bool = False
    watch_auto_extract: bool = False

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "DaemonSettings":
        data = {**DEFAULT_DAEMON_CONFIG, **(raw or {})}
        mode = str(data.get("extract_mode") or "manual").strip().lower()
        if mode not in ("auto", "manual"):
            mode = "manual"
        return cls(
            http_host=str(data.get("http_host") or "127.0.0.1"),
            http_port=int(data.get("http_port") or 8766),
            zotero_enabled=bool(data.get("zotero_enabled", True)),
            zotero_interval_sec=max(60, int(data.get("zotero_interval_sec") or 1800)),
            extract_mode=mode,  # type: ignore[arg-type]
            watch_folder=bool(data.get("watch_folder", False)),
            watch_auto_extract=bool(data.get("watch_auto_extract", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DaemonStatus:
    running: bool = False
    syncing: bool = False
    last_sync_at: Optional[str] = None
    last_sync_result: Optional[Dict[str, Any]] = None
    last_sync_error: Optional[str] = None
    pending_extract: List[str] = field(default_factory=list)
    last_extract_at: Optional[str] = None
    last_extract_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_daemon_settings(ctx: ResolvedContext) -> DaemonSettings:
    raw = ctx.config.get("daemon")
    if not isinstance(raw, dict):
        return DaemonSettings()
    return DaemonSettings.from_dict(raw)


def save_daemon_settings(ctx: ResolvedContext, settings: DaemonSettings) -> DaemonSettings:
    save_config_value(ctx.litgraph_dir, "daemon", settings.to_dict(), ctx.project_root)
    ctx.config["daemon"] = settings.to_dict()
    return settings


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def list_pending_extract(ctx: ResolvedContext) -> List[str]:
    from litgraph.cli.helpers import _needs_extraction
    from litgraph.utils.paper_registry import load_registry

    pending: List[str] = []
    registry = load_registry(ctx.litgraph_dir)
    for entry in registry.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("workspace_id") or "default") != ctx.workspace_id:
            continue
        paper_id = str(entry.get("paper_id") or "").strip()
        if paper_id and _needs_extraction(ctx, paper_id):
            pending.append(paper_id)
    return sorted(set(pending))


def settings_page_path() -> Path:
    return Path(__file__).parent / "static" / "settings.html"
