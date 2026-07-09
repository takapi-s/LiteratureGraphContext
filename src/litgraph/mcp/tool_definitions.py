"""MCP tool definitions."""

TOOLS = {
    "list_papers": {
        "name": "list_papers",
        "description": "List all indexed papers in the literature graph.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "search_papers": {
        "name": "search_papers",
        "description": (
            "Search indexed papers by natural-language query. Returns paper_id, title, score, "
            "and match_reason. Use this first for ambiguous questions before summarize_paper. "
            "Hybrid search includes method/task channels internally. Use center_paper_id to "
            "boost papers near a seed paper in the citation graph."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 10},
                "center_paper_id": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    "summarize_paper": {
        "name": "summarize_paper",
        "description": (
            "Summarize a paper by paper_id with tasks, methods, datasets, contributions, "
            "limitations, and claims (each with claim_id, page, section, evidence_text)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"paper_id": {"type": "string"}},
            "required": ["paper_id"],
        },
    },
    "compare_papers": {
        "name": "compare_papers",
        "description": "Compare multiple papers by task, method, dataset, metric, contribution, limitation, and difference.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["paper_ids"],
        },
    },
    "find_limitations": {
        "name": "find_limitations",
        "description": "Find limitations related to a topic or a specific paper, with evidence (page, section, evidence_text).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "paper_id": {"type": "string"},
            },
        },
    },
    "explore_paper_graph": {
        "name": "explore_paper_graph",
        "description": (
            "Explore graph neighbors from a seed paper. hops=1 returns direct neighbors "
            "(CITES, CITED_BY, CONTRASTS_WITH, EXTENDS). hops>=2 performs multi-hop BFS "
            "including SHARED_METHOD. Returns nodes with paper_id, title, relationship, "
            "and optional direction (1-hop) or hop distance (multi-hop)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "hops": {"type": "integer", "default": 1},
                "relationships": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "include_summary": {"type": "boolean", "default": False},
            },
            "required": ["paper_id"],
        },
    },
    "watch_papers_directory": {
        "name": "watch_papers_directory",
        "description": (
            "Start, stop, or check status of folder watch auto-ingest. "
            "Runs litgraph watch in a background subprocess."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "stop", "status"]},
                "papers_dir": {"type": "string"},
            },
            "required": ["action"],
        },
    },
}
