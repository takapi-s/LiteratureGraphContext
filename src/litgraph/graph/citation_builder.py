"""Build Paper CITES edges from BibTeX entries."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


def _split_citation_keys(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,;]\s*", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def build_citation_pairs(
    bib_entries: List[Dict[str, Any]],
    indexed_paper_ids: Set[str],
) -> List[Tuple[str, str]]:
    """Return (citing_paper_id, cited_paper_id) pairs resolved from bib metadata."""
    bib_key_to_paper: Dict[str, str] = {}
    for entry in bib_entries:
        bib_key = entry.get("bib_key", "")
        if not bib_key:
            continue
        if bib_key in indexed_paper_ids:
            bib_key_to_paper[bib_key] = bib_key
        elif entry.get("source_stem") in indexed_paper_ids:
            bib_key_to_paper[bib_key] = entry["source_stem"]

    for entry in bib_entries:
        bib_key = entry.get("bib_key", "")
        stem = entry.get("source_stem", "")
        if stem in indexed_paper_ids:
            bib_key_to_paper.setdefault(bib_key, stem)

    pairs: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for entry in bib_entries:
        citing = bib_key_to_paper.get(entry.get("bib_key", ""))
        if not citing or citing not in indexed_paper_ids:
            continue
        for cited_key in _split_citation_keys(entry.get("citations", "")):
            cited = bib_key_to_paper.get(cited_key, cited_key)
            if cited in indexed_paper_ids and citing != cited:
                pair = (citing, cited)
                if pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)
    return pairs


def merge_citation_pairs(
    *pair_lists: List[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    """Merge multiple CITES pair lists, deduplicating."""
    merged: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for pair_list in pair_lists:
        for pair in pair_list:
            if pair not in seen:
                seen.add(pair)
                merged.append(pair)
    return merged


def bib_only_entries(
    bib_entries: List[Dict[str, Any]],
    indexed_paper_ids: Set[str],
) -> List[Dict[str, Any]]:
    """Bib entries with no corresponding extracted paper."""
    linked_stems = set(indexed_paper_ids)
    for entry in bib_entries:
        if entry.get("bib_key") in indexed_paper_ids:
            linked_stems.add(entry["bib_key"])
        if entry.get("source_stem") in indexed_paper_ids:
            linked_stems.add(entry["source_stem"])

    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for entry in bib_entries:
        bib_key = entry.get("bib_key", "")
        stem = entry.get("source_stem", "")
        if bib_key in linked_stems or stem in linked_stems:
            continue
        pid = bib_key or stem
        if not pid or pid in seen:
            continue
        seen.add(pid)
        out.append({**entry, "paper_id": pid})
    return out
