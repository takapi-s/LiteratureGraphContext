"""Query layer for literature graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.graph.kuzu_store import get_graph_store


class PaperFinder:
    def __init__(self, db_path: Path) -> None:
        self.store = get_graph_store(db_path)
        self.store.initialize_schema()

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
            "limitations": paper.get("limitations", []),
        }

    def find_papers_by_method(self, method: str) -> List[Dict[str, Any]]:
        from litgraph.graph.normalizer import EntityNormalizer

        aliases_path = self.store.db_path.parent.parent / "aliases.yaml"
        normalizer = EntityNormalizer(aliases_path)
        canonical = normalizer.normalize_method(method)
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
        header = "| Paper | Task | Method | Dataset | Limitation |\n|---|---|---|---|---|\n"
        lines = [
            f"| {r.get('title', r.get('paper_id'))} | {r.get('task', '')} | {r.get('method', '')} | {r.get('dataset', '')} | {r.get('limitation', '')} |"
            for r in rows
        ]
        return {"papers": rows, "markdown_table": header + "\n".join(lines)}
