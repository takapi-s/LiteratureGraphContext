# LiteratureGraphContext Roadmap

> **Current version**: 0.1.0 (MVP)  
> **Last updated**: 2026-07

This document tracks implemented features, known limitations, and planned work.  
For the original design spec, see [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md).

---

## Implemented (v0.1)

### Pipeline

- [x] CLI (`litgraph`) — init, scan, parse, extract, build, query, serve-mcp
- [x] Per-project config (`.litgraph/config.yaml`, `.env`)
- [x] Papers folder configuration (`papers_dir`, scan auto-save, `config set`)
- [x] File scanner with SHA-256 hash cache (incremental processing)
- [x] PDF parser (PyMuPDF) + heuristic section splitter
- [x] Markdown paper notes parser (heading-based sections)
- [x] BibTeX metadata parser (lightweight) + PDF linking at build
- [x] LLM extraction (OpenAI / Anthropic / Gemini / Ollama)
- [x] Pydantic schema validation with evidence fields
- [x] External API send confirmation (`--yes` to skip)
- [x] Entity normalizer via `aliases.yaml` (manual aliases)
- [x] KuzuDB graph storage
- [x] Graph build from extracted JSON + bib metadata merge

### Query & MCP

- [x] CLI query — papers, limitations, compare
- [x] MCP stdio server + `mcp setup`
- [x] MCP tools: `list_papers`, `summarize_paper`, `find_papers_by_method`, `find_papers_by_task`, `find_limitations`, `get_evidence_for_claim`, `compare_papers`

### Graph schema (minimal)

- [x] Nodes: Paper, Task, Method, Dataset, Metric, Claim, Contribution, Limitation, Evidence
- [x] Paper metadata from bib: authors, venue, doi
- [x] Edges: TARGETS, USES, EVALUATES_ON, EVALUATES_WITH, HAS_CLAIM, HAS_CONTRIBUTION, HAS_LIMITATION, SUPPORTED_BY, etc.

---

## Known limitations (v0.1)

These work but are simplified or incomplete relative to the full design.

| Area | Limitation |
|---|---|
| PDF parsing | Heuristic section detection only; complex layouts may fail |
| `compare_papers` | task / method / dataset / limitation only; no metric, contribution, difference columns with evidence |
| Entity normalizer | Manual `aliases.yaml` only; no fuzzy similarity matching |
| Background jobs | `extract --background` returns job_id but no `check_job_status` / progress CLI |
| MCP server | Hand-rolled stdio JSON-RPC; no SSE / official MCP SDK transport |
| MCP setup | Writes `mcp.json` only; no interactive wizard |
| Response limits | `MAX_TOOL_RESPONSE_TOKENS` defined but not fully enforced in server |
| `graph.json` export | Nodes only; edges not exported |
| bib parser | Lightweight regex parser; nested braces and complex BibTeX may fail |
| md parser | Single-paper notes only; no multi-paper literature review document splitting |
| Graph schema | Author / Venue are Paper properties, not separate nodes |
| CLI query | No `summarize_paper` or `get_evidence_for_claim` subcommands (MCP only) |
| Tests | No E2E test with live LLM API |

---

## v0.2 — Graph enrichment & input formats

Priority: strengthen literature graph coverage and metadata.

### MCP tools (Phase 9 partial)

- [ ] `compare_papers` — full comparison table (metric, contribution, difference) with evidence
- [ ] `build_literature_matrix` — topic-based literature matrix generation

### BibTeX & citations

- [ ] Robust BibTeX parser (nested braces, common entry types)
- [ ] `Paper -[:CITES]-> Paper` edges from bib / PDF references
- [ ] `.bib`-only papers (metadata-only nodes when no PDF exists) — optional

### External integrations

- [ ] Semantic Scholar API (metadata, citation lookup)
- [ ] Improved entity normalizer (fuzzy matching + similarity suggestions)

### Jobs & cache

- [ ] `check_job_status` / `list_jobs` (CLI + MCP)
- [ ] Extraction progress reporting for `--background`

### Already done in v0.1 (moved from original v0.2 plan)

- ~~KuzuDB~~ — implemented
- ~~BibTeX basic support~~ — metadata-only implemented
- ~~aliases.yaml~~ — implemented

---

## v0.3 — Advanced storage & integrations

### Database

- [ ] Neo4j backend (optional, via `GraphQueryInterface`)
- [ ] DB factory pattern cleanup for multi-backend switching

### Visualization & tools

- [ ] Graph visualization (Web UI or export)
- [ ] Zotero library import / sync

### Graph reasoning

- [ ] `Paper -[:CONTRASTS_WITH]-> Paper` inference
- [ ] `Paper -[:EXTENDS]-> Paper` inference
- [ ] Author / Venue as first-class nodes (AUTHORED_BY, PUBLISHED_IN)

---

## v0.4 — Literature review automation

### MCP tools (Phase 10–11)

- [ ] `find_research_gaps` — cluster limitations into gap candidates with evidence
- [ ] `generate_related_work_outline` — related work section outline by topic
- [ ] Related work draft generation (LLM-assisted, graph-grounded)

### Analysis

- [ ] Research gap clustering (limitation similarity)
- [ ] Literature matrix auto-generation from graph queries
- [ ] Improved local LLM defaults and model recommendations

---

## v1.0 — Production OSS

- [ ] MCP server stabilization (SDK-based transport, error handling, tool limits)
- [ ] GUI / Web UI for browsing papers and graph
- [ ] Team sharing (multi-user graph, shared `.litgraph` or remote DB)
- [ ] Comprehensive documentation and tutorial
- [ ] Release on PyPI with stable API

---

## Out of scope (for now)

Per the implementation plan, these remain future or explicit non-goals:

- Experiment result CSVs, code repos, slides, notebooks as input
- Free-form knowledge graph (fixed literature-review schema only)
- Full PDF layout reconstruction
- Real-time file watching (watchdog incremental index) — CGC-style

---

## Suggested next steps

If continuing development, recommended order:

1. **Full `compare_papers`** — highest value for literature review workflows
2. **`find_research_gaps`** — core differentiator vs plain PDF RAG
3. **CITES edges from bib** — enables citation graph queries
4. **Job status API** — improves `extract` UX for large paper sets
5. **Semantic Scholar integration** — richer metadata without manual bib curation
