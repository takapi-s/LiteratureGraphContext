"""LLM disambiguation for ambiguous entity name matches (build-time, limited B)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from litgraph.extractor.providers import get_provider

_SYSTEM = """You resolve ambiguous literature-graph entity names.
Return valid JSON only with key "choice": either one of the provided candidate strings exactly, or "NEW" if the extracted name is a distinct entity.
Do NOT merge a named architecture (e.g. BysGNN, STGCN, GMAN) into a generic family (e.g. Graph Neural Network).
"""

_USER_TEMPLATE = """Entity type: {entity_type}
Extracted name: {name}
Candidates: {candidates}

Return JSON: {{"choice": "<exact candidate or NEW>"}}
"""


class EntityDisambiguator:
    def __init__(self, config: Dict[str, Any]) -> None:
        self._enabled = bool(config.get("disambiguation_enabled", True))
        self._provider_name = str(config.get("llm_provider") or "openai")
        self._model = config.get("llm_model")

    def disambiguate(
        self,
        name: str,
        entity_type: str,
        candidates: List[str],
    ) -> Optional[str]:
        if not self._enabled or not candidates:
            return None
        try:
            provider = get_provider(self._provider_name, model=self._model)
            raw = provider.complete_json(
                _SYSTEM,
                _USER_TEMPLATE.format(
                    entity_type=entity_type,
                    name=name,
                    candidates=candidates,
                ),
            )
        except Exception:
            return None
        choice = str(raw.get("choice") or "").strip()
        if not choice or choice.upper() == "NEW":
            return None
        for candidate in candidates:
            if choice == candidate:
                return candidate
        lowered = choice.lower()
        for candidate in candidates:
            if candidate.lower() == lowered:
                return candidate
        return None
