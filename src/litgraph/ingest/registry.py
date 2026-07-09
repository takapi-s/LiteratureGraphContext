"""Adapter registry and payload resolution."""

from __future__ import annotations

from typing import List, Optional

from litgraph.ingest.arxiv import ArxivAdapter
from litgraph.ingest.base import IngestPayload, SourceAdapter
from litgraph.ingest.local import LocalFileAdapter
from litgraph.ingest.url import UrlAdapter
from litgraph.ingest.zotero import ZoteroAdapter

_ADAPTERS: List[SourceAdapter] = [
  ArxivAdapter(),
  UrlAdapter(),
  ZoteroAdapter(),
  LocalFileAdapter(),
]


def get_adapter(source_ref: str) -> SourceAdapter:
  for adapter in _ADAPTERS:
    if adapter.supports(source_ref):
      return adapter
  raise ValueError(f"No ingest adapter supports source_ref: {source_ref}")


def resolve_ingest_payload(
  source_ref: str,
  *,
  data: Optional[bytes] = None,
  filename: Optional[str] = None,
) -> IngestPayload:
  """Resolve bytes from a source_ref, optionally using provided data for bytes:// refs."""
  ref = source_ref.strip()
  if ref.startswith("bytes://") or data is not None:
    if data is None:
      raise ValueError("bytes ingest requires data=...")
    name = filename or ref.split("/")[-1] or "ingest.pdf"
    return IngestPayload(
      data=data,
      filename=name,
      source_ref=ref if ref.startswith("bytes://") else f"bytes://{name}",
      content_type="application/pdf" if name.lower().endswith(".pdf") else "application/octet-stream",
    )
  adapter = get_adapter(ref)
  return adapter.fetch(ref)
