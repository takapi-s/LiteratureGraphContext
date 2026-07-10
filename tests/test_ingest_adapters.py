"""Tests for ingest source adapters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from litgraph.ingest.arxiv import ArxivAdapter, normalize_arxiv_id
from litgraph.ingest.local import LocalFileAdapter
from litgraph.ingest.registry import get_adapter, resolve_ingest_payload


def test_normalize_arxiv_id() -> None:
    assert normalize_arxiv_id("arxiv://2401.12345") == "2401.12345"
    assert normalize_arxiv_id("https://arxiv.org/abs/2401.12345v2") == "2401.12345v2"
    assert normalize_arxiv_id("https://arxiv.org/html/2501.13956") == "2501.13956"


def test_local_adapter(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    adapter = LocalFileAdapter()
    payload = adapter.fetch(str(pdf))
    assert payload.filename == "paper.pdf"
    assert payload.data.startswith(b"%PDF")


def test_get_adapter_arxiv() -> None:
    adapter = get_adapter("arxiv://2401.99999")
    assert isinstance(adapter, ArxivAdapter)


@patch("litgraph.ingest.url.httpx.Client")
def test_url_adapter(mock_client_cls: MagicMock, tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.content = b"%PDF-1.4"
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    from litgraph.ingest.url import UrlAdapter

    payload = UrlAdapter().fetch("https://example.com/paper.pdf")
    assert payload.filename.endswith(".pdf")
    assert payload.data.startswith(b"%PDF")


def test_resolve_ingest_payload_bytes() -> None:
    payload = resolve_ingest_payload("bytes://test.pdf", data=b"hello", filename="test.pdf")
    assert payload.data == b"hello"
    assert payload.filename == "test.pdf"
