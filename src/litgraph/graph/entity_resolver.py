"""Catalog-based entity name resolution (build-time, no aliases)."""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.graph.entity_disambiguator import EntityDisambiguator

AUTO_MERGE_THRESHOLD = 0.92
CANDIDATE_THRESHOLD = 0.82
MAX_AMBIGUOUS_CANDIDATES = 3


def normalize_key(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def acronym_of(name: str) -> str:
    words = normalize_key(name).split()
    return "".join(w[0] for w in words if w)


def safe_merge(query_key: str, candidate_key: str) -> bool:
    if query_key == candidate_key:
        return True
    if len(query_key) <= 3 or len(candidate_key) <= 3:
        return query_key == candidate_key
    ta, tb = set(query_key.split()), set(candidate_key.split())
    if ta and tb:
        overlap = len(ta & tb) / min(len(ta), len(tb))
        if overlap < 0.5:
            return False
    return True


def _entity_field_map(entity_type: str) -> str:
    key = entity_type.lower().rstrip("s")
    if key == "method":
        return "methods"
    if key == "task":
        return "tasks"
    if key == "dataset":
        return "datasets"
    return key + "s"


class EntityResolver:
    def __init__(self, project_config: Dict[str, Any]) -> None:
        er = project_config.get("entity_resolution") or {}
        self.auto_merge_threshold = float(er.get("auto_merge_threshold", AUTO_MERGE_THRESHOLD))
        self.candidate_threshold = float(er.get("candidate_threshold", CANDIDATE_THRESHOLD))
        disambig_config = {
            "disambiguation_enabled": er.get("disambiguation_enabled", True),
            "llm_provider": project_config.get("llm_provider", "openai"),
            "llm_model": project_config.get("llm_model"),
        }
        self._disambiguator = EntityDisambiguator(disambig_config)
        self.stats = {"resolved": 0, "disambiguated": 0, "new": 0}

    def resolve(self, name: str, entity_type: str, catalog: EntityCatalog) -> str:
        original = (name or "").strip()
        if not original:
            return original

        existing = catalog.names(entity_type)
        key = normalize_key(original)

        for candidate in existing:
            if normalize_key(candidate) == key:
                self.stats["resolved"] += 1
                return candidate

        if len(key) <= 4:
            for candidate in existing:
                if key == acronym_of(candidate):
                    self.stats["resolved"] += 1
                    return candidate

        scored: List[Tuple[float, str]] = []
        for candidate in existing:
            cand_key = normalize_key(candidate)
            score = difflib.SequenceMatcher(None, key, cand_key).ratio()
            if score >= self.candidate_threshold and safe_merge(key, cand_key):
                scored.append((score, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)

        if not scored:
            self.stats["new"] += 1
            return original

        best_score, best_name = scored[0]
        if best_score >= self.auto_merge_threshold:
            self.stats["resolved"] += 1
            return best_name

        ambiguous = [name for score, name in scored[:MAX_AMBIGUOUS_CANDIDATES]]
        if len(ambiguous) >= 2 or (
            len(ambiguous) == 1 and best_score < self.auto_merge_threshold
        ):
            chosen = self._disambiguator.disambiguate(original, entity_type, ambiguous)
            if chosen:
                self.stats["disambiguated"] += 1
                return chosen

        if len(ambiguous) == 1 and best_score >= self.candidate_threshold:
            self.stats["resolved"] += 1
            return ambiguous[0]

        self.stats["new"] += 1
        return original

    def normalize_extraction(self, extraction: dict, catalog: EntityCatalog) -> dict:
        out = dict(extraction)
        out["methods"] = [
            self.resolve(m, "method", catalog) for m in extraction.get("methods", [])
        ]
        out["tasks"] = [
            self.resolve(t, "task", catalog) for t in extraction.get("tasks", [])
        ]
        out["datasets"] = [
            self.resolve(d, "dataset", catalog) for d in extraction.get("datasets", [])
        ]
        return out

    def resolve_query_name(
        self,
        name: str,
        entity_type: str,
        catalog: EntityCatalog,
    ) -> str:
        """Resolve a search query against catalog without counting build stats."""
        original = (name or "").strip()
        if not original:
            return original
        stats = dict(self.stats)
        resolved = self.resolve(name, entity_type, catalog)
        self.stats = stats
        return resolved
