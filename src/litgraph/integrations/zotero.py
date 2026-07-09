"""Zotero Web API live sync."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

ZOTERO_API = "https://api.zotero.org"
SYNC_STATE_FILE = "zotero_sync_state.json"


def parse_zotero_json_export(path: Path) -> List[Dict[str, Any]]:
    """Parse a Zotero JSON export (File -> Export Library -> CSL JSON or Zotero JSON)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("items", [])
    entries: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        creators = item.get("creators") or []
        authors = []
        for c in creators:
            if c.get("creatorType") in (None, "author"):
                name = " ".join(p for p in (c.get("firstName"), c.get("lastName")) if p)
                if name:
                    authors.append(name)
        doi = ""
        for ident in item.get("identifiers") or []:
            if isinstance(ident, dict) and ident.get("identifierType") == "DOI":
                doi = ident.get("identifier", "")
        if not doi:
            doi = (item.get("DOI") or item.get("doi") or "")
        key = item.get("key") or item.get("id") or title[:40]
        entries.append({
            "bib_key": str(key),
            "entry_type": item.get("itemType", "article"),
            "title": title,
            "year": item.get("date", "")[:4] if item.get("date") else None,
            "authors": authors,
            "venue": item.get("publicationTitle") or item.get("bookTitle") or "",
            "doi": doi,
            "citations": "",
            "source_file": str(path),
            "source_stem": path.stem,
        })
    return entries


def _api_headers(api_key: str) -> Dict[str, str]:
    return {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3",
    }


def _item_to_entry(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = item.get("data") or item
    title = data.get("title") or ""
    if not title:
        return None
    creators = data.get("creators") or []
    authors = []
    for c in creators:
        if c.get("creatorType") in (None, "author"):
            name = " ".join(p for p in (c.get("firstName"), c.get("lastName")) if p)
            if name:
                authors.append(name)
    doi = data.get("DOI") or data.get("doi") or ""
    year_raw = data.get("date", "") or ""
    year = int(year_raw[:4]) if len(year_raw) >= 4 and year_raw[:4].isdigit() else None
    return {
        "bib_key": str(data.get("key") or data.get("itemKey") or title[:40]),
        "entry_type": data.get("itemType", "article"),
        "title": title,
        "year": year,
        "authors": authors,
        "venue": data.get("publicationTitle") or data.get("bookTitle") or "",
        "doi": doi,
        "citations": "",
        "source_file": "zotero_api",
        "source_stem": "zotero_api",
        "zotero_key": data.get("key") or data.get("itemKey"),
        "zotero_version": data.get("version") or item.get("version"),
    }


def fetch_library_items(
    user_id: str,
    api_key: str,
    collection_key: Optional[str] = None,
    since_version: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch items from Zotero Web API."""
    if collection_key:
        path = f"/users/{user_id}/collections/{collection_key}/items"
    else:
        path = f"/users/{user_id}/items"
    params: Dict[str, Any] = {"limit": limit, "itemType": "-attachment"}
    if since_version is not None:
        params["since"] = since_version

    entries: List[Dict[str, Any]] = []
    start = 0
    with httpx.Client(timeout=60.0, headers=_api_headers(api_key)) as client:
        while True:
            params["start"] = start
            resp = client.get(f"{ZOTERO_API}{path}", params=params)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            for item in batch:
                entry = _item_to_entry(item)
                if entry:
                    entries.append(entry)
            if len(batch) < limit:
                break
            start += limit
    return entries


def load_sync_state(cache_dir: Path) -> Dict[str, Any]:
    path = cache_dir / SYNC_STATE_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_sync_state(cache_dir: Path, state: Dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / SYNC_STATE_FILE
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def sync_zotero_library(
    bib_cache_dir: Path,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    collection_key: Optional[str] = None,
    full_sync: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sync Zotero library via Web API into bib cache."""
    uid, key = _resolve_zotero_credentials(user_id, api_key, config)

    state = load_sync_state(bib_cache_dir)
    since = None if full_sync else state.get("last_version")
    entries = fetch_library_items(uid, key, collection_key=collection_key, since_version=since)

    if not full_sync and since and not entries:
        return {
            "synced": 0,
            "total_cached": _count_cached_entries(bib_cache_dir),
            "message": "No changes since last sync",
            "last_version": since,
        }

    if full_sync or not since:
        merged = {e["bib_key"]: e for e in entries}
    else:
        existing = _load_cached_zotero_entries(bib_cache_dir)
        merged = {e["bib_key"]: e for e in existing}
        for e in entries:
            merged[e["bib_key"]] = e
        entries = list(merged.values())

    bib_cache_dir.mkdir(parents=True, exist_ok=True)
    out = bib_cache_dir / "zotero_live.json"
    out.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    max_version = state.get("last_version", 0)
    for e in entries:
        v = e.get("zotero_version")
        if isinstance(v, int) and v > max_version:
            max_version = v

    save_sync_state(bib_cache_dir, {
        "last_version": max_version,
        "user_id": uid,
        "collection_key": collection_key,
        "entry_count": len(entries),
    })
    return {
        "synced": len(entries),
        "total_cached": len(entries),
        "last_version": max_version,
        "cache_file": str(out),
    }


def _load_cached_zotero_entries(bib_cache_dir: Path) -> List[Dict[str, Any]]:
    path = bib_cache_dir / "zotero_live.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    return []


def _count_cached_entries(bib_cache_dir: Path) -> int:
    return len(_load_cached_zotero_entries(bib_cache_dir))


def _resolve_zotero_credentials(
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    cfg = config or {}
    uid = (
        user_id
        or os.getenv("ZOTERO_USER_ID", "")
        or str(cfg.get("zotero_user_id") or "")
    ).strip()
    key = (
        api_key
        or os.getenv("ZOTERO_API_KEY", "")
        or str(cfg.get("zotero_api_key") or "")
    ).strip()
    if not uid or not key:
        raise ValueError("ZOTERO_USER_ID and ZOTERO_API_KEY are required for Zotero sync")
    return uid, key


def fetch_item_children(user_id: str, api_key: str, item_key: str) -> List[Dict[str, Any]]:
    with httpx.Client(timeout=60.0, headers=_api_headers(api_key)) as client:
        resp = client.get(f"{ZOTERO_API}/users/{user_id}/items/{item_key}/children")
        resp.raise_for_status()
        return resp.json()


def fetch_pdf_for_item(user_id: str, api_key: str, item_key: str) -> Optional[bytes]:
    """Download the first PDF attachment for a Zotero item."""
    children = fetch_item_children(user_id, api_key, item_key)
    for child in children:
        data = child.get("data") or child
        if data.get("itemType") != "attachment":
            continue
        content_type = (data.get("contentType") or "").lower()
        if "pdf" not in content_type and data.get("linkMode") != "imported_file":
            continue
        attachment_key = data.get("key") or data.get("itemKey")
        if not attachment_key:
            continue
        with httpx.Client(timeout=120.0, headers=_api_headers(api_key)) as client:
            file_resp = client.get(
                f"{ZOTERO_API}/users/{user_id}/items/{attachment_key}/file",
                follow_redirects=True,
            )
            if file_resp.status_code == 200 and file_resp.content:
                return file_resp.content
    return None


def sync_zotero_with_pdfs(
    ctx: Any,
    *,
    collection_key: Optional[str] = None,
    full_sync: bool = False,
    extract: bool = True,
    build: bool = True,
) -> Dict[str, Any]:
    """Sync bib metadata then ingest PDF attachments for changed items."""
    from litgraph.context import LitgraphContext

    uid, key = _resolve_zotero_credentials(config=ctx.config)
    bib_result = sync_zotero_library(
        ctx.bib_cache_dir,
        user_id=uid,
        api_key=key,
        collection_key=collection_key,
        full_sync=full_sync,
    )
    entries = _load_cached_zotero_entries(ctx.bib_cache_dir)
    lctx = LitgraphContext(
        project_root=ctx.project_root,
        workspace_id=ctx.workspace_id,
        load_env_files=False,
    )
    ingested = 0
    skipped = 0
    errors: List[str] = []
    for entry in entries:
        zkey = str(entry.get("zotero_key") or entry.get("bib_key") or "")
        if not zkey:
            continue
        source_ref = f"zotero://{uid}/{zkey}"
        try:
            pdf = fetch_pdf_for_item(uid, key, zkey)
            if not pdf:
                skipped += 1
                continue
            result = lctx.ingest_from_bytes(
                pdf,
                filename=f"zotero_{zkey}.pdf",
                source_ref=source_ref,
                extract=extract,
                build=False,
            )
            if entry.get("doi"):
                from litgraph.ingest.dedup import register_paper_identity

                register_paper_identity(
                    ctx.litgraph_dir,
                    result.source_path,
                    result.paper_id,
                    workspace_id=ctx.workspace_id,
                    content_hash=hashlib.sha256(pdf).hexdigest(),
                    source_ref=source_ref,
                    zotero_key=zkey,
                    doi=str(entry.get("doi") or ""),
                )
            ingested += 1
        except Exception as exc:
            errors.append(f"{zkey}: {exc}")
    if build and ingested:
        from litgraph.cli.helpers import build_paper_graph

        build_paper_graph(ctx)
    return {
        **bib_result,
        "pdfs_ingested": ingested,
        "pdfs_skipped": skipped,
        "pdf_errors": errors,
    }


def import_zotero_export(path: Path, bib_cache_dir: Path) -> List[Dict[str, Any]]:
    """Import Zotero JSON export into bib cache (one-shot)."""
    entries = parse_zotero_json_export(path)
    bib_cache_dir.mkdir(parents=True, exist_ok=True)
    out = bib_cache_dir / f"zotero_{path.stem}.json"
    out.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return entries
