"""Workspace helpers for multi-collection graph scoping."""

from __future__ import annotations

import os
import re

DEFAULT_WORKSPACE = "default"
_WORKSPACE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def normalize_workspace_id(workspace_id: str | None) -> str:
    ws = (workspace_id or DEFAULT_WORKSPACE).strip()
    if not ws:
        return DEFAULT_WORKSPACE
    if not _WORKSPACE_RE.match(ws):
        raise ValueError(
            f"Invalid workspace_id {workspace_id!r}; use alphanumeric, underscore, hyphen (max 64 chars)."
        )
    return ws


def workspace_from_env() -> str:
    return normalize_workspace_id(os.getenv("LITGRAPH_WORKSPACE", DEFAULT_WORKSPACE))
