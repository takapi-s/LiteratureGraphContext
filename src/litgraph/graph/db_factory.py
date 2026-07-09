"""Graph database factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.graph.graph_store import GraphQueryInterface
from litgraph.graph.kuzu_store import KuzuGraphStore
from litgraph.utils.workspace import DEFAULT_WORKSPACE


def get_graph_store(
    db_path: Path,
    backend: Optional[str] = None,
    neo4j_config: Optional[Dict[str, Any]] = None,
    *,
    read_only: bool = False,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> GraphQueryInterface:
    """Return a graph store for the configured backend."""
    name = (backend or "kuzu").strip().lower()
    if name == "neo4j":
        from litgraph.graph.neo4j_store import Neo4jGraphStore

        return Neo4jGraphStore(neo4j_config or {}, workspace_id=workspace_id)
    return KuzuGraphStore(db_path, read_only=read_only, workspace_id=workspace_id)
