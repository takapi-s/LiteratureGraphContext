"""URL source adapter."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from litgraph.ingest.base import IngestPayload


class UrlAdapter:
  def supports(self, source_ref: str) -> bool:
    ref = source_ref.strip()
    if ref.startswith("url://"):
      return True
    parsed = urlparse(ref)
    return parsed.scheme in ("http", "https")

  def fetch(self, source_ref: str) -> IngestPayload:
    ref = source_ref.strip()
    url = ref[6:] if ref.startswith("url://") else ref
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
      response = client.get(url)
      response.raise_for_status()
    content_type = response.headers.get("content-type", "application/octet-stream")
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "download.pdf"
    if "." not in filename and "pdf" in content_type:
      filename = "download.pdf"
    return IngestPayload(
      data=response.content,
      filename=filename,
      source_ref=f"url://{url}",
      content_type=content_type,
      metadata={"url": url},
    )
