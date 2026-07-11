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
- Interpreting LGC MCP tools: `list_papers`, `search_papers`, `summarize_paper`, `compare_papers`, `find_limitations`, `explore_paper_graph`.
- Drafting related work from graph context (compare + limitations + evidence; prose and gap interpretation stay with the MCP client).

## Design philosophy

LGC is a **structured evidence layer**, not an agent that writes related work or pre-computes research gaps.

- **LGC owns**: graph connections (CITES, CONTRASTS_WITH, EXTENDS), evidence-backed facts (`paper_id`, page, section, `evidence_text`), and MCP tools that return structured data.
- **The connected agent owns**: interpreting limitations as gaps, drafting prose, open-ended synthesis.

A typical agent flow for literature questions:

```text
search_papers("ambiguous topic")   # always first for discovery
→ summarize_paper(paper_id)        # details + claims with evidence
→ compare_papers([paper_ids])
→ find_limitations(topic=...) or find_limitations(paper_id=...)
→ explore_paper_graph(paper_id, hops=1|2)
→ agent synthesizes, citing paper_id / title / page / evidence_text
```

## Core workflow

1. **Install**: `pip install -e ".[dev]"` (from repo) or `pip install literature-graph` when published.
2. **Setup** (preferred): `litgraph setup --papers-dir ./my-papers` — interactive project / LLM / keys / optional Zotero / MCP / first index.  
   Or: `litgraph init --papers-dir ./my-papers` then `litgraph index -y`. API keys in `~/.litgraph/.env` (preferred) or repo `.env`. Run `litgraph doctor` if project resolution looks wrong.
3. **Index pipeline** (run from an initialized project directory):
   ```bash
   litgraph index -y     # scan → parse → extract → build
   # or step-by-step:
   litgraph scan && litgraph parse && litgraph extract -y && litgraph build
   ```
4. **Query**: CLI (`litgraph query …`) or MCP after `litgraph setup` / `litgraph mcp setup` and registering `litgraph serve-mcp`.

**Entity resolution (v0.7):** extract uses canonical English + `entity_catalog.json`; build merges synonyms via fuzzy match (A) and optional LLM disambiguation (B). `aliases.yaml` is no longer used. Re-index with `litgraph extract --force -y && litgraph build` after upgrading.

Supported inputs under `papers_dir`: `.pdf` (full pipeline), `.md` (notes), `.bib` (metadata only).

## MCP setup (short)

- Run `litgraph setup` (or `litgraph mcp setup`) to write MCP config for Cursor / Claude Desktop.
- Server entry runs `litgraph serve-mcp` with `LITGRAPH_PROJECT_ROOT` pointing at the repo.
- CLI and MCP must share the same initialized project (same `.litgraph/`).
- `~/.litgraph` is global config only—not a project. Do not run `litgraph scan` from `$HOME`.
- Run `litgraph doctor` to diagnose project resolution or legacy data under `~/.litgraph`.
- After upgrading LGC, restart the MCP server so Cursor picks up tool list changes.

## MCP tools (v0.7 — 6 tools)

| Tool | Use for |
|---|---|
| `list_papers` | All indexed papers |
| `search_papers` | Natural-language entry: returns `paper_id`, title, score, match_reason. Use `center_paper_id` to boost papers near a seed in the citation graph. |
| `summarize_paper` | One paper by `paper_id` (tasks, methods, datasets, contributions, limitations, **claims** with evidence) |
| `compare_papers` | Side-by-side comparison of multiple papers |
| `find_limitations` | Limitations by `topic` and/or `paper_id` (with evidence) |
| `explore_paper_graph` | Graph neighbors from a seed paper: `hops=1` for direct neighbors, `hops>=2` for multi-hop lineage |

**CLI-only (removed from MCP in v0.7):** `find_papers_by_method/task` → `litgraph query papers --method/--task`; `build_literature_matrix` → `litgraph query matrix`; jobs → `litgraph jobs`. Old MCP tool names return a redirect JSON with the replacement hint.

## Agent behavior

- Run **`litgraph index`** (or scan → parse → extract → build) before deep graph queries if the user has not indexed yet.
- **`extract` calls an external LLM**; confirm or use `litgraph extract -y` only when appropriate. Already-extracted papers are skipped unless `--force`.
- When answering from graph data, **cite `paper_id`, title, page, section, and `evidence_text`** when available.
- Related work **draft prose** and **gap interpretation** are out of scope for LGC; use `compare_papers`, `find_limitations`, and `explore_paper_graph` as context for the client model.
- `litgraph watch` defaults to scan → parse → build (no LLM); pass `--auto-extract` for full pipeline on file changes (confirmation auto-skipped). Changes queue while a batch is processing.
- Optional: `litgraph viz` for local graph UI; `litgraph test-mcp` to smoke-test all MCP tools; `litgraph import zotero-sync --with-pdfs` for Zotero Web API + PDF ingest.

## References in this repo

- CLI entry: `litgraph.cli.main`
- MCP server and tools: `litgraph.mcp.server`, `tool_definitions.py`, `tool_service.py`
- User docs: `README.md`, `docs/TUTORIAL.md`
