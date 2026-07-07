"""Infer paper-to-paper relationships from the literature graph."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def infer_contrasts_and_extends(
    papers: List[Dict[str, Any]],
    cites_pairs: List[Tuple[str, str]],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Return (CONTRASTS_WITH pairs, EXTENDS pairs) using simple heuristics."""
    by_id = {p["paper_id"]: p for p in papers if p.get("paper_id")}
    contrasts: Set[Tuple[str, str]] = set()
    extends: Set[Tuple[str, str]] = set()

    ids = sorted(by_id.keys())
    for i, a_id in enumerate(ids):
        a = by_id[a_id]
        a_tasks = set(a.get("tasks") or [])
        a_methods = set(a.get("methods") or [])
        for b_id in ids[i + 1 :]:
            b = by_id[b_id]
            b_tasks = set(b.get("tasks") or [])
            b_methods = set(b.get("methods") or [])
            shared_tasks = a_tasks & b_tasks
            if shared_tasks and a_methods and b_methods and a_methods != b_methods:
                pair = tuple(sorted((a_id, b_id)))
                contrasts.add(pair)

    cites_set = set(cites_pairs)
    for citing, cited in cites_set:
        if citing not in by_id or cited not in by_id:
            continue
        c_tasks = set(by_id[citing].get("tasks") or [])
        p_tasks = set(by_id[cited].get("tasks") or [])
        c_methods = set(by_id[citing].get("methods") or [])
        p_methods = set(by_id[cited].get("methods") or [])
        if (c_tasks & p_tasks) and (c_methods >= p_methods or c_methods & p_methods):
            extends.add((citing, cited))

    return sorted(contrasts), sorted(extends)
