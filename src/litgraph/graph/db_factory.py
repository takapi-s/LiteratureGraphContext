"""Graph database factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.graph.graph_store import GraphQueryInterface
from litgraph.graph.kuzu_store import KuzuGraphStore


def get_graph_store(
    db_path: Path,
    backend: Optional[str] = None,
    neo4j_config: Optional[Dict[str, Any]] = None,
) -> GraphQueryInterface:
    """Return a graph store for the configured backend."""
    name = (backend or "kuzu").strip().lower()
    if name == "neo4j":
        from litgraph.graph.neo4j_store import Neo4jGraphStore

        return Neo4jGraphStore(neo4j_config or {})
    return KuzuGraphStore(db_path)
