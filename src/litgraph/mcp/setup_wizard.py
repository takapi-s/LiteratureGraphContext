"""MCP client setup wizard."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def configure_mcp_client(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    litgraph_cmd = shutil.which("litgraph") or "litgraph"
    config = {
        "mcpServers": {
            "literature-graph-context": {
                "command": "bash",
                "args": [
                    "-lc",
                    f"cd {root.resolve()} && exec {litgraph_cmd} serve-mcp",
                ],
            }
        }
    }
    out = root / "mcp.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return out
