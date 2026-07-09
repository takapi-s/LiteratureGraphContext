"""arXiv source adapter."""

from __future__ import annotations

import re

import httpx

from litgraph.ingest.base import IngestPayload

_ARXIV_ID_RE = re.compile(
  r"^(?:arxiv://)?(?:(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$",
  re.I,
)


def normalize_arxiv_id(source_ref: str) -> str:
  ref = source_ref.strip()
  if ref.startswith("arxiv://"):
    ref = ref[len("arxiv://") :]
  match = _ARXIV_ID_RE.match(ref)
  if not match:
    raise ValueError(f"Invalid arXiv source_ref: {source_ref}")
  return match.group(1)


class ArxivAdapter:
  def supports(self, source_ref: str) -> bool:
    try:
      normalize_arxiv_id(source_ref)
      return True
    except ValueError:
      return False

  def fetch(self, source_ref: str) -> IngestPayload:
    arxiv_id = normalize_arxiv_id(source_ref)
    pdf_url = f"https://export.arxiv.org/pdf/{arxiv_id}.pdf"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
      response = client.get(pdf_url)
      response.raise_for_status()
    return IngestPayload(
      data=response.content,
      filename=f"{arxiv_id.replace('/', '_')}.pdf",
      source_ref=f"arxiv://{arxiv_id}",
      content_type="application/pdf",
      metadata={"arxiv_id": arxiv_id, "pdf_url": pdf_url},
    )
