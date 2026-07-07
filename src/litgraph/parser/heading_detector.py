"""Block-based heading detection from PDF layout spans."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Map normalized heading text to canonical section names (aligned with section_splitter).
HEADING_KEYWORDS: List[Tuple[str, re.Pattern[str]]] = [
    ("Abstract", re.compile(r"^abstract$", re.I)),
    ("Introduction", re.compile(r"^(?:\d+\.?\s*)?(?:I{1,3}\.?\s*)?introduction$", re.I)),
    ("RelatedWork", re.compile(r"^(?:\d+\.?\s*)?(?:related work|prior work|literature review|previous work)$", re.I)),
    ("Background", re.compile(r"^(?:\d+\.?\s*)?(?:background|preliminaries)$", re.I)),
    ("Method", re.compile(r"^(?:\d+\.?\s*)?(?:method|methods|methodology|materials and methods|approach)$", re.I)),
    ("Experiment", re.compile(r"^(?:\d+\.?\s*)?(?:experiment|experiments|evaluation|results|experimental setup)$", re.I)),
    ("Discussion", re.compile(r"^(?:\d+\.?\s*)?(?:discussion)$", re.I)),
    ("Conclusion", re.compile(r"^(?:\d+\.?\s*)?(?:conclusion|conclusions)$", re.I)),
    ("References", re.compile(r"^(?:\d+\.?\s*)?(?:references|bibliography)$", re.I)),
    ("Acknowledgments", re.compile(r"^(?:\d+\.?\s*)?(?:acknowledgments?|acknowledgements?)$", re.I)),
]


def _canonical_section_name(text: str) -> Optional[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    for name, pattern in HEADING_KEYWORDS:
        if pattern.match(cleaned):
            return name
    return None


def _line_spans_from_page(page_dict: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
    """Group dict-mode spans into lines with dominant font size."""
    lines: List[Dict[str, Any]] = []
    for block in page_dict.get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            sizes = [float(s.get("size", 0)) for s in spans if s.get("size")]
            if not sizes:
                continue
            bbox = line.get("bbox") or spans[0].get("bbox") or [0, 0, 0, 0]
            lines.append({
                "text": text,
                "size": sum(sizes) / len(sizes),
                "page": page_num,
                "y0": float(bbox[1]) if len(bbox) > 1 else 0.0,
            })
    return lines


def extract_page_lines(pages_dict: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten all lines from parsed PDF dict pages."""
    all_lines: List[Dict[str, Any]] = []
    for page in pages_dict:
        page_num = int(page.get("page", 1))
        page_dict = page.get("dict") or {}
        all_lines.extend(_line_spans_from_page(page_dict, page_num))
    return all_lines


def find_block_section_starts(
    full_text: str,
    pages: List[Dict[str, Any]],
) -> Tuple[List[Tuple[str, int]], List[str]]:
    """
    Return (section_name, char_offset) hits and list of block-detected section names.
    Uses font size relative to body text on lines that match heading keywords.
    """
    lines = extract_page_lines(pages)
    if not lines:
        return [], []

    sizes = sorted(line["size"] for line in lines)
    body_size = sizes[max(0, len(sizes) // 4)]
    threshold = body_size * 1.12

    hits: List[Tuple[str, int]] = []
    block_names: List[str] = []

    # Map line text to offset in full_text by searching sequentially
    search_from = 0
    for line in lines:
        text = line["text"]
        if line["size"] < threshold or len(text) > 80:
            search_from = full_text.find(text, search_from)
            if search_from >= 0:
                search_from += len(text)
            continue
        name = _canonical_section_name(text)
        if not name:
            search_from = full_text.find(text, search_from)
            if search_from >= 0:
                search_from += len(text)
            continue
        pos = full_text.find(text, search_from)
        if pos < 0:
            continue
        hits.append((name, pos))
        block_names.append(name)
        search_from = pos + len(text)

    # Deduplicate by section name (first occurrence)
    deduped: List[Tuple[str, int]] = []
    seen = set()
    for name, pos in sorted(hits, key=lambda x: x[1]):
        if name not in seen:
            deduped.append((name, pos))
            seen.add(name)
    return deduped, block_names
