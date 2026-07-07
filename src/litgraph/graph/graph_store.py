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
    def upsert_bib_only_paper(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def upsert_cites_edge(self, citing_id: str, cited_id: str) -> None:
        ...

    @abstractmethod
    def upsert_paper_relationship(self, from_id: str, to_id: str, rel_type: str) -> None:
        ...

    @abstractmethod
    def delete_paper(self, paper_id: str) -> None:
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
    def build_literature_matrix(self, topic: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_paper_neighbors(
        self,
        paper_id: str,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def expand_paper_graph(
        self,
        paper_id: str,
        hops: int = 2,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_shared_method_neighbors(self, paper_id: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def export_graph_json(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
