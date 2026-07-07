"""Related work outline generation from the literature graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def _group_by_task(papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        tasks = paper.get("tasks") or ["General"]
        if not tasks:
            tasks = ["General"]
        for task in tasks:
            groups[task].append(paper)
    return dict(groups)


def _papers_matching_topic(papers: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
    q = topic.lower()
    matched = []
    for paper in papers:
        haystacks = [
            paper.get("title", ""),
            " ".join(paper.get("tasks") or []),
            " ".join(paper.get("methods") or []),
            " ".join(paper.get("datasets") or []),
        ]
        for lim in paper.get("limitations") or []:
            if isinstance(lim, dict):
                haystacks.append(lim.get("text", lim.get("limitation", "")))
            else:
                haystacks.append(str(lim))
        if q in " ".join(haystacks).lower():
            matched.append(paper)
    return matched if matched else papers


def generate_related_work_outline(
    topic: str,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a related-work section outline grouped by research task."""
    relevant = _papers_matching_topic(papers, topic)
    task_groups = _group_by_task(relevant)
    sections: List[Dict[str, Any]] = []
    order = 1

    for task, group in sorted(task_groups.items(), key=lambda x: x[0].lower()):
        method_map: Dict[str, List[str]] = defaultdict(list)
        for paper in group:
            methods = paper.get("methods") or ["unspecified method"]
            for method in methods:
                method_map[method].append(paper.get("paper_id", ""))
        sections.append({
            "order": order,
            "title": f"{task}",
            "papers": [
                {
                    "paper_id": p.get("paper_id"),
                    "title": p.get("title"),
                    "methods": p.get("methods", []),
                    "datasets": p.get("datasets", []),
                }
                for p in group
            ],
            "method_breakdown": dict(method_map),
        })
        order += 1

    limitation_papers = [
        p for p in relevant
        if p.get("limitations")
    ]
    if limitation_papers:
        sections.append({
            "order": order,
            "title": "Limitations of existing studies",
            "papers": [
                {
                    "paper_id": p.get("paper_id"),
                    "title": p.get("title"),
                    "limitations": p.get("limitations", []),
                }
                for p in limitation_papers
            ],
        })
        order += 1

    sections.append({
        "order": order,
        "title": f"Positioning of the current study on {topic}",
        "papers": [],
        "note": "Use find_limitations and get_paper_neighbors with the connected agent to position your contribution.",
    })

    markdown_lines = ["## Related Work Outline", ""]
    for sec in sections:
        markdown_lines.append(f"{sec['order']}. {sec['title']}")
        for paper in sec.get("papers", []):
            pid = paper.get("paper_id", "")
            title = paper.get("title", pid)
            markdown_lines.append(f"   - {title} ({pid})")
        markdown_lines.append("")

    return {
        "topic": topic,
        "sections": sections,
        "markdown_outline": "\n".join(markdown_lines).strip(),
    }
