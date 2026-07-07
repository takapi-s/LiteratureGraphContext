"""Entity name normalization."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

FUZZY_THRESHOLD = 0.82


def _normalize_key(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_aliases(path: Path) -> Dict[str, Dict[str, List[str]]]:
    if not path.exists():
        return {"methods": {}, "datasets": {}, "tasks": {}}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "methods": data.get("methods", {}) or {},
        "datasets": data.get("datasets", {}) or {},
        "tasks": data.get("tasks", {}) or {},
    }


def _build_reverse_map(aliases: Dict[str, List[str]]) -> Dict[str, str]:
    reverse: Dict[str, str] = {}
    for canonical, variants in aliases.items():
        reverse[_normalize_key(canonical)] = canonical
        for v in variants:
            reverse[_normalize_key(v)] = canonical
    return reverse


class EntityNormalizer:
    def __init__(self, aliases_path: Path) -> None:
        data = load_aliases(aliases_path)
        self._methods = _build_reverse_map(data["methods"])
        self._datasets = _build_reverse_map(data["datasets"])
        self._tasks = _build_reverse_map(data["tasks"])

    def normalize_method(self, name: str) -> str:
        return self._methods.get(_normalize_key(name), name.strip())

    def normalize_dataset(self, name: str) -> str:
        return self._datasets.get(_normalize_key(name), name.strip())

    def normalize_task(self, name: str) -> str:
        return self._tasks.get(_normalize_key(name), name.strip())

    def _fuzzy_lookup(self, name: str, reverse: Dict[str, str]) -> Tuple[str, Optional[float]]:
        key = _normalize_key(name)
        if key in reverse:
            return reverse[key], 1.0
        best_score = 0.0
        best_canonical = name.strip()
        for alias_key, canonical in reverse.items():
            score = difflib.SequenceMatcher(None, key, alias_key).ratio()
            if score > best_score:
                best_score = score
                best_canonical = canonical
        if best_score >= FUZZY_THRESHOLD:
            return best_canonical, best_score
        return name.strip(), None

    def suggest_method(self, name: str) -> List[Dict[str, object]]:
        canonical, score = self._fuzzy_lookup(name, self._methods)
        if score is not None and score < 1.0:
            return [{"name": name, "suggestion": canonical, "score": round(score, 3)}]
        return []

    def normalize_method_fuzzy(self, name: str) -> str:
        return self._fuzzy_lookup(name, self._methods)[0]

    def normalize_dataset_fuzzy(self, name: str) -> str:
        return self._fuzzy_lookup(name, self._datasets)[0]

    def normalize_task_fuzzy(self, name: str) -> str:
        return self._fuzzy_lookup(name, self._tasks)[0]

    def normalize_extraction(self, extraction: dict, fuzzy: bool = True) -> dict:
        out = dict(extraction)
        if fuzzy:
            out["methods"] = [self.normalize_method_fuzzy(m) for m in extraction.get("methods", [])]
            out["datasets"] = [self.normalize_dataset_fuzzy(d) for d in extraction.get("datasets", [])]
            out["tasks"] = [self.normalize_task_fuzzy(t) for t in extraction.get("tasks", [])]
        else:
            out["methods"] = [self.normalize_method(m) for m in extraction.get("methods", [])]
            out["datasets"] = [self.normalize_dataset(d) for d in extraction.get("datasets", [])]
            out["tasks"] = [self.normalize_task(t) for t in extraction.get("tasks", [])]
        return out
