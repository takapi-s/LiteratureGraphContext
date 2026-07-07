"""Neo4j graph store (optional backend)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from litgraph.graph.graph_store import GraphQueryInterface
from litgraph.graph.kuzu_store import REL_EXPORT_QUERIES
from litgraph.query.comparison import build_comparison_rows, build_literature_matrix_rows
from litgraph.utils.ids import claim_id, entity_id, evidence_id, limitation_id


class Neo4jGraphStore(GraphQueryInterface):
    def __init__(self, config: Dict[str, Any]) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise ImportError("Install neo4j: pip install 'literature-graph[neo4j]'") from exc

        uri = config.get("uri") or "bolt://localhost:7687"
        user = config.get("user") or "neo4j"
        password = config.get("password") or ""
        database = config.get("database") or "neo4j"
        self._database = database
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def _run(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self._driver.session(database=self._database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def _run_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        with self._driver.session(database=self._database) as session:
            session.run(query, params or {})

    def initialize_schema(self) -> None:
        constraints = [
            "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT venue_id IF NOT EXISTS FOR (v:Venue) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT method_id IF NOT EXISTS FOR (m:Method) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT metric_id IF NOT EXISTS FOR (m:Metric) REQUIRE m.id IS UNIQUE",
        ]
        for stmt in constraints:
            try:
                self._run_write(stmt)
            except Exception:
                pass

    def clear(self) -> None:
        self._run_write("MATCH (n) DETACH DELETE n")

    def _upsert_authors_and_venue(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        authors = metadata.get("authors") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(";") if a.strip()]
        for author in authors:
            aid = entity_id("author", author)
            self._run_write(
                "MERGE (a:Author {id: $id}) SET a.name = $name "
                "WITH a MATCH (p:Paper {id: $pid}) MERGE (p)-[:AUTHORED_BY]->(a)",
                {"id": aid, "name": author, "pid": paper_id},
            )
        venue = metadata.get("venue") or ""
        if venue:
            vid = entity_id("venue", venue)
            self._run_write(
                "MERGE (v:Venue {id: $id}) SET v.name = $name "
                "WITH v MATCH (p:Paper {id: $pid}) MERGE (p)-[:PUBLISHED_IN]->(v)",
                {"id": vid, "name": venue, "pid": paper_id},
            )

    def upsert_paper_metadata(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        authors = metadata.get("authors") or []
        authors_str = "; ".join(authors) if isinstance(authors, list) else str(authors)
        self._run_write(
            """
            MERGE (p:Paper {id: $id})
            SET p.authors = $authors, p.venue = $venue, p.doi = $doi,
                p.title = coalesce($title, $id), p.year = $year, p.metadata_only = false
            """,
            {
                "id": paper_id,
                "authors": authors_str,
                "venue": metadata.get("venue") or "",
                "doi": metadata.get("doi") or "",
                "title": metadata.get("title") or paper_id,
                "year": metadata.get("year") if metadata.get("year") is not None else -1,
            },
        )
        self._upsert_authors_and_venue(paper_id, metadata)

    def upsert_bib_only_paper(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        authors = metadata.get("authors") or []
        authors_str = "; ".join(authors) if isinstance(authors, list) else str(authors)
        self._run_write(
            """
            MERGE (p:Paper {id: $id})
            SET p.title = $title, p.year = $year, p.authors = $authors,
                p.venue = $venue, p.doi = $doi, p.metadata_only = true
            """,
            {
                "id": paper_id,
                "title": metadata.get("title") or paper_id,
                "year": metadata.get("year") if metadata.get("year") is not None else -1,
                "authors": authors_str,
                "venue": metadata.get("venue") or "",
                "doi": metadata.get("doi") or "",
            },
        )
        self._upsert_authors_and_venue(paper_id, metadata)

    def upsert_cites_edge(self, citing_id: str, cited_id: str) -> None:
        self._run_write(
            "MATCH (a:Paper {id: $from}), (b:Paper {id: $to}) MERGE (a)-[:CITES]->(b)",
            {"from": citing_id, "to": cited_id},
        )

    def upsert_paper_relationship(self, from_id: str, to_id: str, rel_type: str) -> None:
        allowed = {"CONTRASTS_WITH", "EXTENDS", "CITES"}
        if rel_type not in allowed:
            raise ValueError(f"Unsupported relationship: {rel_type}")
        self._run_write(
            f"MATCH (a:Paper {{id: $from}}), (b:Paper {{id: $to}}) MERGE (a)-[:{rel_type}]->(b)",
            {"from": from_id, "to": to_id},
        )

    def upsert_paper_graph(self, extraction: Dict[str, Any]) -> None:
        pid = extraction["paper_id"]
        self._run_write(
            "MERGE (p:Paper {id: $id}) SET p.title = $title, p.year = $year, p.metadata_only = false",
            {"id": pid, "title": extraction.get("title") or pid, "year": extraction.get("year") or -1},
        )
        for task in extraction.get("tasks", []):
            tid = entity_id("task", task)
            self._run_write(
                "MERGE (t:Task {id: $id}) SET t.name = $name "
                "WITH t MATCH (p:Paper {id: $pid}) MERGE (p)-[:TARGETS]->(t)",
                {"id": tid, "name": task, "pid": pid},
            )
        for method in extraction.get("methods", []):
            mid = entity_id("method", method)
            self._run_write(
                "MERGE (m:Method {id: $id}) SET m.name = $name "
                "WITH m MATCH (p:Paper {id: $pid}) MERGE (p)-[:USES]->(m)",
                {"id": mid, "name": method, "pid": pid},
            )
        for dataset in extraction.get("datasets", []):
            did = entity_id("dataset", dataset)
            self._run_write(
                "MERGE (d:Dataset {id: $id}) SET d.name = $name "
                "WITH d MATCH (p:Paper {id: $pid}) MERGE (p)-[:EVALUATES_ON]->(d)",
                {"id": did, "name": dataset, "pid": pid},
            )
        for metric in extraction.get("metrics", []):
            met_id = entity_id("metric", metric)
            self._run_write(
                "MERGE (m:Metric {id: $id}) SET m.name = $name "
                "WITH m MATCH (p:Paper {id: $pid}) MERGE (p)-[:EVALUATES_WITH]->(m)",
                {"id": met_id, "name": metric, "pid": pid},
            )
        self._upsert_evidence_items(extraction, "claims", "Claim", "HAS_CLAIM", "claim", "SUPPORTED_BY")
        self._upsert_evidence_items(
            extraction, "contributions", "Contribution", "HAS_CONTRIBUTION", "contribution",
            "CONTRIBUTION_SUPPORTED_BY",
        )
        self._upsert_evidence_items(
            extraction, "limitations", "Limitation", "HAS_LIMITATION", "limitation",
            "LIMITATION_SUPPORTED_BY",
        )

    def _upsert_evidence_items(
        self, extraction: Dict[str, Any], field: str, label: str, rel: str, kind: str, evidence_rel: str,
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
            self._run_write(
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
            self._run_write(
                f"MATCH (p:Paper {{id: $pid}}), (n:{label} {{id: $nid}}) MERGE (p)-[:{rel}]->(n)",
                {"pid": pid, "nid": node_id},
            )
            eid = evidence_id(pid, kind, i)
            self._run_write(
                "MERGE (e:Evidence {id: $id}) SET e.text = $text, e.paper_id = $paper_id, "
                "e.page = $page, e.section = $section",
                {
                    "id": eid,
                    "text": item.get("evidence_text", ""),
                    "paper_id": pid,
                    "page": int(item.get("page", 1)),
                    "section": item.get("section", ""),
                },
            )
            self._run_write(
                f"MATCH (n:{label} {{id: $nid}}), (e:Evidence {{id: $eid}}) MERGE (n)-[:{evidence_rel}]->(e)",
                {"nid": node_id, "eid": eid},
            )

    def list_papers(self) -> List[Dict[str, Any]]:
        return self._run(
            "MATCH (p:Paper) RETURN p.id AS paper_id, p.title AS title, p.year AS year, "
            "p.authors AS authors, p.venue AS venue, p.doi AS doi, p.metadata_only AS metadata_only "
            "ORDER BY p.title"
        )

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        rows = self._run(
            "MATCH (p:Paper {id: $id}) RETURN p.id AS paper_id, p.title AS title, p.year AS year, "
            "p.authors AS authors, p.venue AS venue, p.doi AS doi, p.metadata_only AS metadata_only",
            {"id": paper_id},
        )
        if not rows:
            return None
        paper = rows[0]
        paper["methods"] = [r["name"] for r in self._run(
            "MATCH (p:Paper {id: $id})-[:USES]->(m:Method) RETURN m.name AS name", {"id": paper_id}
        )]
        paper["tasks"] = [r["name"] for r in self._run(
            "MATCH (p:Paper {id: $id})-[:TARGETS]->(t:Task) RETURN t.name AS name", {"id": paper_id}
        )]
        paper["datasets"] = [r["name"] for r in self._run(
            "MATCH (p:Paper {id: $id})-[:EVALUATES_ON]->(d:Dataset) RETURN d.name AS name", {"id": paper_id}
        )]
        paper["metrics"] = [r["name"] for r in self._run(
            "MATCH (p:Paper {id: $id})-[:EVALUATES_WITH]->(m:Metric) RETURN m.name AS name", {"id": paper_id}
        )]
        paper["contributions"] = self._run(
            "MATCH (p:Paper {id: $id})-[:HAS_CONTRIBUTION]->(c:Contribution) "
            "RETURN c.text AS text, c.page AS page, c.section AS section, c.evidence_text AS evidence_text",
            {"id": paper_id},
        )
        paper["limitations"] = self._run(
            "MATCH (p:Paper {id: $id})-[:HAS_LIMITATION]->(l:Limitation) "
            "RETURN l.id AS limitation_id, l.text AS limitation, l.text AS text, "
            "l.page AS page, l.section AS section, l.evidence_text AS evidence_text",
            {"id": paper_id},
        )
        return paper

    def _papers_for_compare(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        return [p for pid in paper_ids if (p := self.get_paper(pid))]

    def find_papers_by_method(self, method: str) -> List[Dict[str, Any]]:
        return self._run(
            "MATCH (p:Paper)-[:USES]->(m:Method) WHERE toLower(m.name) CONTAINS toLower($q) "
            "RETURN p.id AS paper_id, p.title AS title, m.name AS method",
            {"q": method},
        )

    def find_papers_by_task(self, task: str) -> List[Dict[str, Any]]:
        return self._run(
            "MATCH (p:Paper)-[:TARGETS]->(t:Task) WHERE toLower(t.name) CONTAINS toLower($q) "
            "RETURN p.id AS paper_id, p.title AS title, t.name AS task",
            {"q": task},
        )

    def find_limitations(self, topic: str) -> List[Dict[str, Any]]:
        return self._run(
            """
            MATCH (p:Paper)-[:HAS_LIMITATION]->(l:Limitation)
            WHERE toLower(l.text) CONTAINS toLower($q) OR toLower(l.evidence_text) CONTAINS toLower($q)
            RETURN p.id AS paper_id, p.title AS title, l.text AS limitation,
                   l.page AS page, l.section AS section, l.evidence_text AS evidence_text
            """,
            {"q": topic},
        )

    def get_evidence_for_claim(self, claim_id_val: str) -> Optional[Dict[str, Any]]:
        rows = self._run(
            """
            MATCH (c:Claim {id: $id})-[:SUPPORTED_BY]->(e:Evidence)
            OPTIONAL MATCH (p:Paper {id: c.paper_id})
            RETURN c.id AS claim_id, c.text AS claim, c.paper_id AS paper_id,
                   p.title AS title, e.page AS page, e.section AS section, e.text AS evidence_text
            """,
            {"id": claim_id_val},
        )
        return rows[0] if rows else None

    def compare_papers(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        return build_comparison_rows(self._papers_for_compare(paper_ids))

    def build_literature_matrix(self, topic: str) -> List[Dict[str, Any]]:
        all_ids = [p["paper_id"] for p in self.list_papers()]
        return build_literature_matrix_rows(topic, self._papers_for_compare(all_ids))

    def get_paper_neighbors(
        self,
        paper_id: str,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> List[Dict[str, Any]]:
        rels = relationships or ["CITES", "CITED_BY", "CONTRASTS_WITH", "EXTENDS", "EXTENDED_BY"]
        neighbors: List[Dict[str, Any]] = []
        seen: set = set()

        def add_neighbor(other_id: str, title: str, relationship: str, direction: str) -> None:
            key = (other_id, relationship, direction)
            if key in seen or other_id == paper_id:
                return
            seen.add(key)
            entry: Dict[str, Any] = {
                "paper_id": other_id,
                "title": title,
                "relationship": relationship,
                "direction": direction,
            }
            if include_summary:
                full = self.get_paper(other_id)
                if full:
                    entry["tasks"] = full.get("tasks", [])
                    entry["methods"] = full.get("methods", [])
                    entry["limitation_count"] = len(full.get("limitations") or [])
            neighbors.append(entry)

        if "CITES" in rels:
            for row in self._run(
                "MATCH (p:Paper {id: $id})-[:CITES]->(n:Paper) RETURN n.id AS paper_id, n.title AS title",
                {"id": paper_id},
            ):
                add_neighbor(row["paper_id"], row.get("title", ""), "CITES", "out")

        if "CITED_BY" in rels:
            for row in self._run(
                "MATCH (n:Paper)-[:CITES]->(p:Paper {id: $id}) RETURN n.id AS paper_id, n.title AS title",
                {"id": paper_id},
            ):
                add_neighbor(row["paper_id"], row.get("title", ""), "CITED_BY", "in")

        if "CONTRASTS_WITH" in rels:
            for row in self._run(
                "MATCH (p:Paper {id: $id})-[:CONTRASTS_WITH]-(n:Paper) RETURN n.id AS paper_id, n.title AS title",
                {"id": paper_id},
            ):
                add_neighbor(row["paper_id"], row.get("title", ""), "CONTRASTS_WITH", "undirected")

        if "EXTENDS" in rels:
            for row in self._run(
                "MATCH (p:Paper {id: $id})-[:EXTENDS]->(n:Paper) RETURN n.id AS paper_id, n.title AS title",
                {"id": paper_id},
            ):
                add_neighbor(row["paper_id"], row.get("title", ""), "EXTENDS", "out")

        if "EXTENDED_BY" in rels:
            for row in self._run(
                "MATCH (n:Paper)-[:EXTENDS]->(p:Paper {id: $id}) RETURN n.id AS paper_id, n.title AS title",
                {"id": paper_id},
            ):
                add_neighbor(row["paper_id"], row.get("title", ""), "EXTENDED_BY", "in")

        return neighbors

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
            for row in self._run(f"MATCH (n:{label}) RETURN {cols}"):
                nodes.append({"type": label, **row})
        edges: List[Dict[str, Any]] = []
        for rel, from_label, to_label in REL_EXPORT_QUERIES:
            try:
                for row in self._run(
                    f"MATCH (a:{from_label})-[:{rel}]->(b:{to_label}) RETURN a.id AS source, b.id AS target"
                ):
                    edges.append({"type": rel, "source": row["source"], "target": row["target"]})
            except Exception:
                continue
        return {"nodes": nodes, "edges": edges}

    def delete_paper(self, paper_id: str) -> None:
        for label in ("Claim", "Contribution", "Limitation", "Evidence"):
            self._run(
                f"MATCH (n:{label}) WHERE n.paper_id = $id DETACH DELETE n",
                {"id": paper_id},
            )
        self._run("MATCH (p:Paper {id: $id}) DETACH DELETE p", {"id": paper_id})

    def close(self) -> None:
        self._driver.close()
