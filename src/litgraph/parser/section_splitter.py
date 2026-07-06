"""Heuristic section splitting for academic papers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

SECTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("Abstract", re.compile(r"^\s*abstract\s*$", re.I | re.M)),
    ("Introduction", re.compile(r"^\s*1\.?\s*introduction\s*$", re.I | re.M)),
    ("Method", re.compile(r"^\s*(?:\d+\.?\s*)?(?:method|methodology|approach)\s*$", re.I | re.M)),
    ("Experiment", re.compile(r"^\s*(?:\d+\.?\s*)?(?:experiment|evaluation|results)\s*$", re.I | re.M)),
    ("Conclusion", re.compile(r"^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions|discussion)\s*$", re.I | re.M)),
]


def _find_section_starts(text: str) -> List[Tuple[str, int]]:
    hits: List[Tuple[str, int]] = []
    for name, pattern in SECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append((name, match.start()))
    hits.sort(key=lambda x: x[1])
    deduped: List[Tuple[str, int]] = []
    seen = set()
    for name, pos in hits:
        if name not in seen:
            deduped.append((name, pos))
            seen.add(name)
    return deduped


def _page_for_offset(pages: List[Dict[str, Any]], offset: int) -> int:
    cursor = 0
    for page in pages:
        chunk = page.get("text", "")
        end = cursor + len(chunk) + 1
        if offset <= end:
            return int(page["page"])
        cursor = end
    return int(pages[-1]["page"]) if pages else 1


def split_sections(parsed: Dict[str, Any]) -> Dict[str, Any]:
    pages: List[Dict[str, Any]] = parsed.get("pages", [])
    full_text = parsed.get("full_text") or "\n".join(p.get("text", "") for p in pages)
    starts = _find_section_starts(full_text)
    sections: List[Dict[str, Any]] = []

    if not starts:
        if full_text.strip():
            sections.append({
                "name": "FullText",
                "page_start": 1,
                "page_end": pages[-1]["page"] if pages else 1,
                "text": full_text[:20000],
            })
    else:
        for i, (name, start) in enumerate(starts):
            end = starts[i + 1][1] if i + 1 < len(starts) else len(full_text)
            section_text = full_text[start:end].strip()
            sections.append({
                "name": name,
                "page_start": _page_for_offset(pages, start),
                "page_end": _page_for_offset(pages, end - 1),
                "text": section_text[:20000],
            })

    title = _guess_title(full_text)
    return {**parsed, "title": title, "sections": sections}


def _guess_title(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:20]:
        if len(line) > 8 and not re.match(r"^(abstract|introduction|\d+\.)", line, re.I):
            return line[:300]
    return lines[0][:300] if lines else None
