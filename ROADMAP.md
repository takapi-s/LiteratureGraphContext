# LiteratureGraphContext Roadmap

> **Current version**: 0.6.0  
> **Last updated**: 2026-07

Tracks **remaining work**, known limitations, and out-of-scope items.  
Shipped features through v0.5.x are recorded in git history and [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md).

## Design philosophy

LiteratureGraphContext is a **structured evidence layer**, not an interpretation engine.

| Layer | Responsibility | Examples |
|---|---|---|
| **LGC (data plane)** | Ingest, structure, connect, cite | PDF → graph; `CITES` / `CONTRASTS_WITH`; MCP tools with `evidence_text` |
| **Connected agent** | Interpret, cluster, draft | Research gaps; related work prose; cross-field synthesis |

**Core bet:** multiple studies are properly linked in the graph; MCP returns topic-filtered, evidence-backed facts; the agent answers from that material.

**Intentionally not in LGC:** pre-computed gap clustering, related-work draft generation, embedding-based narrative synthesis. Use `find_limitations`, `compare_papers`, and `build_literature_matrix` as agent context instead.

**In scope (search layer):** `search_papers` with keyword + embedding hybrid retrieval; `expand_paper_graph` for multi-hop lineage; **opaque immutable `paper_id` (UUID at first ingest)** with meaning in metadata + search.

**Vision:** *Literature* means written sources broadly—not only academic papers. The current focus is PDF-centric literature review, but the long-term goal is to index and graph **any structured knowledge source** (web pages, documentation, technical blogs, etc.) under the same schema-oriented workflow.

---

## Known limitations — and how we address them

Prioritized under the design philosophy above.

### Active (improves graph quality & agent context)

| Area | Limitation | Direction |
|---|---|---|
| **Paper identity** | Content-based slug IDs changed on re-extract | **Done (v0.6):** UUID at scan/parse via `paper_registry.json`; `source_path` / `source_stem` on Paper nodes |
| **Search entry** | Attribute search only; ambiguous queries need many MCP calls | **Done (v0.5):** `search_papers` (keyword + RRF + optional embeddings) |
| **Graph traversal** | 1-hop `get_paper_neighbors` only | **Done (v0.5):** `expand_paper_graph` (multi-hop BFS with edge weights) |
| **MCP tool coverage** | Few tools had automated MCP tests | **Done (v0.6):** full MCP contract + agent workflow tests; `litgraph test-mcp` |
| **PDF parsing** | Heuristic section detection only | Expand section patterns; parse diagnostics |
| **Graph UI** | CGC Playground fork; paper-centric sidebar not customized | Paper preview cards in sidebar |
| **MCP stability** | Kuzu lock when `viz` and `serve-mcp` run together | Document single-writer policy; avoid concurrent writers |

### By design (not limitations — delegated to agent)

| Area | Note |
|---|---|
| **Research gap clustering** | Use `find_limitations` + `compare_papers`; agent interprets gaps |
| **Related work prose** | `generate_related_work_outline` is optional sugar |

### Deferred (acceptable for now)

| Area | Limitation | When to revisit |
|---|---|---|
| **MCP setup** | Writes `mcp.json` only; no interactive wizard | v1.0 onboarding |
| **md parser** | Single-paper notes only | Multi-paper survey notes workflow |
| **Zotero sync** | Web API only | Desktop sqlite sync |
| **Tests** | No E2E test with live LLM API | Optional CI smoke |
| **Neo4j** | No migration tool from Kuzu | Teams on Neo4j at scale |
| **Claim-level embeddings** | Paper-level embeddings only | Fine-grained evidence search |

### Out of scope (unchanged)

| Area | Note |
|---|---|
| **PDF layout** | Full layout reconstruction out of scope |
| **Free-form KG** | Fixed literature-review schema only |
| **Graphiti integration** | Reference only; no runtime dependency |

---

## v1.0 — Production OSS

- [ ] **PyPI release** — packaging and stable public API
- [ ] **Documentation and tutorial** — init → extract → MCP → viz; agent + data-plane workflow
- [ ] **PDF section detection** — Related Work, Background, References patterns
- [ ] **Graph UI paper sidebar** — preview cards instead of CGC file tree
- [x] **MCP graph neighborhood tools** — `get_paper_neighbors`, `expand_paper_graph`
- [x] **MCP search entry** — `search_papers`
- [x] **Paper identity v0.6** — UUID registry + stable IDs
- [x] **MCP full tool tests** — contract + agent workflows + `litgraph test-mcp`
- [ ] **Team sharing** — multi-user graph, shared `.litgraph` or remote DB
- [ ] **MCP `watch_papers_directory`** (optional)

---

## Migrating to v0.6 (UUID paper_id)

Re-index required (no migrate script):

```bash
rm -rf .litgraph/cache/parsed .litgraph/cache/extracted .litgraph/cache/files.json \
  .litgraph/db .litgraph/paper_id_map.json
litgraph scan && litgraph parse --all && litgraph extract -y && litgraph build
# Restart MCP server
litgraph test-mcp   # verify all tools
```

`parse --all` is required after clearing caches so files are parsed even when the hash cache reports no changes.

---

## Future expansion — beyond papers

Planned after v1.0 stabilizes the paper workflow. Same graph schema and MCP surface; new ingest adapters.

- [ ] **Web pages and documentation**
- [ ] **Experiment result CSVs**
- [ ] **Code repos**
- [ ] **Slides and notebooks**

---

## Out of scope (for now)

- Free-form knowledge graph
- Full PDF layout reconstruction
- Related work draft generation inside LGC
- Pre-computed research gap clustering
- Graphiti framework as a runtime dependency
