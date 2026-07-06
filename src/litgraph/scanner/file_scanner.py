"""File discovery for paper PDFs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set

SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".bib", ".md"}


def safe_walk(path: Path) -> List[Path]:
    if not path.exists():
        return []
    if not path.is_file():
        files: List[Path] = []

        def onerror(err: OSError) -> None:
            pass

        for root_str, _dirs, filenames in os.walk(str(path), onerror=onerror):
            for name in filenames:
                files.append(Path(root_str) / name)
        return files
    return [path]


def discover_papers(path: Path, extensions: Set[str] | None = None) -> List[Path]:
    exts = extensions or SUPPORTED_EXTENSIONS
    discovered = safe_walk(path)
    return sorted(
        p.resolve()
        for p in discovered
        if p.is_file() and p.suffix.lower() in exts
    )
