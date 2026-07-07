# LiteratureGraphContext Roadmap

> **Current version**: 0.4.0  
> **Last updated**: 2026-07

Tracks **remaining work**, known limitations, and out-of-scope items.  
Shipped features through v0.4.x are recorded in git history and [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md).

**Design note:** Related work draft prose is intentionally left to the MCP-connected AI (`outline` + `gaps` + `matrix` as context).

---

## Known limitations

| Area | Limitation |
|---|---|
| PDF parsing | Heuristic section detection only |
| MCP setup | Writes `mcp.json` only; no interactive wizard |
| md parser | Single-paper notes only |
| Zotero sync | Web API only; no desktop sqlite direct access |
| Research gaps | String-similarity clustering (no embeddings) |
| Tests | No E2E test with live LLM API |
| Neo4j | No migration tool from Kuzu |
| Graph UI | CGC Playground fork; paper-centric sidebar not yet customized |

---

## v1.0 — Production OSS

- [ ] **PyPI release** — packaging and stable public API
- [ ] **Documentation and tutorial** — end-to-end guide (init → extract → MCP → viz)
- [ ] **MCP setup wizard** — interactive Cursor / Claude Desktop configuration
- [ ] **Embedding-based gap clustering** — higher-quality research gap detection
- [ ] **Team sharing** — multi-user graph, shared `.litgraph` or remote DB
- [ ] **MCP `watch_papers_directory`** (optional) — expose file watch via MCP

---

## Out of scope (for now)

- Experiment result CSVs, code repos, slides, notebooks as input
- Free-form knowledge graph (fixed literature-review schema only)
- Full PDF layout reconstruction
- Related work draft generation inside LGC (use MCP client instead)
