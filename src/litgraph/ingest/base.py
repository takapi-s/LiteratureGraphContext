"""Source adapter protocol for ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class IngestPayload:
    """Resolved bytes and metadata from a source_ref."""

    data: bytes
    filename: str
    source_ref: str
    content_type: str = "application/pdf"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    """Fetch paper bytes from a source_ref URI."""

    def supports(self, source_ref: str) -> bool:
        ...

    def fetch(self, source_ref: str) -> IngestPayload:
        ...
