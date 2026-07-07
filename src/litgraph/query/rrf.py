"""Reciprocal rank fusion for hybrid search (pattern borrowed from Graphiti)."""

from __future__ import annotations

from collections import defaultdict
from typing import List, Sequence, Tuple, TypeVar

T = TypeVar("T")


def rrf(
    ranked_lists: Sequence[Sequence[T]],
    *,
    rank_const: int = 60,
    min_score: float = 0.0,
    key_fn=None,
) -> List[Tuple[T, float]]:
    """Merge ranked result lists with reciprocal rank fusion."""
    scores: dict[str, float] = defaultdict(float)
    item_by_key: dict[str, T] = {}

    for results in ranked_lists:
        for index, item in enumerate(results):
            item_key = key_fn(item) if key_fn else str(item)
            item_by_key[item_key] = item
            scores[item_key] += 1.0 / (index + rank_const)

    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    out: List[Tuple[T, float]] = []
    for item_key, score in ranked:
        if score < min_score:
            continue
        out.append((item_by_key[item_key], score))
    return out
