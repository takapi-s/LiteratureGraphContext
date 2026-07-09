# LGC Knowledge Base

This repository uses a single source of truth for *accumulated knowledge* (decisions, lessons learned, concrete implementation notes, and “how to do X” guidance):

`docs/LGC_KNOWLEDGE_BASE.md`

If you find new knowledge while working on the project, append it here instead of creating new standalone files under `docs/`.

---

## Docs consolidation policy

1. **All new knowledge goes to this file**
   - Prefer adding a new subsection under the closest existing heading.
   - If the correct heading does not exist, create it here.
2. **Avoid scattering knowledge across many md files**
   - Creating new `docs/*.md` for incremental updates should generally be avoided.
3. **Deprecate old files instead of keeping parallel sources**
   - When a `docs/*.md` becomes redundant, rename it to something like `*.deprecated.md` (or archive it) and update any references.
4. **This file can reference tools and external resources**
   - Linking is fine; duplicating “the same knowledge” is not.

---

## Interactive tools and asset placement

To keep `docs/` focused on documentation (Markdown), interactive dev tools and their assets should live outside `docs/`.

- **Interactive HTML/JS editors**: use `playground/`
- **Diagrams and static assets referenced from docs**: use `docs/assets/` (e.g. draw.io SVG)

This makes it easy to evolve the UI without polluting `docs/` rendering workflows.

---

## IDEA Matrix

- **Viewing**: `ROADMAP.md` embeds `docs/assets/idea_matrix.drawio.svg` as an image (renders on GitHub).
- **Editing**: open `docs/assets/idea_matrix.drawio.svg` in draw.io / diagrams.net, or the VS Code Draw.io extension.

---

## Entry template (append-only)

Use this template when adding new knowledge.

### YYYY-MM-DD - <topic>

- What we learned / decided:
- Why it matters (trade-offs, failure modes, constraints):
- Where it’s implemented (paths / commands / tool names):
- Verification (what to check / how to reproduce):

---

## 2026-07-08 - IDEA Matrix (Impact × Difficulty) details

The repository tracks *hard/uncertain* implementation ideas on a simple **Impact × Difficulty** plot.

Viewing:
- `ROADMAP.md` embeds `docs/assets/idea_matrix.drawio.svg` as a Markdown image (GitHub-compatible).

Editing:
- `docs/assets/idea_matrix.drawio.svg` in draw.io / diagrams.net, or the VS Code Draw.io extension.
- After editing, commit the updated SVG so GitHub shows the latest plot.

Interaction model:
- X axis: **Difficulty** (`Low` → `Medium` → `High`)
- Y axis: **Impact** (`High` → `Medium` → `Low`)
- Grid buckets roughly map to:
  - Difficulty: `Low` (left), `Medium` (center), `High` (right)
  - Impact: `High` (top), `Medium` (middle), `Low` (bottom)

Conventions:
- Each idea is a colored dot labeled `I01`, `I02`, … (titles are **not** shown on the plot to avoid overlap).
- Use the **Idea index** below (also in `ROADMAP.md`) to look up what each ID means.
- Color hints: `green` = quick win, `amber` = medium effort, `red` = hard/high leverage, `blue`/`purple`/`pink` = area themes, `gray` = housekeeping.
- Within the same difficulty/impact cell, dots are stacked vertically so they do not overlap.

### Idea index (I01–I13)

| ID | Idea | Color | Target |
|---|---|---|---|
| I01 | Hybrid search entry (embeddings + keyword + graph) | red | v0.5 ✅ |
| I02 | New inputs: arXiv/URL/Zotero/CSV connectors | red | v0.9, v0.11 |
| I03 | Containment relations: section/subsection + CONTAINS edges | amber | TBD |
| I04 | PDF structure: robust section detection + diagnostics | amber | v0.11 |
| I05 | Citations: merge refs + bib better (CITES quality) | pink | TBD |
| I06 | ID resolution & errors: actionable hints in MCP/CLI | blue | v0.8+ |
| I07 | Auto-generate `paper_id_map` from `paper_registry` | green | TBD |
| I08 | Graph UI: paper-centric sidebar + preview cards | purple | v0.8 |
| I09 | Workspace-scoped graph (`workspace_id` on nodes & queries) | red | v0.10 |
| I10 | Programmatic API (`LitgraphContext`, injectable store) | amber | v0.9 |
| I11 | HTTP MCP transport (remote callers) | blue | v0.12 |
| I12 | Folder watch / auto-ingest (`watch_papers_directory`) | blue | v0.12 |
| I13 | MCP setup wizard (interactive onboarding) | green | v0.8+ |

---

## 2026-07-08 - BysGNN evaluation + LGC/MCP workflow findings

### BysGNN positioning / how to evaluate vs other papers

Key evaluation axes (prefer “design trade-offs” over raw accuracy when datasets differ):
- Research lineage / stage: original BysGNN vs extensions (e.g., POI → grid adaptation) and how evaluation focus changes.
- Task fit: POI visit forecasting vs grid consumption prediction vs traffic sensing tasks.
- Graph design: dynamic adjacency learned from multiple contexts (time, distance, semantics/categories) versus fixed-topology spacetime GNNs.
- Data conditions: differences in dataset availability (e.g., SafeGraph vs project-specific datasets) and regime (small vs large POIs).

Practical guidance:
- When direct numeric comparison is unfair (different datasets like SafeGraph vs TOYOPay), document comparisons as:
  - Conceptual contrasts in architecture and training signals.
  - “Same dataset baseline” needs to be implemented if numeric comparison is desired.

Model-specific notes from the investigation:
- BysGNN’s core is “dynamic graph construction from multiple contexts” plus GCN aggregation (and extensions explore aggregator changes like GAT).
- GCN vs GAT is a natural “next improvement” hypothesis when the aggregation should not behave like near-uniform neighbor mixing.

### LGC/MCP usage: what works well and what does not

Useful MCP/CLI combination (current reality):
- MCP is helpful for fast discovery and generating a table-like comparison “skeleton”.
- CLI (`litgraph query ...`) is more reliable for full outputs / long text / evidence completeness.
- Add a workflow where agent falls back to CLI + PDF when MCP truncates or returns unstable results.

Observed tool behaviors:
- `find_papers_by_task` / `find_papers_by_method`: effective for retrieving candidate `paper_id` using extracted tags.
- `compare_papers`: produces side-by-side comparisons with evidence fields (when reachable).
- `find_limitations`: returns limitations with page/section/evidence fields (good for writing).

Observed limitations:
- Truncation: MCP responses may cut off long outputs (e.g., matrix/table/abstract).
- Data quality issues: some PDFs may be mis-registered (wrong title/field), so “search results” can mislead without verification.

### ID resolution and ambiguity handling (UUID is the stable key)

ID facts:
- Correct `paper_id` is UUID-based in the form `p_<uuid>`.
- File-stem IDs like `02_hajisafi2023_bysgnn` fail in some MCP paths.

Recommended workflow for “ambiguous question → compare papers”:
1. `search_papers("...")` (or tag-based candidate retrieval) → obtain `paper_id` + title
2. `summarize_paper(p_<uuid>)` → get structured summary + claims/limitations/evidence
3. `compare_papers([p_..., p_...])` → generate comparison table

Why a dedicated `search_papers` tool matters:
- The current “entry points” are split across multiple tools; ambiguous natural language questions require multi-step orchestration.
- A single cross-channel search entry is the missing piece to map “what the user asked” to “which `paper_id` to fetch”.

### Graphiti vs LGC: recommended hybrid

Takeaway:
- Adding an embedding-based “search layer” (Graphiti-like approach) is a good way to reduce LGC’s weak spot: mapping ambiguous natural language to the correct `paper_id`.
- Do not replace the whole system with Graphiti-style narrative; keep LGC’s structured evidence (page/section/evidence_text) as the ground-truth for writing.

Suggested design (high level):
- Index-time: embed structured fields (title + tasks + methods + contributions + limitations) and store vectors (alongside existing LGC DB).
- Query-time: `search_papers(query)` uses hybrid retrieval (embedding + keyword + aliases) to return candidate `paper_id` with `score` and `match_reason`.
- Then reuse existing tools: `summarize_paper`, `compare_papers`, `find_limitations` for citation-ready outputs.

---

## 2026-07-09 - Roadmap reprioritization (docs & PDF parsing)

- What we learned / decided:
  - Documentation and tutorial belong at **v1.0**, not v0.8. README quick start is enough until ingest paths (local folder, URL/arXiv, Zotero) stabilize.
  - PDF section detection + diagnostics (I04) moves from v0.8 to **v0.11**, alongside Zotero PDF fetch. Basic patterns already exist in `section_splitter.py`; robustness matters most when PDFs arrive from external sources.
  - v0.8 narrows to **local UX**: MCP setup wizard (I13), ID/error hints (I06), Graph UI sidebar (I08).
- Why it matters (trade-offs, failure modes, constraints):
  - Writing a full tutorial before v0.9–v0.11 lands means rewriting it when API, workspace, and Zotero workflows change.
  - Interactive onboarding (wizard + actionable errors) reduces the need for prose docs during development.
- Where it's implemented (paths / commands / tool names):
  - `ROADMAP.md` — version roadmap and "Current focus (v0.8)" table
  - `docs/LGC_KNOWLEDGE_BASE.md` — idea index I04 target
- Verification (what to check / how to reproduce):
  - `ROADMAP.md` v0.8 has no docs/PDF items; v0.11 lists I04; v1.0 lists docs + PyPI.

---

## 2026-07-09 - Version numbering: 0.12 / 0.13 then 1.0, then 1.x

- What we learned / decided:
  - Pre-PyPI development continues on **0.x** through **0.13** (0.12 = HTTP MCP + watch; 0.13 = source expansion).
  - **1.0** = first PyPI stable release + documentation (after 0.13).
  - Post-1.0 features use **semver minor** starting at **1.1** for unassigned IDEA items (I03, I05, I07, …).
  - **2.0** reserved for breaking API changes (not planned yet).
- Why it matters:
  - Keeps all pre-release milestones in one 0.x line; 1.0 is the public baseline, 1.1+ are incremental post-release updates.
- Where it's implemented:
  - `ROADMAP.md` — `0.7 → … → 0.13 → 1.0 → 1.1+` flow
  - Idea index I11/I12 → v0.12
- Verification:
  - No post-1.0 v1.1/v1.2 sections for HTTP MCP or source expansion; those are v0.12/v0.13 under Pre-1.0.

---

## 2026-07-09 - v0.9–v0.12 implementation shipped

- What we learned / decided:
  - **v0.9:** Public `LitgraphContext` API (`ingest_from_path`, `ingest_from_bytes`, `ingest_from_source_ref`, query wrappers) + `source_ref` adapters (file, bytes, URL, arXiv, Zotero).
  - **v0.10:** `workspace_id` on all Kuzu nodes/queries; cache at `.litgraph/cache/{workspace}/`; CLI `--workspace` and `LITGRAPH_WORKSPACE`; legacy `cache/` fallback for `default`.
  - **v0.11:** `litgraph import zotero-sync --with-pdfs`, PDF fetch via Zotero Web API, dedup (`zotero_key` → DOI → `content_hash`), PDF section regex `finditer` + block offset fix.
  - **v0.12:** `litgraph serve-mcp --http`, MCP tool `watch_papers_directory` (subprocess `litgraph watch`).
- Where it's implemented:
  - `src/litgraph/context.py`, `src/litgraph/ingest/`, `src/litgraph/utils/workspace.py`, `src/litgraph/graph/kuzu_store.py`, `src/litgraph/integrations/zotero.py`, `src/litgraph/mcp/server.py`, `src/litgraph/mcp/watch_manager.py`
- Verification:
  - `python3 -m pytest tests/ --ignore=tests/test_watch.py` (or full suite ~7min)
  - `litgraph serve-mcp --http --port 8000`
  - `from litgraph import LitgraphContext`
