"""SHA-256 file cache for incremental processing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_cache(cache_path: Path) -> Dict[str, Any]:
    if not cache_path.exists():
        return {}
    with open(cache_path, encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache_path: Path, data: Dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def scan_and_update(
    files: List[Path],
    cache_path: Path,
    project_root: Path,
) -> Tuple[Dict[str, Any], List[Path]]:
    cache = load_cache(cache_path)
    changed: List[Path] = []

    for file_path in files:
        rel = str(file_path.relative_to(project_root)) if file_path.is_relative_to(project_root) else str(file_path)
        stat = file_path.stat()
        sha = file_sha256(file_path)
        entry = {
            "sha256": sha,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
        }
        prev = cache.get(rel)
        if not prev or prev.get("sha256") != sha:
            changed.append(file_path)
        cache[rel] = entry

    save_cache(cache_path, cache)
    return cache, changed


def find_removed_files(
    files: List[Path],
    cache_path: Path,
    project_root: Path,
) -> List[Path]:
    """Return paths that were in the hash cache but no longer on disk."""
    cache = load_cache(cache_path)
    current_rels: set[str] = set()
    for file_path in files:
        rel = (
            str(file_path.relative_to(project_root))
            if file_path.is_relative_to(project_root)
            else str(file_path)
        )
        current_rels.add(rel)
    removed_rels = set(cache.keys()) - current_rels
    removed_paths = [project_root / rel for rel in sorted(removed_rels)]
    if removed_rels:
        for rel in removed_rels:
            del cache[rel]
        save_cache(cache_path, cache)
    return removed_paths


def get_cached_entry(cache_path: Path, rel_path: str) -> Optional[Dict[str, Any]]:
    cache = load_cache(cache_path)
    return cache.get(rel_path)


def remove_from_cache(cache_path: Path, rel_path: str) -> None:
    cache = load_cache(cache_path)
    if rel_path in cache:
        del cache[rel_path]
        save_cache(cache_path, cache)


def update_cache_entry(
    cache_path: Path,
    rel_path: str,
    sha256: str,
    size: int,
) -> None:
    cache = load_cache(cache_path)
    cache[rel_path] = {
        "sha256": sha256,
        "size": size,
        "modified_at": _utc_now_iso(),
    }
    save_cache(cache_path, cache)
