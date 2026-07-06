"""Dispatch parsing by file extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from litgraph.parser.bib_parser import parse_bib_file, save_bib_cache
from litgraph.parser.md_parser import parse_md
from litgraph.parser.pdf_parser import parse_pdf
from litgraph.parser.section_splitter import split_sections
from litgraph.utils.ids import paper_id_from_path


def parse_file(file_path: Path, bib_cache_dir: Path, parsed_cache_dir: Path) -> Tuple[str, str]:
    """Parse one file. Returns (kind, paper_id_or_empty). kind: pdf|md|bib|skip"""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        parsed = split_sections(parse_pdf(file_path))
        parsed["source_type"] = "pdf"
        out = parsed_cache_dir / f"{parsed['paper_id']}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return "pdf", parsed["paper_id"]
    if suffix == ".md":
        parsed = parse_md(file_path)
        out = parsed_cache_dir / f"{parsed['paper_id']}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return "md", parsed["paper_id"]
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
