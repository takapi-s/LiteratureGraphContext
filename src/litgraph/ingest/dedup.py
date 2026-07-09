"""Paper deduplication helpers for ingest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from litgraph.utils.paper_registry import (
    get_paper_id_for_content_hash,
    get_paper_id_for_doi,
    get_paper_id_for_source_ref,
    get_paper_id_for_zotero_key,
    load_registry,
    save_registry,
    update_registry_entry,
)
from litgraph.utils.workspace import DEFAULT_WORKSPACE


def resolve_existing_paper_id(
    litgraph_dir: Path,
    *,
    workspace_id: str = DEFAULT_WORKSPACE,
    zotero_key: str = "",
    doi: str = "",
    content_hash: str = "",
    source_ref: str = "",
) -> Optional[str]:
    """Resolve an existing paper_id using dedup keys in priority order."""
    if zotero_key:
        found = get_paper_id_for_zotero_key(litgraph_dir, zotero_key, workspace_id=workspace_id)
        if found:
            return found
    if doi:
        found = get_paper_id_for_doi(litgraph_dir, doi, workspace_id=workspace_id)
        if found:
            return found
    if content_hash:
        found = get_paper_id_for_content_hash(litgraph_dir, content_hash, workspace_id=workspace_id)
        if found:
            return found
    if source_ref:
        found = get_paper_id_for_source_ref(litgraph_dir, source_ref, workspace_id=workspace_id)
        if found:
            return found
    return None


def register_paper_identity(
    litgraph_dir: Path,
    source_path: str,
    paper_id: str,
    *,
    workspace_id: str = DEFAULT_WORKSPACE,
    content_hash: str = "",
    source_ref: str = "",
    zotero_key: str = "",
    doi: str = "",
) -> None:
    update_registry_entry(
        litgraph_dir,
        source_path,
        paper_id,
        content_hash,
        workspace_id=workspace_id,
        source_ref=source_ref,
        zotero_key=zotero_key,
    )
    if doi:
        registry = load_registry(litgraph_dir, workspace_id)
        entry = dict(registry.get(source_path) or {})
        entry["doi"] = doi
        registry[source_path] = entry
        save_registry(litgraph_dir, registry, workspace_id)
