"""Query layer for literature graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.graph.db_factory import get_graph_store
from litgraph.graph.normalizer import EntityNormalizer
from litgraph.query.comparison import comparison_markdown
from litgraph.query.related_work import generate_related_work_outline


class PaperFinder:
    def __init__(
        self,
        db_path: Path,
        aliases_path: Optional[Path] = None,
        backend: str = "kuzu",
        neo4j_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db_path = db_path
        self.backend = backend
        self.neo4j_config = neo4j_config
        self.aliases_path = aliases_path or (db_path.parent.parent / "aliases.yaml")
        self._store = None

    @property
    def store(self):
        if self._store is None:
            self._store = get_graph_store(self.db_path, backend=self.backend, neo4j_config=self.neo4j_config)
            self._store.initialize_schema()
        return self._store

    def close(self) -> None:
        if self._store is not None:
            self._store.close()
            self._store = None

    def list_papers(self) -> List[Dict[str, Any]]:
        return self.store.list_papers()

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_paper(paper_id)

    def summarize_paper(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        if not paper:
            return {"error": f"Paper not found: {paper_id}"}
        return {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title"),
            "tasks": paper.get("tasks", []),
            "methods": paper.get("methods", []),
            "datasets": paper.get("datasets", []),
            "metrics": paper.get("metrics", []),
            "contributions": paper.get("contributions", []),
            "limitations": paper.get("limitations", []),
        }

    def find_papers_by_method(self, method: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        normalizer = EntityNormalizer(self.aliases_path)
        canonical = normalizer.normalize_method_fuzzy(method) if fuzzy else normalizer.normalize_method(method)
        rows = self.store.find_papers_by_method(canonical)
        if rows:
            return rows
        return self.store.find_papers_by_method(method)

    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        return self.store.find_papers_by_task(task)

    def find_limitations(self, topic: str) -> Dict[str, Any]:
        items = self.store.find_limitations(topic)
        return {"limitations": items}

    def get_evidence_for_claim(self, claim_id: str) -> Dict[str, Any]:
        evidence = self.store.get_evidence_for_claim(claim_id)
        if not evidence:
            return {"error": f"Claim not found: {claim_id}"}
        return evidence

    def compare_papers(self, paper_ids: List[str]) -> Dict[str, Any]:
        rows = self.store.compare_papers(paper_ids)
        return {"papers": rows, "markdown_table": comparison_markdown(rows)}

    def build_literature_matrix(self, topic: str) -> Dict[str, Any]:
        rows = self.store.build_literature_matrix(topic)
        return {
            "topic": topic,
            "papers": rows,
            "count": len(rows),
            "markdown_table": comparison_markdown(rows),
        }

    def get_paper_neighbors(
        self,
        paper_id: str,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> Dict[str, Any]:
        if not self.get_paper(paper_id):
            return {"error": f"Paper not found: {paper_id}"}
        neighbors = self.store.get_paper_neighbors(
            paper_id,
            relationships=relationships,
            include_summary=include_summary,
        )
        return {"paper_id": paper_id, "neighbors": neighbors, "count": len(neighbors)}

    def _papers_full(self) -> List[Dict[str, Any]]:
        papers = []
        for row in self.list_papers():
            pid = row.get("paper_id")
            if pid:
                full = self.get_paper(pid)
                if full:
                    papers.append(full)
        return papers

    def related_work_outline(self, topic: str) -> Dict[str, Any]:
        return generate_related_work_outline(topic, self._papers_full())
