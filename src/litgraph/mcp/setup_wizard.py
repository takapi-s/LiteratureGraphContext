"""MCP client setup wizard."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def configure_mcp_client(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    config = {
        "mcpServers": {
            "literature-graph-context": {
                "command": shutil.which("litgraph") or "litgraph",
                "args": ["serve-mcp"],
                "cwd": str(root.resolve()),
            }
        }
    }
    out = root / "mcp.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return out
