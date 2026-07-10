# LiteratureGraphContext Roadmap

> **Current version**: 0.12.0  
> **Last updated**: 2026-07

Remaining OSS (`literature-graph` on PyPI) tasks and known constraints. For implementation history before v0.5, see [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md).

## Design philosophy

LGC is a **structured evidence layer** (not an interpretation engine).

| Layer | Role | Example |
|---|---|---|
| **LGC (data plane)** | Ingestion, structuring, linking, citation | PDF → graph; `CITES` / `CONTRASTS_WITH`; MCP returns `evidence_text` |
| **Connecting agent** | Interpretation, clustering, writing | Research gaps; Related Work drafts; cross-cutting synthesis |

**Core:** Connect multiple papers correctly in a graph, have MCP return topic-filtered evidence-backed facts, and let agents answer based on that.

**Not in LGC:** Pre-clustering gaps, Related Work draft generation, embedding-based narrative synthesis. Instead, use `find_limitations` / `compare_papers` / `build_literature_matrix` as agent context.

**Search layer (in scope):** `search_papers` (keyword + embedding hybrid), `explore_paper_graph` (multi-hop lineage), immutable UUID `paper_id`.

**Vision:** *Literature* is not limited to academic papers long-term, but **current work stays on structuring academic PDFs**—better sections, citations, claims, and evidence in the graph.

---

## Current focus (v0.13)

**Approach:** Improve how a single paper is parsed, sectioned, extracted, and linked in the graph. Write documentation in one pass at v1.0.

| Priority | Item | Rationale |
|---|---|---|
| ✅ | v0.9 API & ingest | `LitgraphContext` + ingest adapters complete |
| ✅ | v0.10 workspace | `workspace_id` scoping complete |
| ✅ | v0.11 Zotero + PDF | Full pipeline + PDF section improvements complete |
| ✅ | v0.12 Remote MCP & watch | HTTP MCP + `watch_papers_directory` complete |
| 1 | v0.13 Paper structuring | Section hierarchy, citation linking, extraction quality, evidence grounding |
| Last | v1.0 docs + PyPI | Write once after v0.13 + workflows are settled |
| Later | v1.1, v1.2, … | Post-1.0 feature additions via semver minor |

**v0.13 scope** (in recommended order — measure first, then improve):

| Area | Status | Next |
|---|---|---|
| Golden set (regression bench) | Not started | Fixed expected sections / citation pairs / evidence `page`+`section` for `examples/papers/`; pytest diff so I03–I05 progress is measurable |
| PDF section detection | Basics done (v0.11, I04) | Edge cases, subsection hierarchy (I03) |
| PDF section diagnostics | Not started | Failure modes, confidence, repair hints; compare against GROBID / docling on the golden set before hardening the in-house splitter (I04) |
| Citation graph | refs + bib merge done (`merge_citation_pairs`) | Resolution *accuracy*: title fuzzing, DOI / arXiv IDs, optional Semantic Scholar lookup (`integrations/semantic_scholar.py`) with offline fallback (I05) |
| Embedding storage | JSON sidecar (`embeddings.json`, full load + O(n) Python cosine) | Move vectors into the graph store as node properties (I15): Kuzu `FLOAT[]` + vector index (HNSW extension); Neo4j parity via array property + native vector index. Fixes ghost vectors after `rm -rf .litgraph/db` and unblocks section-level scale |
| Section containment | Not started | `CONTAINS` edges for section / subsection + section-level embeddings in the same pass, stored in-graph via I15 (avoids a second re-index) (I03) |
| Extraction quality | Active | Contributions, limitations, methods, tasks with reliable `page` / `section` / `evidence_text` |
| Claim-level structure | Deferred | Paper-level embeddings only today; claim nodes later |

---

## Experimental ideas (Impact × Difficulty)

Uncommitted, uncertain ideas. Edit `docs/assets/idea_matrix.drawio.svg` (draw.io / VS Code Draw.io extension). For semantics, see [docs/LGC_KNOWLEDGE_BASE.md](docs/LGC_KNOWLEDGE_BASE.md).

![IDEA Matrix](docs/assets/idea_matrix.drawio.svg)

| ID | Idea | Target |
|---|---|---|
| I01 | Hybrid search entry (embeddings + keyword + graph) | v0.5 ✅ |
| I02 | New inputs: arXiv / URL / Zotero connectors ✅ — CSV not implemented | v0.9, v0.11 ✅ / CSV → v1.1 candidate |
| I03 | Containment: section / subsection + `CONTAINS` edges (+ section embeddings) | v0.13 |
| I04 | PDF structure: robust section detection + diagnostics | detection v0.11 ✅ / diagnostics v0.13 |
| I05 | Citations: `CITES` resolution accuracy (external IDs) — refs+bib merge shipped | v0.13 |
| I06 | ID resolution & errors: actionable hints in MCP / CLI | v0.8 ✅ |
| I07 | Auto-generate `paper_id_map` from `paper_registry` | v1.1 candidate |
| I08 | Graph UI: paper-centric sidebar + preview cards | v0.8 ✅ |
| I09 | Workspace-scoped graph (`workspace_id` on nodes & queries) | v0.10 ✅ |
| I10 | Programmatic API (`LitgraphContext`, injectable store) | v0.9 ✅ |
| I11 | HTTP MCP transport (remote callers) | v0.12 ✅ |
| I12 | Folder watch / auto-ingest (`watch_papers_directory`) | v0.12 ✅ |
| I13 | MCP setup wizard (interactive onboarding) | v0.8 ✅ |
| I14 | Zotero write-back: push extracted limitations / comparisons to Zotero tags & notes | v1.1 candidate |
| I15 | In-graph embeddings: vectors as node properties + vector index (Kuzu HNSW / Neo4j), retire `embeddings.json` | v0.13 |

---

## Known limitations

| Area | Status | Direction |
|---|---|---|
| Paper identity (slug ID changes on re-extract) | **Done (v0.6)** | UUID + `paper_registry.json` |
| Search entry (attribute search only) | **Done (v0.5)** | `search_papers` |
| Graph traversal (1-hop only) | **Done (v0.5)** | `explore_paper_graph` |
| MCP contract tests | **Done (v0.6)** | `litgraph test-mcp` |
| Entity resolution (duplicate Method/Task) | **Done (v0.7)** | catalog fuzzy merge + optional LLM |
| MCP tool surface (14 → 6 tools) | **Done (v0.7)** | 6 core query tools; ingest is CLI-only |
| PDF parsing | **Active (v0.13)** | Harden section detection, diagnostics, edge cases (I04) |
| Graph UI | **Done (v0.8)** | Paper sidebar + type-specific preview cards (I08) |
| MCP stability | Planned (v1.0 docs) | Document single-writer policy for Kuzu |
| Zotero | **Done (v0.11)** | Full PDF pipeline shipped |
| Embedding store (JSON sidecar, full load + O(n) cosine) | **Active (v0.13)** | In-graph vectors + vector index, Kuzu & Neo4j (I15) |
| md parser | Deferred | Single-paper notes only |
| Neo4j migration | Deferred | No migration tool from Kuzu |
| Claim-level embeddings | Deferred | Paper-level embeddings only |

**Intentionally delegated to agents:** Gap clustering, Related Work drafts via `generate_related_work_outline`.

---

## Version roadmap

**Versioning policy**

| Series | Meaning |
|---|---|
| **0.x** | Pre-PyPI development releases (current: 0.12.0 → 0.13) |
| **1.0** | First stable PyPI release + documentation |
| **1.x** | Feature additions after 1.0 (semver minor) |
| **2.0** | When breaking API changes are required (TBD) |

```text
0.7 ✅ → … → 0.12 ✅ → 0.13 → 1.0 → 1.1 → …
  │                         │       │
  └─ pre-PyPI development   └─ now  └─ post-1.0 expansion
```

### Pre-1.0 (0.x)

#### v0.7 — MCP tool consolidation ✅

- [x] `explore_paper_graph` — merge `get_paper_neighbors` + `expand_paper_graph`
- [x] Remove attribute search, matrix, Related Work drafts, job management from MCP → CLI
- [x] Merge `get_evidence_for_claim` into `summarize_paper`
- [x] Update MCP tests & Cursor skill for 6 tools
- [x] Entity resolution (`entity_catalog.json` + build-time resolver)

#### v0.8 — Local UX ✅

Do not write documentation before features stabilize. Supplement onboarding with wizard and CLI hints.

- [x] Project resolution fix — `~/.litgraph` excluded from walk-up; `litgraph init` required; `litgraph doctor` (I06)
- [x] MCP setup wizard — `litgraph mcp setup` interactive flow (init / LLM / API key / client config) (I13)
- [x] Graph UI paper sidebar — type-specific preview cards in detail panel; `contribution_count` (I08)
- [x] ID / error hints — registry resolution, `did_you_mean` + `hint`, `compare_papers` `missing_ids`, MCP startup crash avoidance (I06)

#### v0.9 — Programmatic API & ingest ✅

- [x] Injectable execution context — `LitgraphContext`, cache paths, config independent of cwd (I10)
- [x] Programmatic ingest API — `ingest_from_path` / `ingest_from_bytes`
- [x] Ingest adapters — `source_ref` plugins (local folder, bytes, URL / arXiv) (I02)

#### v0.10 — Workspace-scoped graph ✅

- [x] `workspace_id` on nodes — filter on all build / query paths; `(workspace_id, paper_id)` unique (I09)
- [x] Default workspace — `default` when omitted (single `.litgraph` workflow remains compatible)
- [x] CLI / MCP context — `--workspace` / `LITGRAPH_WORKSPACE` / `LitgraphContext(workspace_id=...)`

#### v0.11 — Zotero full pipeline ✅

**Shipped**

- [x] JSON export import — `litgraph import zotero <export.json>`
- [x] Web API bib sync — `litgraph import zotero-sync`

**Remaining**

- [x] Zotero ingest adapter — `source_ref: zotero://{library}/{item_key}` (I02)
- [x] `zotero_key` on Paper nodes — `(workspace_id, zotero_key) → paper_id`
- [x] PDF attachment fetch — fetch PDF via Web API → parse → extract → build
- [x] Full pipeline sync — `litgraph import zotero-sync --with-pdfs`
- [x] Collection filter — `--collection` (existing) + workspace combination
- [x] Dedup — match existing papers via `zotero_key` / DOI / `content_hash`
- [x] PDF section detection — regex full match + block offset fix (I04)

#### v0.12 — Remote MCP & watch ✅

- [x] HTTP MCP transport — `litgraph serve-mcp --http` (I11)
- [x] MCP `watch_papers_directory` — folder watch subprocess management (I12)

#### v0.13 — Paper structuring

Improve parse → section → extract → build for academic PDFs. Same graph schema and MCP surface (plus Section nodes / `CONTAINS`); no new ingest adapters.

- [ ] Golden set first — expected sections / citations / evidence for `examples/papers/`, enforced in pytest; every item below is measured against it
- [ ] PDF section diagnostics — failure modes, confidence, repair hints; benchmark GROBID / docling vs in-house splitter on the golden set to decide how far to push the custom parser (I04)
- [ ] Citation resolution accuracy — title fuzzing + DOI / arXiv IDs, optional Semantic Scholar lookup with offline fallback; merge itself already ships in `graph_builder.py` (I05)
- [ ] In-graph embeddings (I15) — store vectors as node properties instead of `cache/{ws}/embeddings.json`:
  - Kuzu (default): `FLOAT[]` property + vector index (HNSW extension) for similarity search
  - Neo4j (optional backend): array property + native vector index, behind the same store interface
  - Search path: replace full-JSON load + Python cosine in `query/embedding_store.py` with store-side queries
  - Lifecycle: vectors live and die with the graph — no more stale "ghost" vectors after DB re-index
  - Keep out of the graph store: `paper_registry.json` (identity must survive DB wipe) and `cache/parsed` / `cache/extracted` (LLM-cost pipeline caches)
- [ ] Section / subsection hierarchy — `CONTAINS` edges + section-level embeddings in the same re-index, stored in-graph via I15 (I03)
- [ ] Extraction grounding — reliable `page` / `section` / `evidence_text` on claims, limitations, contributions

**Migration:** v0.13 requires a re-index (same policy as v0.6 / v0.10): Section nodes, `CONTAINS` edges, and in-graph vectors are populated at build time; legacy `embeddings.json` is read once as a fallback and can be deleted afterwards.

### 1.0 — PyPI release & documentation

Once v0.13 and core workflows are solid, document the full flow.

- [ ] Documentation and tutorial — `setup` / `index` → MCP → viz → Zotero; include Kuzu single-writer policy (closes the "MCP stability" limitation)
- [ ] Quickstart smoke test in CI — run the README command sequence so docs can't rot silently
- [ ] Onboarding polish — `litgraph setup` + `litgraph index` shipped; keep docs aligned as workflows settle
- [ ] Repo hygiene — remove `external/` reference clones (zotero / graphiti / CodeGraphContext; zero code references, link from docs instead); stop tracking `website/node_modules` and `dist/` tarballs
- [ ] CI hardening — coverage reporting; PyPI publish workflow (trusted publishing)
- [ ] PyPI release — packaging and semver-stable programmatic API

### Post-1.0 (1.x)

#### v1.1+ — TBD

Assign remaining IDEA Matrix items in 1.x — e.g. I07 (`paper_id_map` auto-gen), CSV connector (I02 remainder), I14 (Zotero write-back), claim-level embeddings.

---

## Out of scope

- Free-form knowledge graphs (literature-review fixed schema only)
- Full PDF layout reconstruction
- Related Work draft generation or pre-clustering gaps inside LGC
- Graphiti as a runtime dependency
- Auth, billing, multi-tenant SaaS

---

## Migrating to v0.6 (UUID `paper_id`)

Re-indexing required (no migration script):

```bash
rm -rf .litgraph/cache/parsed .litgraph/cache/extracted .litgraph/cache/files.json \
  .litgraph/db .litgraph/paper_id_map.json
litgraph scan && litgraph parse --all && litgraph extract -y && litgraph build
litgraph test-mcp
```

`parse --all` is required so papers are re-parsed even when the hash cache reports "unchanged" after cache clear.

## Migrating to v0.10 (`workspace_id`)

From v0.10 onward, `workspace_id` is introduced on graph, registry, and cache. No migration script is provided (same approach as v0.6). **Re-index** existing projects:

```bash
rm -rf .litgraph/cache .litgraph/db .litgraph/paper_registry.json .litgraph/graph.json
litgraph scan ./papers && litgraph parse --all && litgraph extract -y && litgraph build
litgraph test-mcp
```

In the `default` workspace, legacy `.litgraph/cache/` paths are auto-fallback, but new ingest writes to `cache/default/`.
