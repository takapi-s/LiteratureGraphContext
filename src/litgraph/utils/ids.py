"""ID generation helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


def _slug(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower()).strip("_")
    return slug[:max_len].strip("_") or "unknown"


def _first_author_surname(authors: Any) -> str:
    if authors is None:
        return ""
    if isinstance(authors, list):
        if not authors:
            return ""
        author = str(authors[0])
    else:
        author = str(authors).split(";")[0].strip()
    author = author.strip()
    if "," in author:
        return _slug(author.split(",", 1)[0].strip(), max_len=24)
    parts = author.split()
    return _slug(parts[-1], max_len=24) if parts else ""


def new_paper_id() -> str:
    """Opaque immutable paper_id (Graphiti-style UUID)."""
    return f"p_{uuid4()}"


def paper_id_from_path(path: Path) -> str:
    """Deprecated: filename stem slug. Use paper_registry.assign_paper_id instead."""
    stem = path.stem
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", stem).strip("_").lower()
    return slug or "paper_unknown"


def paper_slug_from_metadata(
    title: Optional[str],
    doi: Optional[str] = None,
    year: Optional[int] = None,
    authors: Any = None,
) -> str:
    """Human-readable slug for display/search (not primary key)."""
    if doi:
        doi_slug = re.sub(r"[^a-z0-9]+", "_", doi.lower().strip()).strip("_")
        if doi_slug:
            return f"doi_{doi_slug}"[:80]

    author = _first_author_surname(authors) or "unknown"
    year_int: Optional[int] = None
    if isinstance(year, int):
        year_int = year
    elif isinstance(year, str):
        digits = re.search(r"(?:19|20)\d{2}", year)
        if digits:
            year_int = int(digits.group(0))
    yr = str(year_int) if year_int and year_int > 0 else "unknown"
    title_part = _slug((title or "untitled")[:80], max_len=40)
    return f"{author}_{yr}_{title_part}"[:80]


def paper_id_from_metadata(
    title: Optional[str],
    doi: Optional[str] = None,
    year: Optional[int] = None,
    authors: Any = None,
) -> str:
    """Deprecated alias for paper_slug_from_metadata."""
    return paper_slug_from_metadata(title, doi=doi, year=year, authors=authors)


def entity_id(entity_type: str, name: str, workspace_id: str = "default") -> str:
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    digest = hashlib.sha256(f"{workspace_id}:{entity_type}:{normalized}".encode()).hexdigest()[:12]
    prefix = entity_type.lower()
    return f"{prefix}_{digest}"


def claim_id(paper_id: str, index: int) -> str:
    return f"claim_{paper_id}_{index:03d}"


def limitation_id(paper_id: str, index: int) -> str:
    return f"limitation_{paper_id}_{index:03d}"


def evidence_id(paper_id: str, kind: str, index: int) -> str:
    return f"evidence_{kind}_{paper_id}_{index:03d}"
