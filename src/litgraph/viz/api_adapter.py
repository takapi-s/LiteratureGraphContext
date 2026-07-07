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


def _paper_summaries(
    raw_nodes: List[Dict[str, Any]],
    raw_edges: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    paper_nodes = [n for n in raw_nodes if str(n.get("type")) == "Paper"]
    claim_counts: Dict[str, int] = {}
    limitation_counts: Dict[str, int] = {}

    for edge in raw_edges:
        rel = str(edge.get("type") or "")
        target = str(edge.get("target") or "")
        if rel == "HAS_CLAIM":
            for node in raw_nodes:
                if str(node.get("id")) == target:
                    pid = str(node.get("paper_id") or "")
                    if pid:
                        claim_counts[pid] = claim_counts.get(pid, 0) + 1
        elif rel == "HAS_LIMITATION":
            for node in raw_nodes:
                if str(node.get("id")) == target:
                    pid = str(node.get("paper_id") or "")
                    if pid:
                        limitation_counts[pid] = limitation_counts.get(pid, 0) + 1

    methods_by_paper: Dict[str, List[str]] = {}
    tasks_by_paper: Dict[str, List[str]] = {}
    for edge in raw_edges:
        rel = str(edge.get("type") or "")
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if rel == "USES":
            for node in raw_nodes:
                if str(node.get("id")) == target and str(node.get("type")) == "Method":
                    methods_by_paper.setdefault(source, []).append(str(node.get("name") or ""))
        elif rel == "TARGETS":
            for node in raw_nodes:
                if str(node.get("id")) == target and str(node.get("type")) == "Task":
                    tasks_by_paper.setdefault(source, []).append(str(node.get("name") or ""))

    summaries: List[Dict[str, Any]] = []
    for paper in sorted(paper_nodes, key=lambda p: str(p.get("title") or p.get("id"))):
        pid = str(paper.get("id") or "")
        summaries.append({
            "paper_id": pid,
            "title": paper.get("title") or pid,
            "year": paper.get("year"),
            "authors": paper.get("authors") or "",
            "venue": paper.get("venue") or "",
            "doi": paper.get("doi") or "",
            "methods": methods_by_paper.get(pid, []),
            "tasks": tasks_by_paper.get(pid, []),
            "claim_count": claim_counts.get(pid, 0),
            "limitation_count": limitation_counts.get(pid, 0),
        })
    return summaries


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
    papers = _paper_summaries(raw_nodes, raw_edges)
    return {
        "nodes": nodes,
        "links": links,
        "files": files,
        "papers": papers,
        "fileContents": {},
        "metadata": {
            "repo": "literature-graph",
            "generator": "literature-graph-context",
        },
    }
