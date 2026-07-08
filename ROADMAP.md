# LiteratureGraphContext Roadmap

> **Current version**: 0.7.0  
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

## Experimental ideas (hard/uncertain)

Ideas that are not yet hard-committed are tracked on an **Impact × Difficulty** matrix.

See `docs/LGC_KNOWLEDGE_BASE.md` for IDEA Matrix semantics, interaction model, and JSON format.

Open the interactive matrix in `playground/idea_matrix/idea_matrix.html`.

<iframe
  src="playground/idea_matrix/idea_matrix.html"
  style="width:100%; height:520px; border:1px solid #e5e7eb; border-radius:12px; background:#ffffff;"
></iframe>

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
| **Entity resolution** | Duplicate Method/Task nodes from extract variance | **Done (v0.7):** English canonical names + catalog fuzzy merge (A) + optional LLM disambiguation (B); `aliases.yaml` removed |

### By design (not limitations — delegated to agent)

| Area | Note |
|---|---|
| **Research gap clustering** | Use `find_limitations` + `compare_papers`; agent interprets gaps |
| **Related work prose** | `generate_related_work_outline` is optional sugar |

### Active — MCP tool surface (too many tools)

v0.6 exposes **14 MCP tools**. Agents must choose among overlapping entry points (`search_papers` vs `find_papers_by_method` / `find_papers_by_task` vs `build_literature_matrix`; `get_paper_neighbors` vs `expand_paper_graph`). Evaluation showed agents pick the wrong tool or call redundant tools. **Target for v0.7: 6–8 core query tools**; ingest/job ops stay CLI-only.

#### Problem

| Issue | Example |
|---|---|
| **Redundant discovery** | `find_papers_by_task("traffic flow prediction")` → 0 hits; `search_papers` → 8+ hits (keyword + embedding). Task/method tools are already internal channels of `search_papers`. |
| **Split graph traversal** | `get_paper_neighbors` (1-hop) and `expand_paper_graph` (multi-hop) differ only by `hops`. |
| **Agent sugar in LGC** | `generate_related_work_outline` drafts prose — delegated to the connected agent by design. |
| **Ingest ops on MCP** | `list_jobs` / `check_job_status` are pipeline admin, not literature queries. |
| **Narrow evidence lookup** | `get_evidence_for_claim` serves claim IDs agents rarely have without `summarize_paper` first. |

#### Consolidation plan (v0.7)

| Action | Tools | Replacement / note |
|---|---|---|
| **Keep (core)** | `search_papers`, `summarize_paper`, `compare_papers`, `find_limitations`, `list_papers` | Primary agent workflow: discover → detail → compare → limitations |
| **Merge** | `get_paper_neighbors` + `expand_paper_graph` | Single `explore_paper_graph(paper_id, hops=1, relationships?, include_summary?)` — `hops=1` replaces neighbors |
| **Deprecate → CLI only** | `find_papers_by_method`, `find_papers_by_task` | Keep as `litgraph query` subcommands; remove from MCP. `search_papers` covers discovery; optional `search_mode: method \| task` for exact Task/Method node lookup |
| **Deprecate → CLI only** | `build_literature_matrix` | Matrix rows available via `compare_papers` on `search_papers` results, or `litgraph query matrix` |
| **Remove from MCP** | `generate_related_work_outline` | Agent drafts from `compare_papers` + `find_limitations` context (same rationale as removed `find_research_gaps`) |
| **Remove from MCP** | `list_jobs`, `check_job_status` | Background extract status via CLI (`litgraph jobs`); not part of literature Q&A |
| **Fold or defer** | `get_evidence_for_claim` | Return `claims` + evidence inside `summarize_paper`; drop standalone tool unless claim-level search is needed |

**Target MCP surface (7 tools):** `list_papers`, `search_papers`, `summarize_paper`, `compare_papers`, `find_limitations`, `explore_paper_graph` (merged), and optionally one ingest helper if watch/sync lands.

#### Migration steps

1. **v0.7.0** — Add `explore_paper_graph`; mark `get_paper_neighbors` / `expand_paper_graph` deprecated in tool descriptions.
2. **v0.7.x** — MCP server registers reduced tool set; deprecated names return a redirect message with the replacement tool name for one minor release.
3. **v0.8.0** — Remove deprecated MCP tools; keep CLI equivalents (`litgraph query method`, `task`, `matrix`, `neighbors`, `expand`).
4. **Docs** — Update Cursor skill, MCP instructions, and `litgraph test-mcp` smoke cases to the reduced set.

#### Success criteria

- Agent smoke workflows (`search → summarize → compare → limitations → graph`) pass with ≤ 7 MCP tools.
- No regression in discovery quality vs current `search_papers` + `expand_paper_graph` path.
- `litgraph test-mcp` covers the reduced contract only.

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

## v0.7 — MCP tool consolidation

- [x] **`explore_paper_graph`** — merge `get_paper_neighbors` + `expand_paper_graph` (`hops` parameter)
- [x] **Deprecate attribute search on MCP** — `find_papers_by_method`, `find_papers_by_task` → CLI only (redirect on old MCP names)
- [x] **Remove agent-sugar tools from MCP** — `generate_related_work_outline`, `build_literature_matrix`
- [x] **Remove ingest tools from MCP** — `list_jobs`, `check_job_status` → CLI only
- [x] **Fold claim evidence** — `get_evidence_for_claim` into `summarize_paper`
- [x] **Update MCP tests & skill** — `test-mcp`, smoke cases, Cursor skill to 6 tools
- [x] **Entity resolution** — `entity_catalog.json` + build-time resolver (A/B); `aliases.yaml` removed

v0.7.0 uses a **big-bang** cut to **6 MCP query tools**; removed tool names return a one-release redirect JSON (not listed in `tools/list`).

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
