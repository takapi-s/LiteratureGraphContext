"""Transform LiteratureGraph export JSON into playground graph format."""

from __future__ import annotations

from typing import Any, Dict, List


def _display_name(node: Dict[str, Any]) -> str:
    for key in ("title", "name", "text"):
        value = node.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text[:80]
    return str(node.get("id", "unknown"))


def _node_size(node_type: str) -> int:
    if node_type == "Paper":
        return 8
    if node_type in {"Method", "Task", "Dataset"}:
        return 5
    if node_type in {"Claim", "Contribution", "Limitation"}:
        return 4
    return 2


def to_playground_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert export_graph_json() output to viewer schema."""
    raw_nodes = payload.get("nodes") or []
    raw_edges = payload.get("edges") or []

    nodes: List[Dict[str, Any]] = []
    paper_ids: List[str] = []

    for node in raw_nodes:
        node_type = str(node.get("type") or "Other")
        node_id = str(node["id"])
        display = _display_name(node)
        paper_id = str(node.get("paper_id") or "")
        if node_type == "Paper":
            paper_id = node_id
            paper_ids.append(node_id)
        group = paper_id or node_type.lower()
        nodes.append(
            {
                "id": node_id,
                "name": display,
                "label": display,
                "type": node_type,
                "file": f"papers/{group}" if group else "",
                "val": _node_size(node_type),
                "properties": node,
            }
        )

    links: List[Dict[str, Any]] = []
    for idx, edge in enumerate(raw_edges):
        links.append(
            {
                "id": f"{edge.get('source')}-{edge.get('type')}-{edge.get('target')}-{idx}",
                "source": str(edge["source"]),
                "target": str(edge["target"]),
                "type": str(edge.get("type") or "RELATED").upper(),
            }
        )

    files = sorted({f"papers/{pid}" for pid in paper_ids})
    return {
        "nodes": nodes,
        "links": links,
        "files": files,
        "fileContents": {},
        "metadata": {
            "repo": "literature-graph",
            "generator": "literature-graph-context",
        },
    }
