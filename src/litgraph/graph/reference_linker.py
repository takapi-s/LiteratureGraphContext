"""Link parsed PDF references to indexed papers and build CITES pairs."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _norm(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _author_surname(author: str) -> str:
    author = author.strip()
    if "," in author:
        return author.split(",", 1)[0].strip().lower()
    parts = author.split()
    return parts[-1].lower() if parts else ""


def _paper_index(papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {p["paper_id"]: p for p in papers if p.get("paper_id")}


def _match_reference(
    ref: Dict[str, Any],
    papers: List[Dict[str, Any]],
) -> Optional[Tuple[str, str]]:
    """Return (cited_paper_id, match_method) or None."""
    ref_doi = (ref.get("doi") or "").lower().strip()
    ref_title = _norm(ref.get("title") or "")
    ref_year = ref.get("year")
    ref_surnames = {_author_surname(a) for a in ref.get("authors") or [] if _author_surname(a)}

    for paper in papers:
        pid = paper.get("paper_id") or ""
        if not pid:
            continue
        paper_doi = (paper.get("doi") or "").lower().strip()
        if ref_doi and paper_doi and ref_doi == paper_doi:
            return pid, "doi"

    for paper in papers:
        pid = paper.get("paper_id") or ""
        title = _norm(paper.get("title") or "")
        if ref_title and title and (ref_title in title or title in ref_title):
            if ref_year is None or paper.get("year") == ref_year or paper.get("year") in (-1, None):
                return pid, "title"
            if paper.get("year") == ref_year:
                return pid, "title_year"

    for paper in papers:
        pid = paper.get("paper_id") or ""
        title = _norm(paper.get("title") or "")
        year = paper.get("year")
        if ref_title and title and ref_year and year == ref_year:
            ratio = difflib.SequenceMatcher(None, ref_title, title).ratio()
            if ratio >= 0.72:
                return pid, "fuzzy_title_year"

    if ref_year and ref_surnames:
        for paper in papers:
            pid = paper.get("paper_id") or ""
            if paper.get("year") not in (ref_year, None) and paper.get("year") != -1:
                continue
            authors = paper.get("authors") or ""
            if isinstance(authors, list):
                paper_surnames = {_author_surname(a) for a in authors}
            else:
                paper_surnames = {_author_surname(a) for a in str(authors).split(";")}
            if ref_surnames & paper_surnames:
                return pid, "author_year"

    return None


def build_reference_citation_pairs(
    citing_paper_id: str,
    references: List[Dict[str, Any]],
    indexed_papers: List[Dict[str, Any]],
) -> List[Tuple[str, str]]:
    """Return (citing, cited) pairs resolved from PDF references."""
    pairs: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for ref in references:
        match = _match_reference(ref, indexed_papers)
        if not match:
            continue
        cited_id, _ = match
        if cited_id == citing_paper_id:
            continue
        pair = (citing_paper_id, cited_id)
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)
    return pairs


def load_parsed_references(parsed_cache_dir: Path, paper_id: str) -> List[Dict[str, Any]]:
    path = parsed_cache_dir / f"{paper_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return list(data.get("references") or [])


def build_all_reference_citation_pairs(
    parsed_cache_dir: Path,
    indexed_paper_ids: Set[str],
    paper_metadata: List[Dict[str, Any]],
) -> Tuple[List[Tuple[str, str]], int]:
    """
    Build CITES pairs from all parsed reference lists.
    Returns (pairs, resolved_count).
    """
    pairs: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    resolved = 0

    meta_by_id = _paper_index(paper_metadata)
    all_papers = list(meta_by_id.values())

    for citing_id in sorted(indexed_paper_ids):
        refs = load_parsed_references(parsed_cache_dir, citing_id)
        if not refs:
            continue
        for citing, cited in build_reference_citation_pairs(citing_id, refs, all_papers):
            if (citing, cited) not in seen:
                seen.add((citing, cited))
                pairs.append((citing, cited))
                resolved += 1

    return pairs, resolved
