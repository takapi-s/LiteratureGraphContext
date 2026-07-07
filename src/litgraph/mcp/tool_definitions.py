"""MCP tool definitions."""

TOOLS = {
    "list_papers": {
        "name": "list_papers",
        "description": "List all indexed papers in the literature graph.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "summarize_paper": {
        "name": "summarize_paper",
        "description": "Summarize a paper by paper_id with tasks, methods, datasets, and limitations.",
        "inputSchema": {
            "type": "object",
            "properties": {"paper_id": {"type": "string"}},
            "required": ["paper_id"],
        },
    },
    "find_papers_by_method": {
        "name": "find_papers_by_method",
        "description": "Find papers that use a given method (e.g. GNN).",
        "inputSchema": {
            "type": "object",
            "properties": {"method": {"type": "string"}},
            "required": ["method"],
        },
    },
    "find_papers_by_task": {
        "name": "find_papers_by_task",
        "description": "Find papers targeting a research task.",
        "inputSchema": {
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
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
    "get_evidence_for_claim": {
        "name": "get_evidence_for_claim",
        "description": "Get evidence for a specific claim_id.",
        "inputSchema": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}},
            "required": ["claim_id"],
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
    "build_literature_matrix": {
        "name": "build_literature_matrix",
        "description": "Build a topic-based literature matrix from indexed papers.",
        "inputSchema": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
    "check_job_status": {
        "name": "check_job_status",
        "description": "Check extraction job status and progress.",
        "inputSchema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    "list_jobs": {
        "name": "list_jobs",
        "description": "List all background extraction jobs.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "get_paper_neighbors": {
        "name": "get_paper_neighbors",
        "description": "List neighboring papers via CITES, CITED_BY, CONTRASTS_WITH, EXTENDS graph edges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "relationships": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "include_summary": {"type": "boolean", "default": False},
            },
            "required": ["paper_id"],
        },
    },
    "search_papers": {
        "name": "search_papers",
        "description": (
            "Search indexed papers by natural-language query. Returns paper_id, title, score, "
            "and match_reason. Use this first for ambiguous questions before summarize_paper."
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
    "expand_paper_graph": {
        "name": "expand_paper_graph",
        "description": (
            "Multi-hop graph expansion from a seed paper across CITES, EXTENDS, CONTRASTS_WITH, "
            "and shared methods."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "hops": {"type": "integer", "default": 2},
                "relationships": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "include_summary": {"type": "boolean", "default": False},
            },
            "required": ["paper_id"],
        },
    },
    "generate_related_work_outline": {
        "name": "generate_related_work_outline",
        "description": "Generate a related work section outline by topic with supporting papers.",
        "inputSchema": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
}
