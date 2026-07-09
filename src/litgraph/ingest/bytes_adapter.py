"""In-memory bytes source adapter."""

from __future__ import annotations

from litgraph.ingest.base import IngestPayload


class BytesAdapter:
  def supports(self, source_ref: str) -> bool:
    return source_ref.startswith("bytes://")

  def fetch(self, source_ref: str) -> IngestPayload:
    raise ValueError(
      "bytes:// source_ref requires ingest_from_bytes(); use resolve_ingest_payload with payload data."
    )
