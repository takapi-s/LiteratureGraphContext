"""Entity name normalization."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml


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

    def normalize_extraction(self, extraction: dict) -> dict:
        out = dict(extraction)
        out["methods"] = [self.normalize_method(m) for m in extraction.get("methods", [])]
        out["datasets"] = [self.normalize_dataset(d) for d in extraction.get("datasets", [])]
        out["tasks"] = [self.normalize_task(t) for t in extraction.get("tasks", [])]
        return out
