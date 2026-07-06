"""BibTeX metadata parser (lightweight, no external parser dependency)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
FIELD_RE = re.compile(r"(\w+)\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^,\n]+)", re.IGNORECASE)


def _clean_value(raw: str) -> str:
    val = raw.strip().rstrip(",")
    if (val.startswith("{") and val.endswith("}")) or (val.startswith('"') and val.endswith('"')):
        val = val[1:-1]
    return val.strip()


def _parse_year(raw: str) -> int | None:
    match = re.search(r"\d{4}", raw)
    return int(match.group()) if match else None


def _parse_authors(raw: str) -> List[str]:
    return [a.strip() for a in raw.split(" and ") if a.strip()]


def _venue(fields: Dict[str, str]) -> str:
    for key in ("journal", "booktitle", "publisher", "school", "institution"):
        if fields.get(key):
            return fields[key]
    return ""


def parse_bib_text(text: str, source_file: str = "", source_stem: str = "") -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for match in ENTRY_RE.finditer(text):
        bib_key = match.group(2).strip()
        start = match.end()
        next_entry = ENTRY_RE.search(text, start)
        block = text[start : next_entry.start() if next_entry else len(text)]
        fields: Dict[str, str] = {}
        for field_match in FIELD_RE.finditer(block):
            fields[field_match.group(1).lower()] = _clean_value(field_match.group(2))
        entries.append({
            "bib_key": bib_key,
            "title": fields.get("title", ""),
            "year": _parse_year(fields.get("year", "")),
            "authors": _parse_authors(fields.get("author", "")),
            "venue": _venue(fields),
            "doi": fields.get("doi", ""),
            "source_file": source_file,
            "source_stem": source_stem,
        })
    return entries


def parse_bib_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return entry


def parse_bib_file(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    return parse_bib_text(text, source_file=str(path), source_stem=path.stem)


def save_bib_cache(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def load_all_bib_entries(bib_cache_dir: Path) -> List[Dict[str, Any]]:
    if not bib_cache_dir.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for cache_file in sorted(bib_cache_dir.glob("*.json")):
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            entries.extend(data)
    return entries
