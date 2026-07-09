"""Ingest adapters for programmatic paper ingestion."""

from litgraph.ingest.base import IngestPayload, SourceAdapter
from litgraph.ingest.registry import resolve_ingest_payload

__all__ = ["IngestPayload", "SourceAdapter", "resolve_ingest_payload"]
