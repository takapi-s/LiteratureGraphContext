"""Ignore rules for papers directory watching."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

DEFAULT_IGNORE_PATTERNS = [
    ".litgraph/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/~$*",
    "**/*.tmp",
    "**/.#*",
    "**/Thumbs.db",
    "**/.DS_Store",
]


def build_ignore_spec(
    ignore_root: Path,
    explicit_path: Optional[Path] = None,
) -> Tuple[PathSpec, Optional[Path]]:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    resolved: Optional[Path] = None
    candidates = [
        explicit_path,
        ignore_root / ".litgraphignore",
        ignore_root.parent / ".litgraphignore",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            patterns.extend(
                line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")
            )
            resolved = candidate.resolve()
            break
    return PathSpec.from_lines(GitWildMatchPattern, patterns), resolved


def should_ignore(path: Path, ignore_root: Path, ignore_spec: PathSpec) -> bool:
    try:
        rel = path.resolve().relative_to(ignore_root.resolve()).as_posix()
    except ValueError:
        return True
    if not rel:
        return False
    return ignore_spec.match_file(rel)
