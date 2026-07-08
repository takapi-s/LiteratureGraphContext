"""In-memory catalog of entity names from DB and build batches."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

_CATALOG_FIELDS = (
    ("methods", "Methods"),
    ("tasks", "Tasks"),
    ("datasets", "Datasets"),
)


def catalog_path(litgraph_dir: Path) -> Path:
    return litgraph_dir / "cache" / "entity_catalog.json"


class EntityCatalog:
    def __init__(self) -> None:
        self._methods: Set[str] = set()
        self._tasks: Set[str] = set()
        self._datasets: Set[str] = set()

    @classmethod
    def from_store(cls, store: Any) -> "EntityCatalog":
        catalog = cls()
        catalog._methods = set(store.list_entity_names("Method"))
        catalog._tasks = set(store.list_entity_names("Task"))
        catalog._datasets = set(store.list_entity_names("Dataset"))
        return catalog

    @classmethod
    def load(cls, litgraph_dir: Path) -> "EntityCatalog":
        catalog = cls()
        path = catalog_path(litgraph_dir)
        if not path.exists():
            return catalog
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return catalog
        catalog._methods = {str(x) for x in (data.get("methods") or []) if x}
        catalog._tasks = {str(x) for x in (data.get("tasks") or []) if x}
        catalog._datasets = {str(x) for x in (data.get("datasets") or []) if x}
        return catalog

    def _bucket(self, entity_type: str) -> Set[str]:
        key = entity_type.lower().rstrip("s")
        if key == "method":
            return self._methods
        if key == "task":
            return self._tasks
        if key == "dataset":
            return self._datasets
        return set()

    def names(self, entity_type: str) -> List[str]:
        return sorted(self._bucket(entity_type))

    def add(self, entity_type: str, name: str) -> None:
        text = (name or "").strip()
        if text:
            self._bucket(entity_type).add(text)

    def ingest_extraction(self, extraction: Dict[str, Any]) -> None:
        for method in extraction.get("methods") or []:
            self.add("method", str(method))
        for task in extraction.get("tasks") or []:
            self.add("task", str(task))
        for dataset in extraction.get("datasets") or []:
            self.add("dataset", str(dataset))

    def save(self, litgraph_dir: Path) -> None:
        path = catalog_path(litgraph_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "methods": sorted(self._methods),
            "tasks": sorted(self._tasks),
            "datasets": sorted(self._datasets),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def prompt_section(self, max_per_type: int = 100) -> str:
        parts: List[str] = []
        for field, label in _CATALOG_FIELDS:
            items = sorted(self._bucket(field.rstrip("s")))[:max_per_type]
            if items:
                parts.append(f"{label}: " + ", ".join(items))
        if not parts:
            return "Known entities: (none yet)"
        return (
            "Known entities in the literature graph (prefer exact matches when appropriate):\n"
            + "\n".join(parts)
        )
