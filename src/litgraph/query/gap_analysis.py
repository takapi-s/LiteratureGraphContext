"""Research gap clustering from graph limitations."""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional


def _norm(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _limitation_matches_topic(item: Dict[str, Any], topic: str) -> bool:
    q = topic.lower()
    fields = [
        item.get("limitation", ""),
        item.get("text", ""),
        item.get("evidence_text", ""),
        item.get("title", ""),
    ]
    return any(q in str(f).lower() for f in fields if f)


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def cluster_limitations(
    items: List[Dict[str, Any]],
    threshold: float = 0.55,
) -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    for item in items:
        text = item.get("limitation") or item.get("text") or ""
        if not text.strip():
            continue
        placed = False
        for cluster in clusters:
            if _similarity(text, cluster["representative"]) >= threshold:
                cluster["items"].append(item)
                placed = True
                break
        if not placed:
            clusters.append({"representative": text, "items": [item]})
    clusters.sort(key=lambda c: len(c["items"]), reverse=True)
    return clusters


def _gap_summary(cluster: Dict[str, Any]) -> str:
    rep = cluster["representative"]
    count = len(cluster["items"])
    if count == 1:
        return rep
    return f"{rep} (reported across {count} papers)"


def find_research_gaps(
    topic: str,
    limitations: List[Dict[str, Any]],
    min_papers: int = 1,
    similarity_threshold: float = 0.55,
) -> Dict[str, Any]:
    """Cluster limitations into research gap candidates with evidence."""
    filtered = [lim for lim in limitations if _limitation_matches_topic(lim, topic)]
    clusters = cluster_limitations(filtered, threshold=similarity_threshold)
    gaps: List[Dict[str, Any]] = []
    for cluster in clusters:
        paper_ids = sorted({i.get("paper_id") for i in cluster["items"] if i.get("paper_id")})
        if len(paper_ids) < min_papers:
            continue
        evidence = [
            {
                "paper_id": i.get("paper_id"),
                "title": i.get("title"),
                "page": i.get("page"),
                "section": i.get("section"),
                "text": i.get("evidence_text") or i.get("limitation") or i.get("text"),
            }
            for i in cluster["items"]
        ]
        gaps.append({
            "gap": _gap_summary(cluster),
            "supporting_papers": paper_ids,
            "paper_count": len(paper_ids),
            "evidence": evidence,
        })
    return {"topic": topic, "gaps": gaps, "gap_count": len(gaps)}
