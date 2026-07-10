"""Zotero source adapter (metadata + optional PDF via API credentials)."""

from __future__ import annotations

import re

from litgraph.ingest.base import IngestPayload
from litgraph.integrations.zotero import _resolve_zotero_credentials, fetch_pdf_for_item

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
        # Prefer library id from source_ref when it is already numeric.
        user_id, api_key = _resolve_zotero_credentials(
            user_id=library if library.isdigit() else None,
        )
        pdf_bytes = fetch_pdf_for_item(user_id, api_key, item_key)
        if not pdf_bytes:
            raise ValueError(f"No PDF attachment found for Zotero item {item_key}")
        return IngestPayload(
            data=pdf_bytes,
            filename=f"zotero_{item_key}.pdf",
            source_ref=f"zotero://{user_id}/{item_key}",
            content_type="application/pdf",
            metadata={"zotero_key": item_key, "library": user_id},
        )
