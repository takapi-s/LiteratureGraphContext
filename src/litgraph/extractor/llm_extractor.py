"""LLM-based structured extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.extractor.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE
from litgraph.extractor.providers import get_provider
from litgraph.extractor.schema import PaperExtraction


def _sections_text(sections: List[Dict[str, Any]]) -> str:
    parts = []
    for sec in sections:
        parts.append(f"## {sec.get('name', 'Section')} (pages {sec.get('page_start')}-{sec.get('page_end')})\n{sec.get('text', '')[:8000]}")
    return "\n\n".join(parts)


def extract_paper(
    parsed: Dict[str, Any],
    provider_name: str,
    model: Optional[str] = None,
) -> PaperExtraction:
    provider = get_provider(provider_name, model=model)
    user_prompt = EXTRACTION_USER_TEMPLATE.format(
        paper_id=parsed.get("paper_id", "unknown"),
        title=parsed.get("title") or "Unknown",
        sections_text=_sections_text(parsed.get("sections", [])),
    )
    raw = provider.complete_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
    raw.setdefault("paper_id", parsed.get("paper_id"))
    return PaperExtraction.model_validate(raw)


def save_extraction(path: Path, extraction: PaperExtraction) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(extraction.model_dump(), f, indent=2, ensure_ascii=False)


def load_extraction(path: Path) -> PaperExtraction:
    with open(path, encoding="utf-8") as f:
        return PaperExtraction.model_validate(json.load(f))
