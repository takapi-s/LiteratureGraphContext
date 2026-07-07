"""BibTeX metadata parser with nested-brace support."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENTRY_START_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s#]+)\s*,", re.IGNORECASE)


def _parse_braced_value(text: str, start: int) -> Tuple[str, int]:
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth == 1:
                i += 1
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return text[start + 1 :], len(text)


def _parse_quoted_value(text: str, start: int) -> Tuple[str, int]:
    i = start + 1
    chars: List[str] = []
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == start + 1 or text[i - 1] != "\\"):
            return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    return "".join(chars), len(text)


def _parse_raw_value(text: str, start: int) -> Tuple[str, int]:
    end = start
    while end < len(text) and text[end] not in ",\n":
        end += 1
    return text[start:end].strip().rstrip(","), end


def _parse_field_value(text: str, start: int) -> Tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text):
        return "", start
    if text[start] == "{":
        return _parse_braced_value(text, start)
    if text[start] == '"':
        return _parse_quoted_value(text, start)
    return _parse_raw_value(text, start)


def _find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def _parse_entry_block(block: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    i = 0
    while i < len(block):
        while i < len(block) and (block[i].isspace() or block[i] == ","):
            i += 1
        if i >= len(block):
            break
        name_end = i
        while name_end < len(block) and (block[name_end].isalnum() or block[name_end] == "_"):
            name_end += 1
        if name_end == i:
            i += 1
            continue
        name = block[i:name_end].lower()
        i = name_end
        while i < len(block) and block[i].isspace():
            i += 1
        if i >= len(block) or block[i] != "=":
            continue
        i += 1
        value, i = _parse_field_value(block, i)
        fields[name] = value.strip()
    return fields


def _parse_year(raw: str) -> int | None:
    match = re.search(r"\d{4}", raw)
    return int(match.group()) if match else None


def _parse_authors(raw: str) -> List[str]:
    parts = re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)
    return [a.strip() for a in parts if a.strip()]


def _venue(fields: Dict[str, str]) -> str:
    for key in ("journal", "booktitle", "publisher", "school", "institution"):
        if fields.get(key):
            return fields[key]
    return ""


def _normalize_citations(raw: str) -> str:
    inner = raw.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1]
    return inner


def parse_bib_text(text: str, source_file: str = "", source_stem: str = "") -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for match in ENTRY_START_RE.finditer(text):
        entry_type = match.group(1).lower()
        bib_key = match.group(2).strip()
        body_start = match.end()
        close = _find_matching_brace(text, match.start() + text[match.start() : match.end()].index("{"))
        block = text[body_start:close]
        fields = _parse_entry_block(block)
        citations = _normalize_citations(fields.get("citations", ""))
        entries.append({
            "bib_key": bib_key,
            "entry_type": entry_type,
            "title": fields.get("title", ""),
            "year": _parse_year(fields.get("year", "")),
            "authors": _parse_authors(fields.get("author", "")),
            "venue": _venue(fields),
            "doi": fields.get("doi", ""),
            "citations": citations,
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
