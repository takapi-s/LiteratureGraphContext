"""Markdown paper notes parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from litgraph.utils.ids import paper_id_from_path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _strip_note_suffix(stem: str) -> str:
    for suffix in ("_notes", "-notes"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def paper_id_from_md_path(path: Path) -> str:
    return paper_id_from_path(Path(_strip_note_suffix(path.stem)))


def parse_md(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    paper_id = paper_id_from_md_path(path)
    headings: List[Tuple[int, str, int]] = []
    for match in HEADING_RE.finditer(text):
        headings.append((match.start(), match.group(2).strip(), len(match.group(1))))

    sections: List[Dict[str, Any]] = []
    title = None

    if not headings:
        if text.strip():
            sections.append({
                "name": "FullText",
                "page_start": 1,
                "page_end": 1,
                "text": text.strip()[:20000],
            })
    else:
        for i, (start, name, level) in enumerate(headings):
            end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
            section_text = text[start:end].strip()
            section_text = HEADING_RE.sub("", section_text, count=1).strip()
            page_num = i + 1
            if i == 0 and level == 1:
                title = name
            sections.append({
                "name": name,
                "page_start": page_num,
                "page_end": page_num,
                "text": section_text[:20000],
            })

    if not title and sections:
        title = sections[0]["name"]

    return {
        "paper_id": paper_id,
        "path": str(path),
        "source_type": "md",
        "title": title,
        "pages": [{"page": 1, "text": text[:20000]}],
        "sections": sections,
        "full_text": text,
    }
