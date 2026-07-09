"""Dispatch parsing by file extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from litgraph.parser.bib_parser import parse_bib_file, save_bib_cache
from litgraph.parser.md_parser import parse_md
from litgraph.parser.pdf_parser import parse_pdf
from litgraph.parser.reference_parser import parse_references_section
from litgraph.parser.section_splitter import get_section_text, split_sections
from litgraph.utils.paper_registry import assign_paper_id, get_paper_id_for_path
from litgraph.scanner.hash_cache import load_cache


def parse_file(
    file_path: Path,
    bib_cache_dir: Path,
    parsed_cache_dir: Path,
    *,
    litgraph_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
    content_hash: str = "",
    source_ref: str = "",
    workspace_id: str = "default",
) -> Tuple[str, str]:
    """Parse one file. Returns (kind, paper_id_or_empty). kind: pdf|md|bib|skip"""
    suffix = file_path.suffix.lower()
    rel_path = ""
    if project_root:
        try:
            rel_path = str(file_path.resolve().relative_to(project_root.resolve()))
        except ValueError:
            rel_path = str(file_path.resolve())

    if litgraph_dir and rel_path:
        sha = content_hash
        if not sha and project_root:
            cache = load_cache(project_root / ".litgraph" / "cache" / "files.json")
            sha = (cache.get(rel_path) or {}).get("sha256", "")
        existing = get_paper_id_for_path(litgraph_dir, rel_path, workspace_id=workspace_id)
        paper_id = existing or assign_paper_id(
            litgraph_dir,
            rel_path,
            sha,
            workspace_id=workspace_id,
            source_ref=source_ref,
        )
    else:
        from litgraph.utils.ids import paper_id_from_path
        paper_id = paper_id_from_path(file_path)

    if suffix == ".pdf":
        parsed = split_sections(parse_pdf(file_path, paper_id=paper_id))
        parsed["source_type"] = "pdf"
        parsed["source_stem"] = file_path.stem
        parsed["source_path"] = rel_path or str(file_path)
        parsed["content_hash"] = content_hash
        parsed["parse_paper_id"] = paper_id
        if source_ref:
            parsed["source_ref"] = source_ref
        ref_text = get_section_text(parsed, "References", "Bibliography")
        if ref_text:
            ref_data = parse_references_section(ref_text)
            parsed["references"] = ref_data.get("references", [])
            parsed["reference_meta"] = ref_data.get("reference_meta", {})
        else:
            parsed["references"] = []
            parsed["reference_meta"] = {"count": 0, "parsed": 0}
        out = parsed_cache_dir / f"{paper_id}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return "pdf", paper_id
    if suffix == ".md":
        parsed = parse_md(file_path, paper_id=paper_id)
        parsed["source_stem"] = file_path.stem
        parsed["source_path"] = rel_path or str(file_path)
        parsed["content_hash"] = content_hash
        parsed["parse_paper_id"] = paper_id
        if source_ref:
            parsed["source_ref"] = source_ref
        out = parsed_cache_dir / f"{paper_id}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return "md", paper_id
    if suffix == ".bib":
        entries = parse_bib_file(file_path)
        out = bib_cache_dir / f"{file_path.stem}.json"
        save_bib_cache(out, entries)
        return "bib", ""
    return "skip", ""


def collect_parse_targets(files: List[Path], only_changed: bool, changed: List[Path]) -> List[Path]:
    if only_changed:
        changed_set = {p.resolve() for p in changed}
        return [p for p in files if p.resolve() in changed_set]
    return files
