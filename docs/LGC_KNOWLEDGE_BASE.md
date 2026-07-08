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
- **Images and other assets for those tools**: keep next to the tool under `playground/` (e.g., `playground/idea_matrix/assets/`)

This makes it easy to evolve the UI without polluting `docs/` rendering workflows.

---

## IDEA Matrix

- **Viewing**: `ROADMAP.md` embeds the editor with an iframe.
- **Editing**: open
  - `playground/idea_matrix/idea_matrix.html`

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
- `ROADMAP.md` embeds the editor via an `iframe`.

Editing:
- `playground/idea_matrix/idea_matrix.html`

Interaction model:
- X axis: **Difficulty** (`Low` → `Medium` → `High`)
- Y axis: **Impact** (`High` → `Medium` → `Low`)
- The editor allows continuous placement, but grid buckets roughly map to:
  - Difficulty buckets (editor viewBox x ranges): `Low` ~[80, 440], `Medium` ~[440, 800], `High` ~[800, 1160]
  - Impact buckets (editor viewBox y ranges): `High` ~[90, 296.7], `Medium` ~[296.7, 503.3], `Low` ~[503.3, 710]

Editing actions:
- Drag dots to re-position.
- Click a dot (or right-side list item) to select it.
- Edit `Name`, `Notes`, and `Color` in the right pane.
- Use `Download JSON` / `Copy JSON` / `Import JSON`.

JSON format:
```json
{
  "ideas": [
    { "id": "I01", "name": "...", "notes": "...", "color": "green", "x": 130, "y": 135 }
  ]
}
```

Notes:
- `x`/`y` are stored in the editor SVG `viewBox` coordinate space:
  - `x`: 0..1200 (clamped ~90..1150)
  - `y`: 0..800 (clamped ~110..690)
- `id` is stable like `I01`, `I02`, ...
- `color` is one of `green`, `amber`, `red`, `blue`, `purple`, `pink`, `gray`.

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

