"""KuzuDB graph store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import kuzu

from litgraph.graph.graph_store import GraphQueryInterface
from litgraph.utils.ids import claim_id, entity_id, evidence_id, limitation_id


class KuzuGraphStore(GraphQueryInterface):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: Optional[kuzu.Database] = None
        self._conn: Optional[kuzu.Connection] = None

    def _connect(self) -> kuzu.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = kuzu.Database(str(self.db_path))
            self._conn = kuzu.Connection(self._db)
        return self._conn

    def _execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        conn = self._connect()
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def initialize_schema(self) -> None:
        statements = [
            "CREATE NODE TABLE IF NOT EXISTS Paper(id STRING PRIMARY KEY, title STRING, year INT64)",
            "CREATE NODE TABLE IF NOT EXISTS Task(id STRING PRIMARY KEY, name STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Method(id STRING PRIMARY KEY, name STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Dataset(id STRING PRIMARY KEY, name STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Metric(id STRING PRIMARY KEY, name STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Claim(id STRING PRIMARY KEY, text STRING, paper_id STRING, page INT64, section STRING, evidence_text STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Contribution(id STRING PRIMARY KEY, text STRING, paper_id STRING, page INT64, section STRING, evidence_text STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Limitation(id STRING PRIMARY KEY, text STRING, paper_id STRING, page INT64, section STRING, evidence_text STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Evidence(id STRING PRIMARY KEY, text STRING, paper_id STRING, page INT64, section STRING)",
            "CREATE REL TABLE IF NOT EXISTS TARGETS(FROM Paper TO Task)",
            "CREATE REL TABLE IF NOT EXISTS USES(FROM Paper TO Method)",
            "CREATE REL TABLE IF NOT EXISTS EVALUATES_ON(FROM Paper TO Dataset)",
            "CREATE REL TABLE IF NOT EXISTS EVALUATES_WITH(FROM Paper TO Metric)",
            "CREATE REL TABLE IF NOT EXISTS HAS_CLAIM(FROM Paper TO Claim)",
            "CREATE REL TABLE IF NOT EXISTS HAS_CONTRIBUTION(FROM Paper TO Contribution)",
            "CREATE REL TABLE IF NOT EXISTS HAS_LIMITATION(FROM Paper TO Limitation)",
            "CREATE REL TABLE IF NOT EXISTS SUPPORTED_BY(FROM Claim TO Evidence)",
            "CREATE REL TABLE IF NOT EXISTS LIMITATION_SUPPORTED_BY(FROM Limitation TO Evidence)",
            "CREATE REL TABLE IF NOT EXISTS CONTRIBUTION_SUPPORTED_BY(FROM Contribution TO Evidence)",
        ]
        for stmt in statements:
            try:
                self._execute(stmt)
            except Exception:
                pass
        for col, typ in [("authors", "STRING"), ("venue", "STRING"), ("doi", "STRING")]:
            try:
                self._execute(f"ALTER TABLE Paper ADD {col} {typ}")
            except Exception:
                pass

    def upsert_paper_metadata(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        self.initialize_schema()
        authors = "; ".join(metadata.get("authors") or [])
        venue = metadata.get("venue") or ""
        doi = metadata.get("doi") or ""
        title = metadata.get("title") or paper_id
        year = metadata.get("year") if metadata.get("year") is not None else -1
        self._execute(
            """
            MERGE (p:Paper {id: $id})
            SET p.authors = $authors, p.venue = $venue, p.doi = $doi
            """,
            {
                "id": paper_id,
                "authors": authors,
                "venue": venue,
                "doi": doi,
            },
        )
        if title and title != paper_id:
            self._execute(
                "MATCH (p:Paper {id: $id}) SET p.title = $title",
                {"id": paper_id, "title": title},
            )
        if year is not None and year != -1:
            self._execute(
                "MATCH (p:Paper {id: $id}) SET p.year = $year",
                {"id": paper_id, "year": year},
            )

    def clear(self) -> None:
        for table in [
            "TARGETS", "USES", "EVALUATES_ON", "EVALUATES_WITH",
            "HAS_CLAIM", "HAS_CONTRIBUTION", "HAS_LIMITATION",
            "SUPPORTED_BY", "LIMITATION_SUPPORTED_BY", "CONTRIBUTION_SUPPORTED_BY",
            "Paper", "Task", "Method", "Dataset", "Metric",
            "Claim", "Contribution", "Limitation", "Evidence",
        ]:
            try:
                self._execute(f"DROP TABLE IF EXISTS {table}")
            except Exception:
                pass
        self.initialize_schema()

    def upsert_paper_graph(self, extraction: Dict[str, Any]) -> None:
        self.initialize_schema()
        pid = extraction["paper_id"]
        title = extraction.get("title") or pid
        year = extraction.get("year") or -1
        self._execute(
            "MERGE (p:Paper {id: $id}) SET p.title = $title, p.year = $year",
            {"id": pid, "title": title, "year": year},
        )

        for task in extraction.get("tasks", []):
            tid = entity_id("task", task)
            self._execute("MERGE (t:Task {id: $id}) SET t.name = $name", {"id": tid, "name": task})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (t:Task {id: $tid}) MERGE (p)-[:TARGETS]->(t)",
                {"pid": pid, "tid": tid},
            )

        for method in extraction.get("methods", []):
            mid = entity_id("method", method)
            self._execute("MERGE (m:Method {id: $id}) SET m.name = $name", {"id": mid, "name": method})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (m:Method {id: $mid}) MERGE (p)-[:USES]->(m)",
                {"pid": pid, "mid": mid},
            )

        for dataset in extraction.get("datasets", []):
            did = entity_id("dataset", dataset)
            self._execute("MERGE (d:Dataset {id: $id}) SET d.name = $name", {"id": did, "name": dataset})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (d:Dataset {id: $did}) MERGE (p)-[:EVALUATES_ON]->(d)",
                {"pid": pid, "did": did},
            )

        for metric in extraction.get("metrics", []):
            met_id = entity_id("metric", metric)
            self._execute("MERGE (m:Metric {id: $id}) SET m.name = $name", {"id": met_id, "name": metric})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (m:Metric {id: $mid}) MERGE (p)-[:EVALUATES_WITH]->(m)",
                {"pid": pid, "mid": met_id},
            )

        self._upsert_evidence_items(extraction, "claims", "Claim", "HAS_CLAIM", "claim", evidence_rel="SUPPORTED_BY")
        self._upsert_evidence_items(extraction, "contributions", "Contribution", "HAS_CONTRIBUTION", "contribution", evidence_rel="CONTRIBUTION_SUPPORTED_BY")
        self._upsert_evidence_items(extraction, "limitations", "Limitation", "HAS_LIMITATION", "limitation", evidence_rel="LIMITATION_SUPPORTED_BY")

    def _upsert_evidence_items(
        self,
        extraction: Dict[str, Any],
        field: str,
        label: str,
        rel: str,
        kind: str,
        evidence_rel: str = "SUPPORTED_BY",
    ) -> None:
        pid = extraction["paper_id"]
        for i, item in enumerate(extraction.get(field, [])):
            if isinstance(item, str):
                item = {"text": item, "evidence_text": item, "page": 1, "section": "Unknown"}
            if field == "claims":
                node_id = claim_id(pid, i)
            elif field == "limitations":
                node_id = limitation_id(pid, i)
            else:
                node_id = f"{kind}_{pid}_{i:03d}"
            self._execute(
                f"MERGE (n:{label} {{id: $id}}) SET n.text = $text, n.paper_id = $paper_id, n.page = $page, n.section = $section, n.evidence_text = $evidence_text",
                {
                    "id": node_id,
                    "text": item.get("text", ""),
                    "paper_id": pid,
                    "page": int(item.get("page", 1)),
                    "section": item.get("section", ""),
                    "evidence_text": item.get("evidence_text", ""),
                },
            )
            self._execute(
                f"MATCH (p:Paper {{id: $pid}}), (n:{label} {{id: $nid}}) MERGE (p)-[:{rel}]->(n)",
                {"pid": pid, "nid": node_id},
            )
            eid = evidence_id(pid, kind, i)
            self._execute(
                "MERGE (e:Evidence {id: $id}) SET e.text = $text, e.paper_id = $paper_id, e.page = $page, e.section = $section",
                {
                    "id": eid,
                    "text": item.get("evidence_text", ""),
                    "paper_id": pid,
                    "page": int(item.get("page", 1)),
                    "section": item.get("section", ""),
                },
            )
            self._execute(
                f"MATCH (n:{label} {{id: $nid}}), (e:Evidence {{id: $eid}}) MERGE (n)-[:{evidence_rel}]->(e)",
                {"nid": node_id, "eid": eid},
            )

    def _rows(self, result: Any) -> List[Dict[str, Any]]:
        if hasattr(result, "rows_as_dict"):
            try:
                return list(result.rows_as_dict())
            except Exception:
                pass
        cols = result.get_column_names() if hasattr(result, "get_column_names") else []
        rows: List[Dict[str, Any]] = []
        while result.has_next():
            row = result.get_next()
            if isinstance(row, dict):
                rows.append(row)
            elif isinstance(row, list) and cols:
                rows.append(dict(zip(cols, row)))
            elif isinstance(row, list) and row:
                rows.append({"value": row[0]})
        return rows

    def list_papers(self) -> List[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper) RETURN p.id AS paper_id, p.title AS title, p.year AS year, "
            "p.authors AS authors, p.venue AS venue, p.doi AS doi ORDER BY p.title"
        )
        return self._rows(result)

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper {id: $id}) RETURN p.id AS paper_id, p.title AS title, p.year AS year, "
            "p.authors AS authors, p.venue AS venue, p.doi AS doi",
            {"id": paper_id},
        )
        rows = self._rows(result)
        if not rows:
            return None
        paper = rows[0]
        paper["methods"] = [r["name"] for r in self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:USES]->(m:Method) RETURN m.name AS name", {"id": paper_id}
        ))]
        paper["tasks"] = [r["name"] for r in self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:TARGETS]->(t:Task) RETURN t.name AS name", {"id": paper_id}
        ))]
        paper["datasets"] = [r["name"] for r in self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:EVALUATES_ON]->(d:Dataset) RETURN d.name AS name", {"id": paper_id}
        ))]
        paper["limitations"] = self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:HAS_LIMITATION]->(l:Limitation) RETURN l.id AS limitation_id, l.text AS limitation, l.page AS page, l.section AS section, l.evidence_text AS evidence_text",
            {"id": paper_id},
        ))
        return paper

    def find_papers_by_method(self, method: str) -> List[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper)-[:USES]->(m:Method) WHERE lower(m.name) CONTAINS lower($q) RETURN p.id AS paper_id, p.title AS title, m.name AS method",
            {"q": method},
        )
        return self._rows(result)

    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper)-[:TARGETS]->(t:Task) WHERE lower(t.name) CONTAINS lower($q) RETURN p.id AS paper_id, p.title AS title, t.name AS task",
            {"q": task},
        )
        return self._rows(result)

    def find_limitations(self, topic: str) -> List[Dict[str, Any]]:
        result = self._execute(
            """
            MATCH (p:Paper)-[:HAS_LIMITATION]->(l:Limitation)
            WHERE lower(l.text) CONTAINS lower($q) OR lower(l.evidence_text) CONTAINS lower($q)
            RETURN p.id AS paper_id, p.title AS title, l.text AS limitation,
                   l.page AS page, l.section AS section, l.evidence_text AS evidence_text
            """,
            {"q": topic},
        )
        return self._rows(result)

    def get_evidence_for_claim(self, claim_id_val: str) -> Optional[Dict[str, Any]]:
        result = self._execute(
            """
            MATCH (c:Claim {id: $id})-[:SUPPORTED_BY]->(e:Evidence)
            OPTIONAL MATCH (p:Paper {id: c.paper_id})
            RETURN c.id AS claim_id, c.text AS claim, c.paper_id AS paper_id,
                   p.title AS title, e.page AS page, e.section AS section, e.text AS evidence_text
            """,
            {"id": claim_id_val},
        )
        rows = self._rows(result)
        return rows[0] if rows else None

    def compare_papers(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        out = []
        for pid in paper_ids:
            paper = self.get_paper(pid)
            if paper:
                out.append({
                    "paper_id": paper.get("paper_id"),
                    "title": paper.get("title"),
                    "task": ", ".join(paper.get("tasks", [])),
                    "method": ", ".join(paper.get("methods", [])),
                    "dataset": ", ".join(paper.get("datasets", [])),
                    "limitation": "; ".join(l.get("limitation", l.get("text", "")) for l in paper.get("limitations", [])),
                })
        return out

    def export_graph_json(self) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        for label, fields in [
            ("Paper", ["id", "title", "year", "authors", "venue", "doi"]),
            ("Task", ["id", "name"]),
            ("Method", ["id", "name"]),
            ("Dataset", ["id", "name"]),
            ("Metric", ["id", "name"]),
            ("Claim", ["id", "text", "paper_id", "page", "section", "evidence_text"]),
            ("Contribution", ["id", "text", "paper_id", "page", "section", "evidence_text"]),
            ("Limitation", ["id", "text", "paper_id", "page", "section", "evidence_text"]),
            ("Evidence", ["id", "text", "paper_id", "page", "section"]),
        ]:
            cols = ", ".join(f"n.{f} AS {f}" for f in fields)
            result = self._execute(f"MATCH (n:{label}) RETURN {cols}")
            for row in self._rows(result):
                nodes.append({"type": label, **row})
        return {"nodes": nodes, "edges": []}

    def close(self) -> None:
        self._conn = None
        self._db = None


def get_graph_store(db_path: Path) -> GraphQueryInterface:
    return KuzuGraphStore(db_path)
