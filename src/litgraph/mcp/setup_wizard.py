"""MCP client setup wizard."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def resolve_litgraph_mcp_command() -> tuple[str, list[str]]:
    """Return (command, args) to run `litgraph serve-mcp` on any platform."""
    litgraph = shutil.which("litgraph")
    if litgraph:
        return litgraph, ["serve-mcp"]
    return sys.executable, ["-m", "litgraph", "serve-mcp"]


def build_mcp_client_config(project_root: Path) -> dict:
    """Build a Cursor / Claude Desktop MCP config for the given project."""
    command, args = resolve_litgraph_mcp_command()
    return {
        "mcpServers": {
            "literature-graph-context": {
                "command": command,
                "args": args,
                "env": {
                    "LITGRAPH_PROJECT_ROOT": str(project_root.resolve()),
                },
            }
        }
    }


def configure_mcp_client(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    config = build_mcp_client_config(root)
    out = root / "mcp.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    return out
