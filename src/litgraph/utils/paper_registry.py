"""Persistent paper_id registry: opaque UUID assigned at first ingest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.utils.ids import new_paper_id


def _registry_path(litgraph_dir: Path) -> Path:
    return litgraph_dir / "paper_registry.json"


def load_registry(litgraph_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = _registry_path(litgraph_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): dict(v) for k, v in (data or {}).items()}


def save_registry(litgraph_dir: Path, registry: Dict[str, Dict[str, Any]]) -> None:
    path = _registry_path(litgraph_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def assign_paper_id(
    litgraph_dir: Path,
    source_path: str,
    content_hash: str = "",
) -> str:
    """Return stable paper_id for source_path; create UUID on first sight."""
    registry = load_registry(litgraph_dir)
    entry = registry.get(source_path)
    if entry and entry.get("paper_id"):
        if not content_hash or entry.get("content_hash") == content_hash:
            return str(entry["paper_id"])
        entry["content_hash"] = content_hash
        entry["updated_at"] = _utc_now()
        registry[source_path] = entry
        save_registry(litgraph_dir, registry)
        return str(entry["paper_id"])

    paper_id = new_paper_id()
    registry[source_path] = {
        "paper_id": paper_id,
        "content_hash": content_hash,
        "assigned_at": _utc_now(),
    }
    save_registry(litgraph_dir, registry)
    return paper_id


def get_paper_id_for_path(litgraph_dir: Path, source_path: str) -> Optional[str]:
    entry = load_registry(litgraph_dir).get(source_path)
    if entry:
        return str(entry.get("paper_id") or "")
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
