"""Zotero Web API live sync."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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
    url = str(data.get("url") or data.get("URL") or "").strip()
    year_raw = data.get("date", "") or ""
    year = int(year_raw[:4]) if len(year_raw) >= 4 and year_raw[:4].isdigit() else None
    entry: Dict[str, Any] = {
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
    if url:
        entry["url"] = url
    return entry


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
            if resp.status_code == 403:
                raise ValueError(
                    f"Zotero API returned 403 for {path}. "
                    "Check that ZOTERO_USER_ID is the numeric ID (not username) "
                    "and the API key has library read access. "
                    "Tip: omit ZOTERO_USER_ID and LGC will resolve it from the key."
                )
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
    existing = load_sync_state(cache_dir)
    if "ingested_versions" not in state and existing.get("ingested_versions"):
        state = {**state, "ingested_versions": existing["ingested_versions"]}
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_ingested_versions(cache_dir: Path) -> Dict[str, int]:
    raw = load_sync_state(cache_dir).get("ingested_versions") or {}
    result: Dict[str, int] = {}
    for key, value in raw.items():
        if value is None:
            continue
        try:
            result[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return result


def _entry_zotero_version(entry: Dict[str, Any]) -> Optional[int]:
    version = entry.get("zotero_version")
    if isinstance(version, int):
        return version
    if isinstance(version, str) and version.isdigit():
        return int(version)
    return None


def should_skip_ingested_item(
    zkey: str,
    entry: Dict[str, Any],
    ingested_versions: Dict[str, int],
) -> bool:
    """True when this Zotero item was already ingested at the current version."""
    if not zkey or zkey not in ingested_versions:
        return False
    version = _entry_zotero_version(entry)
    if version is None:
        return False
    return ingested_versions[zkey] == version


def record_ingested_version(cache_dir: Path, zkey: str, entry: Dict[str, Any]) -> None:
    version = _entry_zotero_version(entry)
    if not zkey or version is None:
        return
    state = load_sync_state(cache_dir)
    ingested = dict(state.get("ingested_versions") or {})
    ingested[zkey] = version
    state["ingested_versions"] = ingested
    save_sync_state(cache_dir, state)


def sync_zotero_library(
    bib_cache_dir: Path,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    collection_key: Optional[str] = None,
    full_sync: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sync Zotero library via Web API into bib cache."""
    raw_before = (
        (user_id or os.getenv("ZOTERO_USER_ID", "") or str((config or {}).get("zotero_user_id") or ""))
        .strip()
    )
    uid, key = _resolve_zotero_credentials(user_id, api_key, config)
    if not _is_numeric_user_id(raw_before) or raw_before != uid:
        try:
            persist_zotero_user_id(uid)
        except OSError:
            pass

    state = load_sync_state(bib_cache_dir)
    since = None if full_sync else state.get("last_version")
    entries = fetch_library_items(uid, key, collection_key=collection_key, since_version=since)

    if not full_sync and since and not entries:
        return {
            "synced": 0,
            "total_cached": _count_cached_entries(bib_cache_dir),
            "message": "No changes since last sync",
            "last_version": since,
            "user_id": uid,
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
        "user_id": uid,
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


def _is_numeric_user_id(value: str) -> bool:
    return bool(value) and value.isdigit()


def fetch_key_info(api_key: str) -> Dict[str, Any]:
    """Return metadata for an API key via GET /keys/current (includes userID)."""
    with httpx.Client(timeout=30.0, headers=_api_headers(api_key)) as client:
        resp = client.get(f"{ZOTERO_API}/keys/current")
        if resp.status_code == 403:
            raise ValueError(
                "Zotero API key was rejected (403). Create a key with library "
                "read access at https://www.zotero.org/settings/keys"
            )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from Zotero /keys/current")
        return data


def resolve_user_id_from_api_key(api_key: str) -> str:
    """Resolve numeric Zotero user ID from an API key."""
    info = fetch_key_info(api_key)
    uid = info.get("userID") or info.get("userId") or info.get("user_id")
    if uid is None:
        raise ValueError("Zotero /keys/current did not return userID")
    uid_str = str(uid).strip()
    if not _is_numeric_user_id(uid_str):
        raise ValueError(f"Zotero returned a non-numeric userID: {uid_str!r}")
    return uid_str


def _resolve_zotero_credentials(
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    *,
    auto_resolve_user_id: bool = True,
) -> tuple[str, str]:
    cfg = config or {}
    raw_uid = (
        user_id
        or os.getenv("ZOTERO_USER_ID", "")
        or str(cfg.get("zotero_user_id") or "")
    ).strip()
    key = (
        api_key
        or os.getenv("ZOTERO_API_KEY", "")
        or str(cfg.get("zotero_api_key") or "")
    ).strip()
    if not key:
        raise ValueError(
            "ZOTERO_API_KEY is required for Zotero sync. "
            "Create one at https://www.zotero.org/settings/keys"
        )
    uid = raw_uid if _is_numeric_user_id(raw_uid) else ""
    resolved_from_key = False
    if not uid and auto_resolve_user_id:
        uid = resolve_user_id_from_api_key(key)
        resolved_from_key = True
    if not uid:
        raise ValueError(
            "ZOTERO_USER_ID is missing and could not be resolved from the API key. "
            "It must be the numeric ID from https://www.zotero.org/settings/keys "
            "(not your username)."
        )
    if resolved_from_key or (raw_uid and raw_uid != uid):
        os.environ["ZOTERO_USER_ID"] = uid
    return uid, key


def persist_zotero_user_id(user_id: str, env_file: Optional[Path] = None) -> Path:
    """Write resolved numeric user ID into the global env file."""
    from litgraph.cli.config_manager import GLOBAL_ENV_FILE, ensure_global_config_dir

    target = env_file or GLOBAL_ENV_FILE
    ensure_global_config_dir()
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    lines = existing.splitlines() if existing else []
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("ZOTERO_USER_ID=") and not line.strip().startswith("#"):
            new_lines.append(f"ZOTERO_USER_ID={user_id}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"ZOTERO_USER_ID={user_id}")
    text = "\n".join(new_lines)
    if text and not text.endswith("\n"):
        text += "\n"
    target.write_text(text, encoding="utf-8")
    os.environ["ZOTERO_USER_ID"] = user_id
    return target


def fetch_item_children(user_id: str, api_key: str, item_key: str) -> List[Dict[str, Any]]:
    with httpx.Client(timeout=60.0, headers=_api_headers(api_key)) as client:
        resp = client.get(f"{ZOTERO_API}/users/{user_id}/items/{item_key}/children")
        resp.raise_for_status()
        return resp.json()


def fetch_item_data(user_id: str, api_key: str, item_key: str) -> Dict[str, Any]:
    """Fetch a single Zotero item's metadata."""
    with httpx.Client(timeout=60.0, headers=_api_headers(api_key)) as client:
        resp = client.get(f"{ZOTERO_API}/users/{user_id}/items/{item_key}")
        resp.raise_for_status()
        payload = resp.json()
    data = payload.get("data") or payload
    return data if isinstance(data, dict) else {}


def enrich_entry_url(
    user_id: str,
    api_key: str,
    entry: Dict[str, Any],
) -> Dict[str, Any]:
    """Ensure bib cache entries have a URL when Zotero stores one."""
    if str(entry.get("url") or "").strip():
        return entry
    zkey = str(entry.get("zotero_key") or entry.get("bib_key") or "").strip()
    if not zkey:
        return entry
    data = fetch_item_data(user_id, api_key, zkey)
    url = str(data.get("url") or data.get("URL") or "").strip()
    if not url:
        return entry
    return {**entry, "url": url}


def resolve_remote_ingest_source_ref(entry: Dict[str, Any]) -> Optional[str]:
    """Map a Zotero bib entry URL to an ingest source_ref (arXiv or direct PDF URL)."""
    url = str(entry.get("url") or "").strip()
    if not url:
        return None

    from litgraph.ingest.arxiv import normalize_arxiv_id

    try:
        arxiv_id = normalize_arxiv_id(url)
        return f"arxiv://{arxiv_id}"
    except ValueError:
        pass

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    path_lower = parsed.path.lower()
    if path_lower.endswith(".pdf") or "/pdf/" in path_lower:
        return url
    return None


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
    changed_only: bool = True,
    extract: bool = True,
    build: bool = True,
    show_progress: bool = True,
) -> Dict[str, Any]:
    """Sync bib metadata then ingest PDF attachments for changed items."""
    from rich.console import Console

    from litgraph.context import LitgraphContext

    console = Console(stderr=True)

    def _log(message: str) -> None:
        if show_progress:
            console.print(message)

    uid, key = _resolve_zotero_credentials(config=ctx.config)
    # Prefer the active workspace bib dir; fall back to legacy .litgraph/cache/bib
    # when an older sync wrote there (pre-workspace path).
    bib_dir = ctx.bib_cache_dir
    legacy_bib = ctx.litgraph_dir / "cache" / "bib"
    if not (bib_dir / "zotero_live.json").exists() and (legacy_bib / "zotero_live.json").exists():
        bib_dir = legacy_bib

    _log("[cyan]Fetching Zotero library metadata…[/cyan]")
    bib_result = sync_zotero_library(
        bib_dir,
        user_id=uid,
        api_key=key,
        collection_key=collection_key,
        full_sync=full_sync,
    )
    _log(
        f"[green]Bib sync[/green]: {bib_result.get('synced', 0)} entr"
        f"{'y' if bib_result.get('synced') == 1 else 'ies'} "
        f"(version {bib_result.get('last_version', '?')})"
    )
    # Keep workspace bib cache in sync when we had to read/write legacy path.
    if bib_dir != ctx.bib_cache_dir:
        ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)
        for name in ("zotero_live.json", SYNC_STATE_FILE):
            src = bib_dir / name
            if src.exists():
                (ctx.bib_cache_dir / name).write_bytes(src.read_bytes())

    entries = _load_cached_zotero_entries(ctx.bib_cache_dir)
    work_entries = [
        e for e in entries if str(e.get("zotero_key") or e.get("bib_key") or "").strip()
    ]
    ingested_versions = get_ingested_versions(ctx.bib_cache_dir)
    candidates = work_entries
    if changed_only and not full_sync:
        work_entries = []
        for entry in candidates:
            zkey = str(entry.get("zotero_key") or entry.get("bib_key") or "")
            if should_skip_ingested_item(zkey, entry, ingested_versions):
                continue
            work_entries.append(entry)
    total = len(work_entries)
    version_skipped = len(candidates) - total if changed_only and not full_sync else 0
    _log(
        f"[cyan]Ingesting PDFs[/cyan]: {total} item(s)"
        + (f" ({version_skipped} unchanged skipped)" if version_skipped else "")
        + (" (LLM extract enabled — this can take several minutes)" if extract else "")
    )

    lctx = LitgraphContext(
        project_root=ctx.project_root,
        workspace_id=ctx.workspace_id,
        load_env_files=False,
    )
    ingested = 0
    skipped = 0
    errors: List[str] = []
    for index, entry in enumerate(work_entries, start=1):
        zkey = str(entry.get("zotero_key") or entry.get("bib_key") or "")
        title = str(entry.get("title") or zkey).strip()
        label = title if len(title) <= 64 else title[:61] + "…"
        source_ref = f"zotero://{uid}/{zkey}"
        _log(f"  [{index}/{total}] {label}")
        try:
            _log("    ↓ download PDF")
            pdf = fetch_pdf_for_item(uid, key, zkey)
            if not pdf:
                work_entry = enrich_entry_url(uid, key, entry)
                remote_ref = resolve_remote_ingest_source_ref(work_entry)
                if remote_ref:
                    from litgraph.ingest.registry import resolve_ingest_payload

                    _log(f"    ↓ fetch PDF from webpage URL")
                    payload = resolve_ingest_payload(remote_ref)
                    pdf = payload.data
                else:
                    skipped += 1
                    _log("    [yellow]skip[/yellow] (no PDF attachment or downloadable URL)")
                    continue
            _log(
                "    → parse"
                + (" + extract" if extract else "")
                + f" ({len(pdf) // 1024} KB)"
            )
            result = lctx.ingest_from_bytes(
                pdf,
                filename=f"zotero_{zkey}.pdf",
                source_ref=source_ref,
                extract=extract,
                build=False,
                show_progress=show_progress,
            )
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
            if result.errors:
                for err in result.errors:
                    errors.append(f"{zkey}: {err}")
                _log(f"    [yellow]partial[/yellow] {result.paper_id}")
            elif result.skipped_extract:
                _log(f"    [dim]ok (extract cached)[/dim] {result.paper_id}")
            else:
                _log(f"    [green]ok[/green] {result.paper_id}")
            record_ingested_version(ctx.bib_cache_dir, zkey, entry)
            ingested += 1
        except Exception as exc:
            errors.append(f"{zkey}: {exc}")
            _log(f"    [red]failed[/red] {exc}")
    if build and ingested:
        _log("[cyan]Building graph…[/cyan]")
        from litgraph.cli.helpers import build_paper_graph

        build_result = build_paper_graph(ctx)
        _log(
            f"[green]Graph ready[/green]: "
            f"{build_result.get('papers_indexed', 0)} paper(s), "
            f"nodes={build_result.get('nodes', 0)}, edges={build_result.get('edges', 0)}"
        )
    return {
        **bib_result,
        "pdfs_ingested": ingested,
        "pdfs_skipped": skipped,
        "pdfs_version_skipped": version_skipped,
        "pdf_errors": errors,
    }


def import_zotero_export(path: Path, bib_cache_dir: Path) -> List[Dict[str, Any]]:
    """Import Zotero JSON export into bib cache (one-shot)."""
    entries = parse_zotero_json_export(path)
    bib_cache_dir.mkdir(parents=True, exist_ok=True)
    out = bib_cache_dir / f"zotero_{path.stem}.json"
    out.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return entries
