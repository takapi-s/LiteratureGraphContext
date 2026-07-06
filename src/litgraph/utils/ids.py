"""ID generation helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def paper_id_from_path(path: Path) -> str:
    stem = path.stem
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", stem).strip("_").lower()
    return slug or "paper_unknown"


def entity_id(entity_type: str, name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    digest = hashlib.sha256(f"{entity_type}:{normalized}".encode()).hexdigest()[:12]
    prefix = entity_type.lower()
    return f"{prefix}_{digest}"


def claim_id(paper_id: str, index: int) -> str:
    return f"claim_{paper_id}_{index:03d}"


def limitation_id(paper_id: str, index: int) -> str:
    return f"limitation_{paper_id}_{index:03d}"


def evidence_id(paper_id: str, kind: str, index: int) -> str:
    return f"evidence_{kind}_{paper_id}_{index:03d}"
