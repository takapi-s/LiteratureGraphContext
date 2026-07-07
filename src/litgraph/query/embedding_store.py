"""Paper embedding index and cosine similarity search."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def embeddings_path(litgraph_dir: Path) -> Path:
    return litgraph_dir / "cache" / "embeddings.json"


def load_embeddings(litgraph_dir: Path) -> Dict[str, List[float]]:
    path = embeddings_path(litgraph_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): list(v) for k, v in (data or {}).items()}


def save_embeddings(litgraph_dir: Path, embeddings: Dict[str, List[float]]) -> None:
    path = embeddings_path(litgraph_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(embeddings, indent=2), encoding="utf-8")


def build_embedding_text(paper: Dict[str, Any]) -> str:
    parts = [
        paper.get("title") or "",
        " ".join(paper.get("tasks") or []),
        " ".join(paper.get("methods") or []),
        " ".join(paper.get("datasets") or []),
    ]
    for key in ("contributions", "limitations"):
        for item in paper.get(key) or []:
            if isinstance(item, dict):
                parts.append(item.get("text", item.get("limitation", "")))
            else:
                parts.append(str(item))
    return " ".join(p for p in parts if p).strip()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
    except Exception:
        return []


def index_paper_embeddings(
    litgraph_dir: Path,
    papers: List[Dict[str, Any]],
    *,
    model: str = "text-embedding-3-small",
) -> Dict[str, Any]:
    """Build or refresh paper-level embeddings for search."""
    if not os.getenv("OPENAI_API_KEY"):
        return {"indexed": 0, "skipped": len(papers), "reason": "OPENAI_API_KEY not set"}

    store = load_embeddings(litgraph_dir)
    to_index: List[tuple[str, str]] = []
    for paper in papers:
        pid = paper.get("paper_id")
        if not pid:
            continue
        text = build_embedding_text(paper)
        if text:
            to_index.append((pid, text))

    if not to_index:
        return {"indexed": 0, "skipped": 0}

    vectors = embed_texts([text for _, text in to_index], model=model)
    if not vectors:
        return {"indexed": 0, "skipped": len(to_index), "reason": "embedding API failed"}

    for (pid, _), vector in zip(to_index, vectors):
        store[pid] = vector
    save_embeddings(litgraph_dir, store)
    return {"indexed": len(vectors), "skipped": 0, "model": model}
