"""Graph store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GraphQueryInterface(ABC):
    @abstractmethod
    def initialize_schema(self) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def upsert_paper_metadata(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def upsert_paper_graph(self, extraction: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def list_papers(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def find_papers_by_method(self, method: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def find_limitations(self, topic: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_evidence_for_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def compare_papers(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def export_graph_json(self) -> Dict[str, Any]:
        ...
