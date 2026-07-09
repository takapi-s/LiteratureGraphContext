"""Zotero source adapter (metadata + optional PDF via API credentials)."""

from __future__ import annotations

import os
import re
from typing import Optional

from litgraph.ingest.base import IngestPayload
from litgraph.integrations.zotero import fetch_pdf_for_item

_ZOTERO_REF_RE = re.compile(r"^zotero://([^/]+)/([^/]+)$", re.I)


class ZoteroAdapter:
    def supports(self, source_ref: str) -> bool:
        return bool(_ZOTERO_REF_RE.match(source_ref.strip()))

    def fetch(self, source_ref: str) -> IngestPayload:
        match = _ZOTERO_REF_RE.match(source_ref.strip())
        if not match:
            raise ValueError(f"Invalid Zotero source_ref: {source_ref}")
        library = match.group(1)
        item_key = match.group(2)
        user_id = os.getenv("ZOTERO_USER_ID", "")
        api_key = os.getenv("ZOTERO_API_KEY", "")
        if not user_id or not api_key:
            raise ValueError("ZOTERO_USER_ID and ZOTERO_API_KEY are required for zotero:// ingest")
        pdf_bytes = fetch_pdf_for_item(user_id, api_key, item_key)
        if not pdf_bytes:
            raise ValueError(f"No PDF attachment found for Zotero item {item_key}")
        return IngestPayload(
            data=pdf_bytes,
            filename=f"zotero_{item_key}.pdf",
            source_ref=f"zotero://{library}/{item_key}",
            content_type="application/pdf",
            metadata={"zotero_key": item_key, "library": library},
        )
