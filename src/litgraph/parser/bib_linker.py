"""Link BibTeX entries to paper IDs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_title(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def link_bib_to_paper(
    paper_id: str,
    parsed_path: Optional[str],
    parsed_title: Optional[str],
    bib_entries: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    path_stem = Path(parsed_path).stem if parsed_path else ""
    norm_title = _normalize_title(parsed_title or "")

    # 1. Same bib file stem as paper file stem
    for entry in bib_entries:
        if entry.get("source_stem") == paper_id or entry.get("source_stem") == path_stem:
            return entry

    # 2. bib_key matches paper_id
    for entry in bib_entries:
        if entry.get("bib_key") == paper_id:
            return entry

    # 3. Normalized title match
    if norm_title:
        for entry in bib_entries:
            if _normalize_title(entry.get("title", "")) == norm_title:
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
        )
        if match:
            linked[pid] = match
    return linked
