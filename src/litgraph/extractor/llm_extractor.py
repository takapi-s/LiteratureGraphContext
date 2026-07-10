"""LLM-based structured extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.extractor.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE
from litgraph.extractor.providers import get_provider
from litgraph.extractor.schema import PaperExtraction
from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.utils.paper_identity import finalize_extraction_identity

STRING_LIST_FIELDS = ("tasks", "methods", "datasets", "metrics")


def _coerce_string_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("text", "name", "value", "method", "task", "dataset", "metric"):
            value = item.get(key)
            if value:
                return str(value).strip()
        return ""
    if item is None:
        return ""
    return str(item).strip()


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        text = _coerce_string_item(value)
        return [text] if text else []
    out: List[str] = []
    for item in value:
        text = _coerce_string_item(item)
        if text:
            out.append(text)
    return out


def normalize_extraction_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce common LLM shape mistakes before Pydantic validation."""
    out = dict(raw)
    for field in STRING_LIST_FIELDS:
        if field in out:
            out[field] = _normalize_string_list(out.get(field))
    year = out.get("year")
    if isinstance(year, str):
        digits = re.search(r"(?:19|20)\d{2}", year)
        out["year"] = int(digits.group(0)) if digits else None
    for field in ("contributions", "claims", "limitations"):
        items = out.get(field)
        if not isinstance(items, list):
            continue
        fixed = []
        for item in items:
            if not isinstance(item, dict):
                fixed.append(item)
                continue
            row = dict(item)
            page = row.get("page")
            if isinstance(page, str) and page.strip().isdigit():
                row["page"] = int(page.strip())
            fixed.append(row)
        out[field] = fixed
    return out


def _sections_text(sections: List[Dict[str, Any]]) -> str:
    parts = []
    for sec in sections:
        parts.append(f"## {sec.get('name', 'Section')} (pages {sec.get('page_start')}-{sec.get('page_end')})\n{sec.get('text', '')[:8000]}")
    return "\n\n".join(parts)


def extract_paper(
    parsed: Dict[str, Any],
    provider_name: str,
    model: Optional[str] = None,
    *,
    doi: Optional[str] = None,
    entity_catalog: Optional[EntityCatalog] = None,
) -> PaperExtraction:
    provider = get_provider(provider_name, model=model)
    catalog = entity_catalog or EntityCatalog()
    user_prompt = EXTRACTION_USER_TEMPLATE.format(
        paper_id=parsed.get("paper_id", "unknown"),
        title=parsed.get("title") or "Unknown",
        known_entities=catalog.prompt_section(),
        sections_text=_sections_text(parsed.get("sections", [])),
    )
    raw = provider.complete_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
    raw.setdefault("paper_id", parsed.get("paper_id"))
    raw = finalize_extraction_identity(parsed, normalize_extraction_raw(raw), doi=doi)
    return PaperExtraction.model_validate(raw)


def save_extraction(path: Path, extraction: PaperExtraction) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(extraction.model_dump(), f, indent=2, ensure_ascii=False)


def load_extraction(path: Path) -> PaperExtraction:
    with open(path, encoding="utf-8") as f:
        return PaperExtraction.model_validate(json.load(f))
