"""Semantic Scholar API client."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

S2_BASE = "https://api.semanticscholar.org/graph/v1"


def _headers() -> Dict[str, str]:
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        return {"x-api-key": api_key}
    return {}


def search_paper(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search papers by title or keyword."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,venue,externalIds,citationCount,referenceCount",
    }
    with httpx.Client(timeout=30.0, headers=_headers()) as client:
        resp = client.get(f"{S2_BASE}/paper/search", params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data") or []


def lookup_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """Fetch paper metadata by DOI."""
    with httpx.Client(timeout=30.0, headers=_headers()) as client:
        resp = client.get(
            f"{S2_BASE}/paper/DOI:{doi}",
            params={"fields": "title,year,authors,venue,externalIds,citationCount,references.paperId,references.title"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def enrich_metadata(title: str, doi: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return enriched metadata dict suitable for upsert_paper_metadata."""
    paper = None
    if doi:
        paper = lookup_by_doi(doi)
    if not paper and title:
        results = search_paper(title, limit=1)
        paper = results[0] if results else None
    if not paper:
        return None

    authors = [a.get("name", "") for a in paper.get("authors") or [] if a.get("name")]
    ext = paper.get("externalIds") or {}
    return {
        "title": paper.get("title") or title,
        "year": paper.get("year"),
        "authors": authors,
        "venue": paper.get("venue") or "",
        "doi": ext.get("DOI") or doi or "",
        "citation_count": paper.get("citationCount"),
        "semantic_scholar_id": paper.get("paperId"),
    }
