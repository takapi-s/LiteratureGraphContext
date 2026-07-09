"""Local file source adapter."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from litgraph.ingest.base import IngestPayload


class LocalFileAdapter:
  def supports(self, source_ref: str) -> bool:
    ref = source_ref.strip()
    if ref.startswith("file://"):
      return True
    path = Path(ref)
    return path.exists() and path.is_file()

  def fetch(self, source_ref: str) -> IngestPayload:
    ref = source_ref.strip()
    if ref.startswith("file://"):
      parsed = urlparse(ref)
      path = Path(unquote(parsed.path))
    else:
      path = Path(ref).resolve()
    if not path.is_file():
      raise FileNotFoundError(f"Local file not found: {source_ref}")
    data = path.read_bytes()
    suffix = path.suffix.lower()
    content_type = {
      ".pdf": "application/pdf",
      ".md": "text/markdown",
      ".bib": "application/x-bibtex",
    }.get(suffix, "application/octet-stream")
    return IngestPayload(
      data=data,
      filename=path.name,
      source_ref=f"file://{path.resolve()}",
      content_type=content_type,
      metadata={"local_path": str(path.resolve())},
    )
