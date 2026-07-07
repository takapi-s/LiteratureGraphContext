"""KuzuDB graph store."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import kuzu

from litgraph.graph.graph_store import GraphQueryInterface
from litgraph.query.comparison import build_comparison_rows, build_literature_matrix_rows
from litgraph.utils.ids import claim_id, entity_id, evidence_id, limitation_id

REL_EXPORT_QUERIES: List[Tuple[str, str, str]] = [
    ("TARGETS", "Paper", "Task"),
    ("USES", "Paper", "Method"),
    ("EVALUATES_ON", "Paper", "Dataset"),
    ("EVALUATES_WITH", "Paper", "Metric"),
    ("HAS_CLAIM", "Paper", "Claim"),
    ("HAS_CONTRIBUTION", "Paper", "Contribution"),
    ("HAS_LIMITATION", "Paper", "Limitation"),
    ("SUPPORTED_BY", "Claim", "Evidence"),
    ("LIMITATION_SUPPORTED_BY", "Limitation", "Evidence"),
    ("CONTRIBUTION_SUPPORTED_BY", "Contribution", "Evidence"),
    ("AUTHORED_BY", "Paper", "Author"),
    ("PUBLISHED_IN", "Paper", "Venue"),
    ("CITES", "Paper", "Paper"),
    ("CONTRASTS_WITH", "Paper", "Paper"),
    ("EXTENDS", "Paper", "Paper"),
]


class KuzuGraphStore(GraphQueryInterface):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: Optional[kuzu.Database] = None
        self._conn: Optional[kuzu.Connection] = None

    def _connect(self) -> kuzu.Connection:
        if self._conn is not None:
            return self._conn
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._db = kuzu.Database(str(self.db_path))
            self._conn = kuzu.Connection(self._db)
        except RuntimeError as exc:
            if "Could not set lock" not in str(exc):
                raise
            from litgraph.utils.db_lock import release_db_lock

            stopped = release_db_lock(self.db_path)
            if not stopped:
                raise
            names = ", ".join(f"{proc.command}(pid={proc.pid})" for proc in stopped)
            print(f"Released Kuzu lock by stopping: {names}", file=sys.stderr)
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
            "CREATE NODE TABLE IF NOT EXISTS Author(id STRING PRIMARY KEY, name STRING)",
            "CREATE NODE TABLE IF NOT EXISTS Venue(id STRING PRIMARY KEY, name STRING)",
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
            "CREATE REL TABLE IF NOT EXISTS AUTHORED_BY(FROM Paper TO Author)",
            "CREATE REL TABLE IF NOT EXISTS PUBLISHED_IN(FROM Paper TO Venue)",
            "CREATE REL TABLE IF NOT EXISTS CITES(FROM Paper TO Paper)",
            "CREATE REL TABLE IF NOT EXISTS CONTRASTS_WITH(FROM Paper TO Paper)",
            "CREATE REL TABLE IF NOT EXISTS EXTENDS(FROM Paper TO Paper)",
        ]
        for stmt in statements:
            try:
                self._execute(stmt)
            except Exception:
                pass
        for col, typ in [("authors", "STRING"), ("venue", "STRING"), ("doi", "STRING"), ("metadata_only", "BOOL")]:
            try:
                self._execute(f"ALTER TABLE Paper ADD {col} {typ}")
            except Exception:
                pass

    def _upsert_authors_and_venue(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        authors = metadata.get("authors") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(";") if a.strip()]
        for author in authors:
            aid = entity_id("author", author)
            self._execute("MERGE (a:Author {id: $id}) SET a.name = $name", {"id": aid, "name": author})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (a:Author {id: $aid}) MERGE (p)-[:AUTHORED_BY]->(a)",
                {"pid": paper_id, "aid": aid},
            )
        venue = metadata.get("venue") or ""
        if venue:
            vid = entity_id("venue", venue)
            self._execute("MERGE (v:Venue {id: $id}) SET v.name = $name", {"id": vid, "name": venue})
            self._execute(
                "MATCH (p:Paper {id: $pid}), (v:Venue {id: $vid}) MERGE (p)-[:PUBLISHED_IN]->(v)",
                {"pid": paper_id, "vid": vid},
            )

    def upsert_paper_metadata(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        self.initialize_schema()
        authors = metadata.get("authors") or []
        if isinstance(authors, list):
            authors_str = "; ".join(authors)
        else:
            authors_str = str(authors)
        venue = metadata.get("venue") or ""
        doi = metadata.get("doi") or ""
        title = metadata.get("title") or paper_id
        year = metadata.get("year") if metadata.get("year") is not None else -1
        self._execute(
            """
            MERGE (p:Paper {id: $id})
            SET p.authors = $authors, p.venue = $venue, p.doi = $doi, p.metadata_only = false
            """,
            {"id": paper_id, "authors": authors_str, "venue": venue, "doi": doi},
        )
        if title and title != paper_id:
            self._execute("MATCH (p:Paper {id: $id}) SET p.title = $title", {"id": paper_id, "title": title})
        if year is not None and year != -1:
            self._execute("MATCH (p:Paper {id: $id}) SET p.year = $year", {"id": paper_id, "year": year})
        self._upsert_authors_and_venue(paper_id, metadata)

    def upsert_bib_only_paper(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        self.initialize_schema()
        title = metadata.get("title") or paper_id
        year = metadata.get("year") if metadata.get("year") is not None else -1
        authors = metadata.get("authors") or []
        authors_str = "; ".join(authors) if isinstance(authors, list) else str(authors)
        self._execute(
            """
            MERGE (p:Paper {id: $id})
            SET p.title = $title, p.year = $year, p.authors = $authors,
                p.venue = $venue, p.doi = $doi, p.metadata_only = true
            """,
            {
                "id": paper_id,
                "title": title,
                "year": year,
                "authors": authors_str,
                "venue": metadata.get("venue") or "",
                "doi": metadata.get("doi") or "",
            },
        )
        self._upsert_authors_and_venue(paper_id, metadata)

    def upsert_cites_edge(self, citing_id: str, cited_id: str) -> None:
        self.initialize_schema()
        self._execute(
            "MATCH (a:Paper {id: $from}), (b:Paper {id: $to}) MERGE (a)-[:CITES]->(b)",
            {"from": citing_id, "to": cited_id},
        )

    def upsert_paper_relationship(self, from_id: str, to_id: str, rel_type: str) -> None:
        allowed = {"CONTRASTS_WITH", "EXTENDS", "CITES"}
        if rel_type not in allowed:
            raise ValueError(f"Unsupported relationship: {rel_type}")
        self.initialize_schema()
        self._execute(
            f"MATCH (a:Paper {{id: $from}}), (b:Paper {{id: $to}}) MERGE (a)-[:{rel_type}]->(b)",
            {"from": from_id, "to": to_id},
        )

    def clear(self) -> None:
        for table in [
            "TARGETS", "USES", "EVALUATES_ON", "EVALUATES_WITH",
            "HAS_CLAIM", "HAS_CONTRIBUTION", "HAS_LIMITATION",
            "SUPPORTED_BY", "LIMITATION_SUPPORTED_BY", "CONTRIBUTION_SUPPORTED_BY",
            "AUTHORED_BY", "PUBLISHED_IN", "CITES", "CONTRASTS_WITH", "EXTENDS",
            "Paper", "Author", "Venue", "Task", "Method", "Dataset", "Metric",
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
            "MERGE (p:Paper {id: $id}) SET p.title = $title, p.year = $year, p.metadata_only = false",
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
        self._upsert_evidence_items(
            extraction, "contributions", "Contribution", "HAS_CONTRIBUTION", "contribution",
            evidence_rel="CONTRIBUTION_SUPPORTED_BY",
        )
        self._upsert_evidence_items(
            extraction, "limitations", "Limitation", "HAS_LIMITATION", "limitation",
            evidence_rel="LIMITATION_SUPPORTED_BY",
        )

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
                f"MERGE (n:{label} {{id: $id}}) SET n.text = $text, n.paper_id = $paper_id, "
                "n.page = $page, n.section = $section, n.evidence_text = $evidence_text",
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
            "p.authors AS authors, p.venue AS venue, p.doi AS doi, p.metadata_only AS metadata_only "
            "ORDER BY p.title"
        )
        return self._rows(result)

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper {id: $id}) RETURN p.id AS paper_id, p.title AS title, p.year AS year, "
            "p.authors AS authors, p.venue AS venue, p.doi AS doi, p.metadata_only AS metadata_only",
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
        paper["metrics"] = [r["name"] for r in self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:EVALUATES_WITH]->(m:Metric) RETURN m.name AS name", {"id": paper_id}
        ))]
        paper["contributions"] = self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:HAS_CONTRIBUTION]->(c:Contribution) "
            "RETURN c.text AS text, c.page AS page, c.section AS section, c.evidence_text AS evidence_text",
            {"id": paper_id},
        ))
        paper["limitations"] = self._rows(self._execute(
            "MATCH (p:Paper {id: $id})-[:HAS_LIMITATION]->(l:Limitation) "
            "RETURN l.id AS limitation_id, l.text AS limitation, l.text AS text, "
            "l.page AS page, l.section AS section, l.evidence_text AS evidence_text",
            {"id": paper_id},
        ))
        return paper

    def _papers_for_compare(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        papers = []
        for pid in paper_ids:
            paper = self.get_paper(pid)
            if paper:
                papers.append(paper)
        return papers

    def find_papers_by_method(self, method: str) -> List[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper)-[:USES]->(m:Method) WHERE lower(m.name) CONTAINS lower($q) "
            "RETURN p.id AS paper_id, p.title AS title, m.name AS method",
            {"q": method},
        )
        return self._rows(result)

    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        result = self._execute(
            "MATCH (p:Paper)-[:TARGETS]->(t:Task) WHERE lower(t.name) CONTAINS lower($q) "
            "RETURN p.id AS paper_id, p.title AS title, t.name AS task",
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
        return build_comparison_rows(self._papers_for_compare(paper_ids))

    def build_literature_matrix(self, topic: str) -> List[Dict[str, Any]]:
        all_ids = [p["paper_id"] for p in self.list_papers()]
        papers = self._papers_for_compare(all_ids)
        return build_literature_matrix_rows(topic, papers)

    def export_graph_json(self) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        for label, fields in [
            ("Paper", ["id", "title", "year", "authors", "venue", "doi", "metadata_only"]),
            ("Author", ["id", "name"]),
            ("Venue", ["id", "name"]),
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

        edges: List[Dict[str, Any]] = []
        for rel, from_label, to_label in REL_EXPORT_QUERIES:
            try:
                result = self._execute(
                    f"MATCH (a:{from_label})-[r:{rel}]->(b:{to_label}) RETURN a.id AS source, b.id AS target"
                )
                for row in self._rows(result):
                    edges.append({"type": rel, "source": row["source"], "target": row["target"]})
            except Exception:
                continue
        return {"nodes": nodes, "edges": edges}

    def delete_paper(self, paper_id: str) -> None:
        self.initialize_schema()
        for label in ("Claim", "Contribution", "Limitation", "Evidence"):
            try:
                self._execute(
                    f"MATCH (n:{label}) WHERE n.paper_id = $id DETACH DELETE n",
                    {"id": paper_id},
                )
            except Exception:
                pass
        try:
            self._execute("MATCH (p:Paper {id: $id}) DETACH DELETE p", {"id": paper_id})
        except Exception:
            pass

    def close(self) -> None:
        self._conn = None
        self._db = None
