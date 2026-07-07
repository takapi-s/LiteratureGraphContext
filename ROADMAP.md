# LiteratureGraphContext Roadmap

> **Current version**: 0.4.0  
> **Last updated**: 2026-07

Tracks **remaining work**, known limitations, and out-of-scope items.  
Shipped features through v0.4.x are recorded in git history and [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md).

## Design philosophy

LiteratureGraphContext is a **structured evidence layer**, not an interpretation engine.

| Layer | Responsibility | Examples |
|---|---|---|
| **LGC (data plane)** | Ingest, structure, connect, cite | PDF → graph; `CITES` / `CONTRASTS_WITH`; MCP tools with `evidence_text` |
| **Connected agent** | Interpret, cluster, draft | Research gaps; related work prose; cross-field synthesis |

**Core bet:** multiple studies are properly linked in the graph; MCP returns topic-filtered, evidence-backed facts; the agent answers from that material.

**Intentionally not in LGC:** pre-computed gap clustering, related-work draft generation, embedding-based narrative synthesis. Use `find_limitations`, `compare_papers`, and `build_literature_matrix` as agent context instead.

**Vision:** *Literature* means written sources broadly—not only academic papers. The current focus is PDF-centric literature review, but the long-term goal is to index and graph **any structured knowledge source** (web pages, documentation, technical blogs, etc.) under the same schema-oriented workflow.

---

## Known limitations — and how we address them

Prioritized under the design philosophy above.

### Active (improves graph quality & agent context)

| Area | Limitation | Direction |
|---|---|---|
| **PDF parsing** | Heuristic section detection only | Expand section patterns (Related Work, Background, References, etc.); add parse diagnostics; later block-based heading detection. Goal: better inputs for LLM extract → richer graph nodes. |
| **Graph UI** | CGC Playground fork; paper-centric sidebar not customized | Replace file-tree sidebar with paper preview cards (title, authors, year, methods, claim/limitation counts). Click → highlight subgraph. Visualization of graph links is part of the product story. |
| **MCP graph traversal** | Tools are mostly attribute search (`by_task`, `by_method`) | Add neighborhood queries (e.g. cited papers, `CONTRASTS_WITH` / `EXTENDS` peers) so agents can follow edges, not only filter by keyword. |

### By design (not limitations — delegated to agent)

| Area | Note |
|---|---|
| **Research gap clustering** | `find_research_gaps` and embedding-based clustering are redundant when agents call `find_limitations` + `compare_papers`. Deprecate or remove `find_research_gaps`; do not invest in embedding gap pipelines. |
| **Related work prose** | `generate_related_work_outline` is optional sugar; agents can build outlines from `summarize_paper` + matrix tools. |

### Deferred (acceptable for now)

| Area | Limitation | When to revisit |
|---|---|---|
| **MCP setup** | Writes `mcp.json` only; no interactive wizard | v1.0 onboarding, if OSS adoption needs it |
| **md parser** | Single-paper notes only | When multi-paper survey notes become a real workflow |
| **Zotero sync** | Web API only; no desktop sqlite | When library sync is a blocker for users |
| **Tests** | No E2E test with live LLM API | Optional CI job or manual smoke; not blocking data-plane work |
| **Neo4j** | No migration tool from Kuzu | When teams standardize on Neo4j at scale |

### Out of scope (unchanged)

| Area | Note |
|---|---|
| **PDF layout** | Full layout reconstruction stays out of scope; heuristic + section expansion is enough |
| **Free-form KG** | Fixed literature-review schema only |

---

## v1.0 — Production OSS

- [ ] **PyPI release** — packaging and stable public API
- [ ] **Documentation and tutorial** — end-to-end guide (init → extract → MCP → viz); emphasize agent + data-plane workflow
- [ ] **PDF section detection** — Related Work, Background, References patterns; parse diagnostics
- [ ] **Graph UI paper sidebar** — preview cards instead of CGC file tree
- [ ] **MCP graph neighborhood tools** — traverse `CITES` / `CONTRASTS_WITH` / `EXTENDS` from a paper
- [ ] **Team sharing** — multi-user graph, shared `.litgraph` or remote DB
- [ ] **MCP `watch_papers_directory`** (optional) — expose file watch via MCP

Removed from v1.0 (per design philosophy):

- ~~Embedding-based gap clustering~~
- ~~MCP setup wizard~~ (deferred)

---

## Future expansion — beyond papers

Planned after v1.0 stabilizes the paper workflow. Same graph schema and MCP surface; new ingest adapters.

- [ ] **Web pages and documentation** — URLs, HTML/Markdown snapshots, site crawls (docs, blogs, reference pages)
- [ ] **Experiment result CSVs** — tabular results linked to papers and claims
- [ ] **Code repos** — methods and implementations tied to cited work
- [ ] **Slides and notebooks** — supplementary materials alongside PDFs

Constraints for all new sources:

- Fixed literature-review schema (not a free-form knowledge graph)
- Provenance preserved (`source_type`, URL/path, fetch date, evidence spans)

---

## Out of scope (for now)

- Free-form knowledge graph (fixed literature-review schema only)
- Full PDF layout reconstruction
- Related work draft generation inside LGC (use MCP client instead)
- Pre-computed research gap clustering (use `find_limitations` + agent)
