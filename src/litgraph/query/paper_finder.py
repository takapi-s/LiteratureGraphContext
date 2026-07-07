"""Query layer for literature graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.graph.db_factory import get_graph_store
from litgraph.graph.normalizer import EntityNormalizer
from litgraph.query.comparison import comparison_markdown


from litgraph.query.gap_analysis import find_research_gaps as cluster_gaps
from litgraph.query.related_work import generate_related_work_outline


class PaperFinder:
    def __init__(
        self,
        db_path: Path,
        aliases_path: Optional[Path] = None,
        backend: str = "kuzu",
        neo4j_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.store = get_graph_store(db_path, backend=backend, neo4j_config=neo4j_config)
        self.store.initialize_schema()
        self.aliases_path = aliases_path or (db_path.parent.parent / "aliases.yaml")

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

    def collect_all_limitations(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for paper in self.list_papers():
            pid = paper.get("paper_id")
            if not pid:
                continue
            full = self.get_paper(pid)
            if not full:
                continue
            for lim in full.get("limitations") or []:
                if isinstance(lim, dict):
                    items.append({
                        "paper_id": pid,
                        "title": full.get("title"),
                        "limitation": lim.get("limitation") or lim.get("text", ""),
                        "text": lim.get("text", lim.get("limitation", "")),
                        "page": lim.get("page"),
                        "section": lim.get("section"),
                        "evidence_text": lim.get("evidence_text", ""),
                    })
        return items

    def _papers_full(self) -> List[Dict[str, Any]]:
        papers = []
        for row in self.list_papers():
            pid = row.get("paper_id")
            if pid:
                full = self.get_paper(pid)
                if full:
                    papers.append(full)
        return papers

    def find_research_gaps(self, topic: str, min_papers: int = 1) -> Dict[str, Any]:
        return cluster_gaps(topic, self.collect_all_limitations(), min_papers=min_papers)

    def related_work_outline(self, topic: str) -> Dict[str, Any]:
        return generate_related_work_outline(topic, self._papers_full())
