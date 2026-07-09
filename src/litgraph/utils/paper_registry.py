"""Persistent paper_id registry: opaque UUID assigned at first ingest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.utils.ids import new_paper_id
from litgraph.utils.workspace import DEFAULT_WORKSPACE, normalize_workspace_id


def _registry_path(litgraph_dir: Path) -> Path:
    return litgraph_dir / "paper_registry.json"


def _is_legacy_flat(data: Dict[str, Any]) -> bool:
    if not data:
        return False
    for value in data.values():
        if isinstance(value, dict) and "paper_id" in value:
            return True
    return False


def _load_full_registry(litgraph_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    path = _registry_path(litgraph_dir)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not raw:
        return {}
    if _is_legacy_flat(raw):
        return {DEFAULT_WORKSPACE: {str(k): dict(v) for k, v in raw.items()}}
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for workspace, entries in raw.items():
        if isinstance(entries, dict):
            result[str(workspace)] = {str(k): dict(v) for k, v in entries.items()}
    return result


def _save_full_registry(litgraph_dir: Path, full: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    path = _registry_path(litgraph_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")


def load_registry(litgraph_dir: Path, workspace_id: str = DEFAULT_WORKSPACE) -> Dict[str, Dict[str, Any]]:
    ws = normalize_workspace_id(workspace_id)
    full = _load_full_registry(litgraph_dir)
    return {str(k): dict(v) for k, v in full.get(ws, {}).items()}


def save_registry(
    litgraph_dir: Path,
    registry: Dict[str, Dict[str, Any]],
    workspace_id: str = DEFAULT_WORKSPACE,
) -> None:
    ws = normalize_workspace_id(workspace_id)
    full = _load_full_registry(litgraph_dir)
    full[ws] = registry
    _save_full_registry(litgraph_dir, full)


def assign_paper_id(
    litgraph_dir: Path,
    source_path: str,
    content_hash: str = "",
    *,
    workspace_id: str = DEFAULT_WORKSPACE,
    source_ref: str = "",
) -> str:
    """Return stable paper_id for source_path; create UUID on first sight."""
    ws = normalize_workspace_id(workspace_id)
    registry = load_registry(litgraph_dir, ws)
    entry = registry.get(source_path)
    if entry and entry.get("paper_id"):
        if not content_hash or entry.get("content_hash") == content_hash:
            if source_ref and not entry.get("source_ref"):
                entry["source_ref"] = source_ref
                registry[source_path] = entry
                save_registry(litgraph_dir, registry, ws)
            return str(entry["paper_id"])
        entry["content_hash"] = content_hash
        entry["updated_at"] = _utc_now()
        if source_ref:
            entry["source_ref"] = source_ref
        registry[source_path] = entry
        save_registry(litgraph_dir, registry, ws)
        return str(entry["paper_id"])

    paper_id = new_paper_id()
    registry[source_path] = {
        "paper_id": paper_id,
        "content_hash": content_hash,
        "assigned_at": _utc_now(),
    }
    if source_ref:
        registry[source_path]["source_ref"] = source_ref
    save_registry(litgraph_dir, registry, ws)
    return paper_id


def update_registry_entry(
    litgraph_dir: Path,
    source_path: str,
    paper_id: str,
    content_hash: str = "",
    *,
    workspace_id: str = DEFAULT_WORKSPACE,
    source_ref: str = "",
    zotero_key: str = "",
) -> None:
    ws = normalize_workspace_id(workspace_id)
    registry = load_registry(litgraph_dir, ws)
    entry = dict(registry.get(source_path) or {})
    entry["paper_id"] = paper_id
    if content_hash:
        entry["content_hash"] = content_hash
    if source_ref:
        entry["source_ref"] = source_ref
    if zotero_key:
        entry["zotero_key"] = zotero_key
    entry.setdefault("assigned_at", _utc_now())
    entry["updated_at"] = _utc_now()
    registry[source_path] = entry
    save_registry(litgraph_dir, registry, ws)


def get_paper_id_for_path(
    litgraph_dir: Path,
    source_path: str,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> Optional[str]:
    entry = load_registry(litgraph_dir, workspace_id).get(source_path)
    if entry:
        return str(entry.get("paper_id") or "")
    return None


def get_paper_id_for_source_ref(
    litgraph_dir: Path,
    source_ref: str,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> Optional[str]:
    registry = load_registry(litgraph_dir, workspace_id)
    for entry in registry.values():
        if entry.get("source_ref") == source_ref and entry.get("paper_id"):
            return str(entry["paper_id"])
    return None


def get_paper_id_for_zotero_key(
    litgraph_dir: Path,
    zotero_key: str,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> Optional[str]:
    registry = load_registry(litgraph_dir, workspace_id)
    for entry in registry.values():
        if entry.get("zotero_key") == zotero_key and entry.get("paper_id"):
            return str(entry["paper_id"])
    return None


def get_paper_id_for_doi(
    litgraph_dir: Path,
    doi: str,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> Optional[str]:
    if not doi:
        return None
    normalized = doi.strip().lower()
    registry = load_registry(litgraph_dir, workspace_id)
    for entry in registry.values():
        if str(entry.get("doi", "")).strip().lower() == normalized and entry.get("paper_id"):
            return str(entry["paper_id"])
    return None


def get_paper_id_for_content_hash(
    litgraph_dir: Path,
    content_hash: str,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> Optional[str]:
    if not content_hash:
        return None
    registry = load_registry(litgraph_dir, workspace_id)
    for entry in registry.values():
        if entry.get("content_hash") == content_hash and entry.get("paper_id"):
            return str(entry["paper_id"])
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
