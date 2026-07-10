"""Link BibTeX entries to paper IDs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_title(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _titles_compatible(a: str, b: str) -> bool:
    """Exact match, or one normalized title is a long prefix of the other."""
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < 24:
        return False
    return longer.startswith(shorter) or shorter in longer


def link_bib_to_paper(
    paper_id: str,
    parsed_path: Optional[str],
    parsed_title: Optional[str],
    bib_entries: List[Dict[str, Any]],
    *,
    zotero_key: Optional[str] = None,
    doi: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    path_stem = Path(parsed_path).stem if parsed_path else ""
    norm_title = _normalize_title(parsed_title or "")
    doi_norm = (doi or "").strip().lower()

    # 1. Same bib file stem as paper file stem
    for entry in bib_entries:
        if entry.get("source_stem") == paper_id or entry.get("source_stem") == path_stem:
            return entry

    # 2. Ingested Zotero PDF stems look like zotero_{itemKey}
    if path_stem.startswith("zotero_"):
        zkey = path_stem[len("zotero_") :]
        for entry in bib_entries:
            if entry.get("zotero_key") == zkey or entry.get("bib_key") == zkey:
                return entry

    # 3. Explicit zotero_key / DOI from registry
    if zotero_key:
        for entry in bib_entries:
            if entry.get("zotero_key") == zotero_key or entry.get("bib_key") == zotero_key:
                return entry
    if doi_norm:
        for entry in bib_entries:
            if str(entry.get("doi") or "").strip().lower() == doi_norm:
                return entry

    # 4. bib_key / zotero_key matches paper_id
    for entry in bib_entries:
        if entry.get("bib_key") == paper_id or entry.get("zotero_key") == paper_id:
            return entry

    # 5. Normalized title match (exact or truncated LLM title vs full bib title)
    if norm_title:
        for entry in bib_entries:
            if _titles_compatible(norm_title, _normalize_title(entry.get("title", ""))):
                return entry

    return None


def link_all_papers(
    paper_ids: List[Dict[str, Any]],
    bib_entries: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    linked: Dict[str, Dict[str, Any]] = {}
    for paper in paper_ids:
        pid = paper.get("paper_id") or paper.get("id")
        if not pid:
            continue
        match = link_bib_to_paper(
            pid,
            paper.get("path"),
            paper.get("title"),
            bib_entries,
            zotero_key=paper.get("zotero_key"),
            doi=paper.get("doi"),
        )
        if match:
            linked[pid] = match
    return linked
