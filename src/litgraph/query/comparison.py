"""Paper comparison helpers."""

from __future__ import annotations

from typing import Any, Dict, List


def _join_evidence(items: List[Dict[str, Any]], text_key: str = "text") -> List[Dict[str, Any]]:
    out = []
    for item in items:
        if isinstance(item, str):
            out.append({"text": item, "evidence_text": item, "page": None, "section": None})
        else:
            out.append({
                "text": item.get(text_key, item.get("text", "")),
                "evidence_text": item.get("evidence_text", ""),
                "page": item.get("page"),
                "section": item.get("section"),
            })
    return out


def _summarize_difference(paper: Dict[str, Any], others: List[Dict[str, Any]]) -> str:
    diffs: List[str] = []
    my_methods = set(paper.get("methods") or [])
    my_datasets = set(paper.get("datasets") or [])
    my_metrics = set(paper.get("metrics") or [])
    other_methods: set[str] = set()
    other_datasets: set[str] = set()
    other_metrics: set[str] = set()
    for o in others:
        other_methods.update(o.get("methods") or [])
        other_datasets.update(o.get("datasets") or [])
        other_metrics.update(o.get("metrics") or [])

    unique_methods = my_methods - other_methods
    unique_datasets = my_datasets - other_datasets
    unique_metrics = my_metrics - other_metrics
    if unique_methods:
        diffs.append(f"methods: {', '.join(sorted(unique_methods))}")
    if unique_datasets:
        diffs.append(f"datasets: {', '.join(sorted(unique_datasets))}")
    if unique_metrics:
        diffs.append(f"metrics: {', '.join(sorted(unique_metrics))}")
    if not diffs:
        return "Similar profile to other papers in this set"
    return "; ".join(diffs)


def build_comparison_rows(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build full comparison rows with metrics, contributions, and differences."""
    rows: List[Dict[str, Any]] = []
    for paper in papers:
        pid = paper.get("paper_id")
        others = [p for p in papers if p.get("paper_id") != pid]
        contributions = _join_evidence(paper.get("contributions") or [])
        limitations = _join_evidence(paper.get("limitations") or [], text_key="limitation")
        rows.append({
            "paper_id": pid,
            "title": paper.get("title"),
            "task": ", ".join(paper.get("tasks") or []),
            "method": ", ".join(paper.get("methods") or []),
            "dataset": ", ".join(paper.get("datasets") or []),
            "metric": ", ".join(paper.get("metrics") or []),
            "contributions": contributions,
            "contribution": "; ".join(c["text"] for c in contributions if c.get("text")),
            "limitations": limitations,
            "limitation": "; ".join(
                l.get("text", l.get("limitation", "")) for l in limitations if l.get("text") or l.get("limitation")
            ),
            "difference": _summarize_difference(paper, others),
        })
    return rows


def comparison_markdown(rows: List[Dict[str, Any]]) -> str:
    header = (
        "| Paper | Task | Method | Dataset | Metric | Contribution | Limitation | Difference |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in rows:
        title = r.get("title", r.get("paper_id", ""))
        lines.append(
            f"| {title} | {r.get('task', '')} | {r.get('method', '')} | {r.get('dataset', '')} | "
            f"{r.get('metric', '')} | {r.get('contribution', '')} | {r.get('limitation', '')} | "
            f"{r.get('difference', '')} |"
        )
    return header + "\n".join(lines)


def build_literature_matrix_rows(topic: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter papers relevant to a topic and return matrix rows."""
    q = topic.lower()
    matched: List[Dict[str, Any]] = []
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
        blob = " ".join(haystacks).lower()
        if q in blob:
            matched.append(paper)
    return build_comparison_rows(matched)
