"""Query layer for literature graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litgraph.graph.db_factory import get_graph_store
from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.graph.entity_resolver import EntityResolver
from litgraph.query.comparison import comparison_markdown
from litgraph.query.paper_search import search_papers as hybrid_search_papers
from litgraph.query.related_work import generate_related_work_outline
from litgraph.utils.paper_identity import (
    normalize_paper_id_input,
    resolve_canonical_paper_id,
    resolve_paper_id_from_registry,
)


class PaperFinder:
    def __init__(
        self,
        db_path: Path,
        backend: str = "kuzu",
        neo4j_config: Optional[Dict[str, Any]] = None,
        *,
        read_only: bool = False,
        project_config: Optional[Dict[str, Any]] = None,
        workspace_id: str = "default",
    ) -> None:
        self.db_path = db_path
        self.backend = backend
        self.neo4j_config = neo4j_config
        self.read_only = read_only
        self.project_config = project_config or {}
        self.workspace_id = workspace_id
        self.litgraph_dir = db_path.parent.parent
        self._store = None
        self._closed = False

    @property
    def store(self):
        if self._closed:
            self._closed = False
            self._store = None
        if self._store is None:
            self._store = get_graph_store(
                self.db_path,
                backend=self.backend,
                neo4j_config=self.neo4j_config,
                read_only=self.read_only,
                workspace_id=self.workspace_id,
            )
            if not self.read_only:
                self._store.initialize_schema()
        return self._store

    def close(self) -> None:
        if self._store is not None:
            self._store.close()
            self._store = None
        self._closed = True

    def _entity_catalog(self) -> EntityCatalog:
        return EntityCatalog.from_store(self.store)

    def _resolver(self) -> EntityResolver:
        return EntityResolver(self.project_config)

    def _resolve_paper_id(self, paper_id: str) -> str:
        pid = normalize_paper_id_input(paper_id)
        resolved = resolve_canonical_paper_id(self.litgraph_dir, pid)
        if resolved != pid:
            return resolved
        from_registry = resolve_paper_id_from_registry(self.litgraph_dir, pid)
        if from_registry:
            return from_registry
        return pid

    def _did_you_mean(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """Fuzzy-match query against known paper ids, titles, and source stems."""
        import difflib

        from litgraph.utils.paper_registry import load_registry

        candidates: Dict[str, str] = {}
        for row in self.list_papers():
            pid = str(row.get("paper_id") or "")
            if not pid:
                continue
            candidates.setdefault(pid.lower(), pid)
            title = str(row.get("title") or "")
            if title:
                candidates.setdefault(title.lower(), pid)
        for source_path, entry in load_registry(self.litgraph_dir).items():
            pid = str(entry.get("paper_id") or "")
            stem = Path(source_path).stem
            if pid and stem:
                candidates.setdefault(stem.lower(), pid)

        matches = difflib.get_close_matches(
            query.lower(), list(candidates.keys()), n=limit * 2, cutoff=0.6
        )
        out: List[Dict[str, str]] = []
        seen: set = set()
        for match in matches:
            pid = candidates[match]
            if pid in seen:
                continue
            seen.add(pid)
            out.append({"paper_id": pid, "matched": match})
            if len(out) >= limit:
                break
        return out

    def _paper_not_found_error(self, paper_id: str) -> Dict[str, Any]:
        suggestions = self.search_papers(paper_id, top_k=5)
        mapping = {}
        map_path = self.litgraph_dir / "paper_id_map.json"
        if map_path.exists():
            try:
                import json
                mapping = json.loads(map_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                mapping = {}
        if not self.list_papers():
            hint = (
                "No papers are indexed yet. Run: "
                "litgraph scan && litgraph parse && litgraph extract && litgraph build"
            )
        else:
            hint = (
                "Call search_papers with a title or topic keyword to obtain a valid "
                "paper_id, or pass the source filename (e.g. mypaper_2024.pdf)."
            )
        return {
            "error": f"Paper not found: {paper_id}",
            "hint": hint,
            "resolved_id": self._resolve_paper_id(paper_id),
            "did_you_mean": self._did_you_mean(paper_id),
            "suggestions": suggestions.get("papers", []),
            "paper_id_map_entries": {
                k: v for k, v in mapping.items()
                if k == paper_id or v == paper_id or paper_id in (k, v)
            },
        }

    def list_papers(self) -> List[Dict[str, Any]]:
        return self.store.list_papers()

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_paper_id(paper_id)
        paper = self.store.get_paper(resolved)
        if paper:
            return paper
        if resolved != paper_id:
            return self.store.get_paper(paper_id)
        return None

    def summarize_paper(self, paper_id: str) -> Dict[str, Any]:
        paper = self.get_paper(paper_id)
        if not paper:
            return self._paper_not_found_error(paper_id)
        return {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title"),
            "tasks": paper.get("tasks", []),
            "methods": paper.get("methods", []),
            "datasets": paper.get("datasets", []),
            "metrics": paper.get("metrics", []),
            "contributions": paper.get("contributions", []),
            "limitations": paper.get("limitations", []),
            "claims": paper.get("claims", []),
        }

    def find_papers_by_method(self, method: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        catalog = self._entity_catalog()
        resolver = self._resolver()
        canonical = (
            resolver.resolve_query_name(method, "method", catalog)
            if fuzzy
            else method.strip()
        )
        rows = self.store.find_papers_by_method(canonical)
        if rows:
            return rows
        return self.store.find_papers_by_method(method)

    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        catalog = self._entity_catalog()
        resolver = self._resolver()
        canonical = resolver.resolve_query_name(task, "task", catalog)
        rows = self.store.find_papers_by_task(canonical)
        if rows:
            return rows
        return self.store.find_papers_by_task(task)

    def find_limitations(
        self,
        topic: str = "",
        paper_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if paper_id:
            paper = self.get_paper(paper_id)
            if not paper:
                return self._paper_not_found_error(paper_id)
            pid = paper.get("paper_id")
            items = []
            for lim in paper.get("limitations") or []:
                if isinstance(lim, dict):
                    items.append({
                        "paper_id": pid,
                        "title": paper.get("title"),
                        "limitation": lim.get("limitation", lim.get("text", "")),
                        "text": lim.get("text", lim.get("limitation", "")),
                        "page": lim.get("page"),
                        "section": lim.get("section"),
                        "evidence_text": lim.get("evidence_text", ""),
                    })
                else:
                    items.append({
                        "paper_id": pid,
                        "title": paper.get("title"),
                        "limitation": str(lim),
                        "text": str(lim),
                    })
            return {"limitations": items, "paper_id": pid}
        items = self.store.find_limitations(topic)
        return {"limitations": items, "topic": topic}

    def get_evidence_for_claim(self, claim_id: str) -> Dict[str, Any]:
        evidence = self.store.get_evidence_for_claim(claim_id)
        if not evidence:
            return {"error": f"Claim not found: {claim_id}"}
        return evidence

    def compare_papers(self, paper_ids: List[str]) -> Dict[str, Any]:
        resolved = [self._resolve_paper_id(pid) for pid in paper_ids]
        rows = self.store.compare_papers(resolved)
        result: Dict[str, Any] = {"papers": rows, "markdown_table": comparison_markdown(rows)}
        found = {str(row.get("paper_id")) for row in rows}
        missing = [
            original
            for original, res in zip(paper_ids, resolved)
            if res not in found and original not in found
        ]
        if missing:
            result["missing_ids"] = missing
            result["hint"] = (
                "Some paper_ids were not found and are excluded from the comparison. "
                "Call search_papers to obtain valid paper_id values."
            )
        return result

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
        resolved = self._resolve_paper_id(paper_id)
        paper = self.get_paper(resolved)
        if not paper:
            return self._paper_not_found_error(paper_id)
        neighbors = self.store.get_paper_neighbors(
            resolved,
            relationships=relationships,
            include_summary=include_summary,
        )
        return {
            "paper_id": resolved,
            "title": paper.get("title"),
            "neighbors": neighbors,
            "count": len(neighbors),
        }

    def expand_paper_graph(
        self,
        paper_id: str,
        hops: int = 2,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> Dict[str, Any]:
        resolved = self._resolve_paper_id(paper_id)
        paper = self.get_paper(resolved)
        if not paper:
            return self._paper_not_found_error(paper_id)
        neighbors = self.store.expand_paper_graph(
            resolved,
            hops=hops,
            relationships=relationships,
            include_summary=include_summary,
        )
        return {
            "paper_id": resolved,
            "title": paper.get("title"),
            "hops": hops,
            "papers": neighbors,
            "count": len(neighbors),
        }

    def explore_paper_graph(
        self,
        paper_id: str,
        hops: int = 1,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> Dict[str, Any]:
        resolved = self._resolve_paper_id(paper_id)
        paper = self.get_paper(resolved)
        if not paper:
            return self._paper_not_found_error(paper_id)

        if hops <= 1:
            neighbors = self.store.get_paper_neighbors(
                resolved,
                relationships=relationships,
                include_summary=include_summary,
            )
            nodes = []
            for n in neighbors:
                item = dict(n)
                item.setdefault("hop", 1)
                nodes.append(item)
        else:
            expanded = self.store.expand_paper_graph(
                resolved,
                hops=hops,
                relationships=relationships,
                include_summary=include_summary,
            )
            nodes = []
            for n in expanded:
                item = dict(n)
                item.setdefault("hop", int(item.get("hop") or 1))
                nodes.append(item)

        return {
            "paper_id": resolved,
            "title": paper.get("title"),
            "hops": hops,
            "nodes": nodes,
            "count": len(nodes),
        }

    def search_papers(
        self,
        query: str,
        top_k: int = 10,
        center_paper_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        center = self._resolve_paper_id(center_paper_id) if center_paper_id else None
        return hybrid_search_papers(
            self,
            query,
            top_k=top_k,
            center_paper_id=center,
            litgraph_dir=self.litgraph_dir,
            workspace_id=self.workspace_id,
        )

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
