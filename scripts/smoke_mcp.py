"""Smoke-test MCP tools against the examples demo graph."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from litgraph.mcp.server import MCPServer


def _call(server: MCPServer, name: str, args: dict) -> dict:
    response = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })
    text = response["result"]["content"][0]["text"]
    return json.loads(text)


def main() -> None:
    server = MCPServer(ROOT)

    tools = server.handle_request({
        "jsonrpc": "2.0",
        "id": 0,
        "method": "tools/list",
        "params": {},
    })
    names = [t["name"] for t in tools["result"]["tools"]]
    print(f"tools ({len(names)}): {', '.join(names[:5])}...")

    papers = _call(server, "list_papers", {})
    print(f"list_papers: {len(papers.get('papers', []))} paper(s)")

    gnn = _call(server, "find_papers_by_method", {"method": "GNN"})
    ids = [p.get("paper_id") for p in gnn.get("papers", [])]
    print(f"find_papers_by_method(GNN): {ids}")

    limits = _call(server, "find_limitations", {"topic": "event"})
    print(f"find_limitations(event): {len(limits.get('limitations', []))} hit(s)")

    compare = _call(
        server,
        "compare_papers",
        {"paper_ids": ["mobility_gnn_2024", "event_forecasting_2025"]},
    )
    assert "markdown_table" in compare
    print("compare_papers: ok (markdown_table)")

    gaps = _call(server, "find_research_gaps", {"topic": "event", "min_papers": 1})
    print(f"find_research_gaps: {len(gaps.get('gaps', []))} gap(s)")

    print("MCP smoke test passed.")


if __name__ == "__main__":
    main()
