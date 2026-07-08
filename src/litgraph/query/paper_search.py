"""Cross-field paper search with keyword channels, embeddings, and RRF."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set

from litgraph.query.embedding_store import build_embedding_text, cosine_similarity, embed_texts, load_embeddings
from litgraph.query.rrf import rrf


def _tokenize(query: str) -> List[str]:
    return [t for t in re.split(r"\s+", query.lower().strip()) if t]


def _match_fields(paper: Dict[str, Any], query: str) -> List[str]:
    q = query.lower()
    fields: List[str] = []
    if q in (paper.get("title") or "").lower():
        fields.append("title")
    task_blob = " ".join(paper.get("tasks") or []).lower()
    if q in task_blob or any(tok in task_blob for tok in _tokenize(query)):
        fields.append("task")
    method_blob = " ".join(paper.get("methods") or []).lower()
    if q in method_blob or any(tok in method_blob for tok in _tokenize(query)):
        fields.append("method")
    lim_blob = " ".join(
        (lim.get("text", lim.get("limitation", "")) if isinstance(lim, dict) else str(lim))
        for lim in (paper.get("limitations") or [])
    ).lower()
    if q in lim_blob:
        fields.append("limitation")
    return fields


def _keyword_score(paper: Dict[str, Any], query: str) -> float:
    tokens = _tokenize(query)
    if not tokens:
        return 0.0
    blob = build_embedding_text(paper).lower()
    hits = sum(1 for tok in tokens if tok in blob)
    if hits == 0:
        return 0.0
    return hits / math.sqrt(len(tokens) * max(len(blob.split()), 1))


def _channel_method(finder: Any, query: str) -> List[Dict[str, Any]]:
    return finder.find_papers_by_method(query)


def _channel_task(finder: Any, query: str) -> List[Dict[str, Any]]:
    return finder.find_papers_by_task(query)


def _channel_matrix(finder: Any, query: str) -> List[Dict[str, Any]]:
    result = finder.build_literature_matrix(query)
    return result.get("papers", [])


def _channel_keyword_all(papers: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    scored = [(p, _keyword_score(p, query)) for p in papers]
    scored = [(p, s) for p, s in scored if s > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [p for p, _ in scored]


def _channel_embedding(
    papers: List[Dict[str, Any]],
    query: str,
    litgraph_dir,
) -> List[Dict[str, Any]]:
    store = load_embeddings(litgraph_dir)
    if not store:
        return []

    vectors = embed_texts([query])
    if not vectors:
        return []
    query_vec = vectors[0]

    scored: List[tuple[Dict[str, Any], float]] = []
    for paper in papers:
        pid = paper.get("paper_id")
        if not pid:
            continue
        vec = store.get(pid)
        if not vec:
            continue
        score = cosine_similarity(query_vec, vec)
        if score > 0:
            scored.append((paper, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [p for p, _ in scored]


def _graph_distance_boost(
    finder: Any,
    center_paper_id: str,
    paper_ids: List[str],
) -> Dict[str, float]:
    """Boost papers closer to center in the citation/extension graph."""
    if not center_paper_id:
        return {}
    expanded = finder.expand_paper_graph(center_paper_id, hops=2)
    boosts: Dict[str, float] = {}
    for item in expanded.get("papers", []):
        pid = item.get("paper_id")
        if not pid:
            continue
        hop = item.get("hop", 99)
        rel = item.get("relationship", "")
        weight = {"EXTENDS": 1.0, "CITED_BY": 0.8, "CITES": 0.7, "CONTRASTS_WITH": 0.6, "SHARED_METHOD": 0.4}.get(
            rel, 0.3
        )
        boosts[pid] = weight / max(hop, 1)
    return boosts


def search_papers(
    finder: Any,
    query: str,
    *,
    top_k: int = 10,
    center_paper_id: Optional[str] = None,
    litgraph_dir=None,
) -> Dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"query": query, "papers": [], "count": 0}

    all_papers: List[Dict[str, Any]] = []
    for row in finder.list_papers():
        pid = row.get("paper_id")
        if pid:
            full = finder.get_paper(pid)
            if full:
                all_papers.append(full)

    channels = [
        _channel_method(finder, query),
        _channel_task(finder, query),
        _channel_matrix(finder, query),
        _channel_keyword_all(all_papers, query),
    ]
    if litgraph_dir is not None:
        channels.append(_channel_embedding(all_papers, query, litgraph_dir))

    ranked_lists = []
    for channel in channels:
        ids = []
        seen: Set[str] = set()
        for paper in channel:
            pid = paper.get("paper_id")
            if pid and pid not in seen:
                seen.add(pid)
                ids.append(pid)
        if ids:
            ranked_lists.append(ids)

    merged = rrf(ranked_lists) if ranked_lists else []
    paper_by_id = {p["paper_id"]: p for p in all_papers if p.get("paper_id")}

    graph_boosts = _graph_distance_boost(finder, center_paper_id or "", [pid for pid, _ in merged])

    results: List[Dict[str, Any]] = []
    for pid, score in merged[: top_k * 2]:
        paper = paper_by_id.get(pid)
        if not paper:
            paper = finder.get_paper(pid)
        if not paper:
            continue
        fields = _match_fields(paper, query)
        final_score = score + graph_boosts.get(pid, 0.0)
        results.append({
            "paper_id": pid,
            "title": paper.get("title"),
            "score": round(final_score, 4),
            "match_fields": fields or ["keyword"],
            "match_reason": ", ".join(fields) if fields else "hybrid keyword/embedding match",
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    results = results[:top_k]
    return {"query": query, "papers": results, "count": len(results)}
