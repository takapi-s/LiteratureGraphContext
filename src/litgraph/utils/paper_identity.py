"""Paper identity: registry-backed UUID; legacy paper_id_map for backward compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.utils.ids import paper_slug_from_metadata


def _mapping_path(litgraph_dir: Path) -> Path:
    return litgraph_dir / "paper_id_map.json"


def load_paper_id_map(litgraph_dir: Path) -> Dict[str, str]:
    path = _mapping_path(litgraph_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): str(v) for k, v in (data or {}).items()}


def save_paper_id_map(litgraph_dir: Path, mapping: Dict[str, str]) -> None:
    path = _mapping_path(litgraph_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


def record_paper_id_mapping(litgraph_dir: Path, parse_paper_id: str, canonical_paper_id: str) -> None:
    """Legacy: no-op under UUID registry (kept for API compatibility)."""
    if not parse_paper_id or parse_paper_id == canonical_paper_id:
        return
    mapping = load_paper_id_map(litgraph_dir)
    mapping[parse_paper_id] = canonical_paper_id
    save_paper_id_map(litgraph_dir, mapping)


def resolve_canonical_paper_id(litgraph_dir: Path, paper_id: str) -> str:
    """Resolve legacy aliases and paper_id_map entries to canonical id."""
    mapping = load_paper_id_map(litgraph_dir)
    if paper_id in mapping:
        return mapping[paper_id]
    for old_id, new_id in mapping.items():
        if new_id == paper_id:
            return new_id
    return paper_id


def resolve_paper_id_from_registry(litgraph_dir: Path, candidate: str) -> Optional[str]:
    """Resolve a source filename, stem, or path from paper_registry.json to a paper_id.

    Lets callers pass e.g. ``mobility_gnn_2024`` or ``mobility_gnn_2024.pdf``
    instead of the opaque UUID assigned at ingest.
    """
    from litgraph.utils.paper_registry import load_registry

    text = (candidate or "").strip()
    if not text:
        return None
    lowered = text.lower().replace("\\", "/")
    for source_path, entry in load_registry(litgraph_dir).items():
        pid = str(entry.get("paper_id") or "")
        if not pid:
            continue
        normalized = source_path.lower().replace("\\", "/")
        path = Path(source_path)
        if lowered in (normalized, path.name.lower(), path.stem.lower()):
            return pid
    return None


def normalize_paper_id_input(paper_id: str) -> str:
    pid = (paper_id or "").strip()
    if pid.startswith("paper_"):
        return pid[6:]
    return pid


def finalize_extraction_identity(
    parsed: Dict[str, Any],
    extraction: Dict[str, Any],
    *,
    doi: Optional[str] = None,
) -> Dict[str, Any]:
    """Keep registry paper_id; attach provenance and optional display slug."""
    parse_id = str(parsed.get("paper_id") or extraction.get("paper_id", ""))
    out = dict(extraction)
    out["paper_id"] = parse_id
    out["parse_paper_id"] = parsed.get("parse_paper_id") or parse_id
    out["source_path"] = parsed.get("path") or parsed.get("source_path") or ""
    out["source_stem"] = parsed.get("source_stem") or (
        Path(out["source_path"]).stem if out["source_path"] else parse_id
    )
    out["content_hash"] = parsed.get("content_hash") or ""
    out["slug"] = paper_slug_from_metadata(
        extraction.get("title") or parsed.get("title"),
        doi=doi or parsed.get("doi") or extraction.get("doi"),
        year=extraction.get("year") or parsed.get("year"),
        authors=parsed.get("authors") or extraction.get("authors"),
    )
    if doi or parsed.get("doi"):
        out["doi"] = doi or parsed.get("doi")
    return out


def migrate_parsed_cache(
    parsed_cache_dir: Path,
    parse_paper_id: str,
    canonical_paper_id: str,
) -> None:
    """Legacy no-op when IDs are stable (UUID registry)."""
    if parse_paper_id == canonical_paper_id:
        return
    old_path = parsed_cache_dir / f"{parse_paper_id}.json"
    new_path = parsed_cache_dir / f"{canonical_paper_id}.json"
    if not old_path.exists() or old_path.resolve() == new_path.resolve():
        return
    try:
        doc = json.loads(old_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    doc["paper_id"] = canonical_paper_id
    new_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    old_path.unlink(missing_ok=True)


def migrate_extracted_cache(
    extracted_cache_dir: Path,
    parse_paper_id: str,
    canonical_paper_id: str,
    extraction: Dict[str, Any],
) -> Path:
    extracted_cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = extracted_cache_dir / f"{canonical_paper_id}.json"
    out_path.write_text(json.dumps(extraction, indent=2, ensure_ascii=False), encoding="utf-8")
    if parse_paper_id != canonical_paper_id:
        old_path = extracted_cache_dir / f"{parse_paper_id}.json"
        if old_path.exists() and old_path.resolve() != out_path.resolve():
            old_path.unlink(missing_ok=True)
    return out_path
