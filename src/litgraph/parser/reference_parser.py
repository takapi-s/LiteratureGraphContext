"""Parse bibliography entries from a References section."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

DOI_RE = re.compile(r"\b(10\.\d{4,}/[^\s\]}>,;]+)", re.I)
ARXIV_RE = re.compile(r"\barxiv[:\s]*(\d{4}\.\d{4,5})\b", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
# Numbered reference: [1] or 1.
ENTRY_START_RE = re.compile(r"^(?:\[?\d+\]?\.?)\s+")
AUTHOR_LEAD_RE = re.compile(
    r"^([A-Z][A-Za-z\-']+(?:\s+[A-Z]\.)?(?:\s*,\s*[A-Z][A-Za-z\-']+(?:\s+[A-Z]\.)?)*)\s*[,.]",
)


def _split_reference_entries(text: str) -> List[str]:
    if not text.strip():
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    # Drop standalone section header if present
    if re.match(r"^(?:references|bibliography)\s*$", lines[0], re.I):
        lines = lines[1:]
    if not lines:
        return []

    entries: List[str] = []
    current: List[str] = []
    for line in lines:
        if ENTRY_START_RE.match(line) and current:
            entries.append(" ".join(current))
            current = [ENTRY_START_RE.sub("", line).strip()]
        else:
            cleaned = ENTRY_START_RE.sub("", line).strip() if not current else line
            current.append(cleaned)
    if current:
        entries.append(" ".join(current))

    if len(entries) <= 1 and len(text) > 80:
        # Fallback: split on bracketed numbers
        parts = re.split(r"\n\s*(?=\[\d+\])", text)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]
    return entries if entries else [text.strip()]


def _extract_authors(raw: str) -> List[str]:
    match = AUTHOR_LEAD_RE.match(raw)
    if not match:
        return []
    chunk = match.group(1)
    return [a.strip() for a in re.split(r",\s*", chunk) if a.strip()]


def _extract_year(raw: str) -> Optional[int]:
    years = [int(m.group(0)) for m in YEAR_RE.finditer(raw)]
    if not years:
        return None
    # Prefer publication year near the end (common in reference formats)
    return years[-1]


def _extract_title(raw: str, authors: List[str], doi: str, year: Optional[int]) -> str:
    title = raw
    if doi:
        title = title.replace(doi, " ")
    for author in authors:
        title = title.replace(author, " ")
    if year:
        title = re.sub(rf"\b{year}\b", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .,;")
    # Trim venue tails after period if long
    if len(title) > 120 and ". " in title:
        title = title.split(". ")[0]
    return title[:300]


def parse_reference_entry(raw: str) -> Dict[str, Any]:
    doi_match = DOI_RE.search(raw)
    doi = doi_match.group(1).rstrip(".,;") if doi_match else ""
    arxiv_match = ARXIV_RE.search(raw)
    arxiv_id = arxiv_match.group(1) if arxiv_match else ""
    authors = _extract_authors(raw)
    year = _extract_year(raw)
    title = _extract_title(raw, authors, doi, year)
    return {
        "raw": raw[:2000],
        "doi": doi,
        "arxiv_id": arxiv_id,
        "year": year,
        "authors": authors,
        "title": title,
    }


def parse_references_section(text: str) -> Dict[str, Any]:
    """Parse References section text into structured entries."""
    entries_raw = _split_reference_entries(text)
    references = [parse_reference_entry(raw) for raw in entries_raw if raw.strip()]
    parsed = sum(1 for r in references if r.get("doi") or r.get("title") or r.get("authors"))
    return {
        "references": references,
        "reference_meta": {
            "count": len(references),
            "parsed": parsed,
        },
    }
