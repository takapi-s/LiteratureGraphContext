"""PDF text extraction using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import fitz

from litgraph.utils.ids import paper_id_from_path


def parse_pdf(path: Path) -> Dict[str, Any]:
    paper_id = paper_id_from_path(path)
    pages: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []

    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            pages.append({"page": i + 1, "text": text})
            full_text_parts.append(text)

    return {
        "paper_id": paper_id,
        "path": str(path),
        "pages": pages,
        "full_text": "\n".join(full_text_parts),
    }
