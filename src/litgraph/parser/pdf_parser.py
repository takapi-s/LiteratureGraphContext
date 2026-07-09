"""PDF text extraction using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz

from litgraph.utils.ids import paper_id_from_path


class EmptyPdfError(ValueError):
    """Raised when a PDF file has no content."""


def parse_pdf(path: Path, paper_id: Optional[str] = None) -> Dict[str, Any]:
    from litgraph.utils.ids import paper_id_from_path
    pid = paper_id or paper_id_from_path(path)
    pages: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.stat().st_size == 0:
        raise EmptyPdfError(f"Cannot parse empty PDF: {path}")

    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            page_dict = page.get_text("dict") or {}
            pages.append({
                "page": i + 1,
                "text": text,
                "dict": page_dict,
            })
            full_text_parts.append(text)

    return {
        "paper_id": pid,
        "path": str(path),
        "pages": pages,
        "full_text": "\n".join(full_text_parts),
    }
