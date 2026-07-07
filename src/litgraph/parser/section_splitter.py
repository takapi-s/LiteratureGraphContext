"""Heuristic section splitting for academic papers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from litgraph.parser.heading_detector import find_block_section_starts

SECTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("Abstract", re.compile(r"^\s*abstract\s*$", re.I | re.M)),
    ("Introduction", re.compile(r"^\s*(?:\d+\.?\s*)?(?:I{1,3}\.?\s*)?introduction\s*$", re.I | re.M)),
    ("RelatedWork", re.compile(
        r"^\s*(?:\d+\.?\s*)?(?:related work|prior work|literature review|previous work)\s*$",
        re.I | re.M,
    )),
    ("Background", re.compile(r"^\s*(?:\d+\.?\s*)?(?:background|preliminaries)\s*$", re.I | re.M)),
    ("Method", re.compile(
        r"^\s*(?:\d+\.?\s*)?(?:methods?|methodology|materials and methods|approach)\s*$",
        re.I | re.M,
    )),
    ("Experiment", re.compile(
        r"^\s*(?:\d+\.?\s*)?(?:experiments?|evaluation|results|experimental setup)\s*$",
        re.I | re.M,
    )),
    ("Discussion", re.compile(r"^\s*(?:\d+\.?\s*)?discussion\s*$", re.I | re.M)),
    ("Conclusion", re.compile(r"^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions)\s*$", re.I | re.M)),
    ("References", re.compile(r"^\s*(?:\d+\.?\s*)?(?:references|bibliography)\s*$", re.I | re.M)),
    ("Acknowledgments", re.compile(r"^\s*(?:\d+\.?\s*)?acknowledgments?\s*$", re.I | re.M)),
]

_TITLE_SKIP_RE = re.compile(
    r"^(abstract|introduction|\d+\.|arxiv|doi|http|www\.|@|university|proceedings|journal|vol\.|pp\.)",
    re.I,
)


def _find_regex_section_starts(text: str) -> Tuple[List[Tuple[str, int]], List[str]]:
    hits: List[Tuple[str, int]] = []
    regex_names: List[str] = []
    for name, pattern in SECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append((name, match.start()))
            regex_names.append(name)
    hits.sort(key=lambda x: x[1])
    deduped: List[Tuple[str, int]] = []
    seen = set()
    for name, pos in hits:
        if name not in seen:
            deduped.append((name, pos))
            seen.add(name)
    return deduped, regex_names


def _merge_section_starts(
    regex_starts: List[Tuple[str, int]],
    block_starts: List[Tuple[str, int]],
) -> Tuple[List[Tuple[str, int]], str]:
    """Merge regex and block hits; per section name keep earliest offset."""
    combined: Dict[str, int] = {}
    for name, pos in regex_starts + block_starts:
        if name not in combined or pos < combined[name]:
            combined[name] = pos
    merged = sorted(combined.items(), key=lambda x: x[1])
    if regex_starts and block_starts:
        detection = "merged"
    elif block_starts:
        detection = "blocks"
    elif regex_starts:
        detection = "regex"
    else:
        detection = "none"
    return merged, detection


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

    regex_starts, regex_hits = _find_regex_section_starts(full_text)
    block_starts, block_hits = find_block_section_starts(full_text, pages)
    starts, detection = _merge_section_starts(regex_starts, block_starts)

    sections: List[Dict[str, Any]] = []
    fallback_fulltext = False

    if not starts:
        fallback_fulltext = True
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
    section_meta = {
        "detection": detection,
        "regex_hits": regex_hits,
        "block_hits": block_hits,
        "fallback_fulltext": fallback_fulltext,
        "section_names": [s["name"] for s in sections],
    }

    return {
        **parsed,
        "title": title,
        "sections": sections,
        "section_meta": section_meta,
    }


def _guess_title(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:20]:
        if len(line) > 8 and not _TITLE_SKIP_RE.match(line):
            return line[:300]
    return lines[0][:300] if lines else None


def get_section_text(parsed: Dict[str, Any], *names: str) -> str:
    """Return text of the first matching section by name."""
    wanted = {n.lower() for n in names}
    for sec in parsed.get("sections") or []:
        if str(sec.get("name", "")).lower() in wanted:
            return str(sec.get("text") or "")
    return ""
