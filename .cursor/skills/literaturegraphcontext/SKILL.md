---
name: literaturegraphcontext
description: >-
  Use LiteratureGraphContext (LGC) to index paper PDFs into a literature
  knowledge graph and query via CLI or MCP. Apply when the user wants literature
  review, related work, paper comparison, graph neighbors, or configuring the
  litgraph MCP server.
---

# LiteratureGraphContext (LGC)

## When to use this skill

- Setting up or refreshing a papers folder into a queryable literature graph.
- Explaining `litgraph` CLI, `.litgraph` config, or MCP wiring in Cursor.
- Interpreting LGC MCP tools: `list_papers`, `find_limitations`, `get_paper_neighbors`, `build_literature_matrix`, etc.
- Drafting related work from graph context (outline + matrix + evidence; prose and gap interpretation stay with the MCP client).

## Design philosophy

LGC is a **structured evidence layer**, not an agent that writes related work or pre-computes research gaps.

- **LGC owns**: graph connections (CITES, CONTRASTS_WITH, EXTENDS), evidence-backed facts (`paper_id`, page, section, `evidence_text`), and MCP tools that return structured data.
- **The connected agent owns**: interpreting limitations as gaps, drafting prose, open-ended synthesis.

A typical agent flow for literature questions:

```text
search_papers("ambiguous topic")   # always first for discovery
→ compare_papers([paper_ids])
→ summarize_paper(paper_id)        # details from search result IDs
→ find_limitations(topic=...) or find_limitations(paper_id=...)
→ get_paper_neighbors(paper_id)
→ agent synthesizes, citing paper_id / title / page / evidence_text
```

## Core workflow

1. **Install**: `pip install -e ".[dev]"` (from repo) or `pip install literature-graph` when published.
2. **Configure**: `litgraph init --papers-dir ./my-papers`. API keys in `.env` or `~/.litgraph/.env` (`LLM_PROVIDER`, `OPENAI_API_KEY`, etc.).
3. **Index pipeline** (run from project root):
   ```bash
   litgraph scan          # hash cache
   litgraph parse         # PDF / .md / .bib → cache
   litgraph extract -y    # LLM structured extract (needs API key; skips cached papers)
   litgraph build         # cache → Kùzu graph
   ```
4. **Query**: CLI (`litgraph query …`) or MCP after `litgraph mcp setup` and registering `litgraph serve-mcp`.

Supported inputs under `papers_dir`: `.pdf` (full pipeline), `.md` (notes), `.bib` (metadata only).

## MCP setup (short)

- Run `litgraph mcp setup` to write `mcp.json` for Cursor / Claude Desktop.
- Server entry runs `litgraph serve-mcp` from the project root so it resolves `.litgraph/`.
- CLI and MCP must share the same project root and graph DB.
- After upgrading LGC, restart the MCP server so Cursor picks up tool list changes.

## MCP tools

| Tool | Use for |
|---|---|
| `list_papers` | All indexed papers |
| `search_papers` | Natural-language entry: returns `paper_id`, title, score, match_reason |
| `summarize_paper` | One paper by `paper_id` |
| `find_papers_by_method` / `find_papers_by_task` | Method or task search |
| `find_limitations` | Limitations by `topic` and/or `paper_id` (with evidence) |
| `get_evidence_for_claim` | Evidence for a `claim_id` |
| `compare_papers` | Side-by-side comparison |
| `build_literature_matrix` | Topic matrix across papers |
| `get_paper_neighbors` | Neighbors via CITES, CITED_BY, CONTRASTS_WITH, EXTENDS (`relationships`, `include_summary` optional) |
| `expand_paper_graph` | Multi-hop BFS from a seed paper (`hops`, `relationships` optional) |
| `generate_related_work_outline` | Section outline with supporting papers |
| `list_jobs` / `check_job_status` | Background `extract --background` jobs |

**Removed:** `find_research_gaps` — use `find_limitations` + `get_paper_neighbors` + `compare_papers`; let the agent interpret gaps.

## Agent behavior

- Run **scan → parse → extract → build** before deep graph queries if the user has not indexed yet.
- **`extract` calls an external LLM**; confirm or use `litgraph extract -y` only when appropriate. Already-extracted papers are skipped unless `--force`.
- When answering from graph data, **cite `paper_id`, title, page, section, and `evidence_text`** when available.
- Related work **draft prose** and **gap interpretation** are out of scope for LGC; use `generate_related_work_outline`, `find_limitations`, `get_paper_neighbors`, and `build_literature_matrix` as context for the client model.
- `litgraph watch` defaults to scan → parse → build (no LLM); pass `--auto-extract` for full pipeline on file changes (confirmation auto-skipped). Changes queue while a batch is processing.
- Optional: `litgraph viz` for local graph UI; `litgraph test-mcp` to smoke-test all MCP tools; `litgraph import zotero-sync` for Zotero Web API bib cache.

## References in this repo

- CLI entry: `litgraph.cli.main`
- MCP server and tools: `litgraph.mcp.server`, `tool_definitions.py`, `tool_service.py`
- User docs: `README.md`, `docs/literature_graph_mcp_implementation_plan.md`
