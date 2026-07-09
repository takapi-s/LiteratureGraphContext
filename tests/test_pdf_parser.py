"""Tests for PDF parsing."""

from __future__ import annotations

import pytest
from pathlib import Path

from litgraph.parser.pdf_parser import EmptyPdfError, parse_pdf


def test_parse_pdf_rejects_empty_file(tmp_path):
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"")

    with pytest.raises(EmptyPdfError, match="empty PDF"):
        parse_pdf(pdf)
