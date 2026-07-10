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
| Last | v1.0 PyPI + docs | First stable `pip install literature-graph` after v0.13 |
| Next | v1.1 Background daemon | Zotero auto-sync, HTTP MCP hub, settings UI (mostly shipped) |
| Later | v1.x → v2.0 | v1.x: packaging prep (PyInstaller, supervisor); **v2.0: OS installers** (Python not required) |

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
| I02 | New inputs: arXiv / URL / Zotero connectors ✅ — CSV not implemented | v0.9, v0.11 ✅ / CSV → v1.2+ candidate |
| I03 | Containment: section / subsection + `CONTAINS` edges (+ section embeddings) | v0.13 |
| I04 | PDF structure: robust section detection + diagnostics | detection v0.11 ✅ / diagnostics v0.13 |
| I05 | Citations: `CITES` resolution accuracy (external IDs) — refs+bib merge shipped | v0.13 |
| I06 | ID resolution & errors: actionable hints in MCP / CLI | v0.8 ✅ |
| I07 | Auto-generate `paper_id_map` from `paper_registry` | v1.2+ candidate |
| I08 | Graph UI: paper-centric sidebar + preview cards | v0.8 ✅ |
| I09 | Workspace-scoped graph (`workspace_id` on nodes & queries) | v0.10 ✅ |
| I10 | Programmatic API (`LitgraphContext`, injectable store) | v0.9 ✅ |
| I11 | HTTP MCP transport (remote callers) | v0.12 ✅ |
| I12 | Folder watch / auto-ingest (`watch_papers_directory`) | v0.12 ✅ |
| I13 | MCP setup wizard (interactive onboarding) | v0.8 ✅ |
| I14 | Zotero write-back: push extracted limitations / comparisons to Zotero tags & notes | v1.2+ candidate |
| I15 | In-graph embeddings: vectors as node properties + vector index (Kuzu HNSW / Neo4j), retire `embeddings.json` | v0.13 |
| I16 | End-user distribution: PyInstaller frozen exe, PySide6 tray supervisor, Inno Setup / DMG / deb, GitHub Releases | v1.x spike / **v2.0 ship** |

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
| MCP stability | **Done (v1.1 daemon)** / docs (v1.0) | `litgraph daemon` single-writer hub; document HTTP MCP + avoid stdio lock conflicts |
| Zotero | **Done (v0.11)** | Full PDF pipeline shipped; incremental sync in daemon (v1.1) |
| Distribution | **Active (v2.0)** | v1.0 = PyPI (`pip install`); v2.0 = PyInstaller bundle + Inno Setup / DMG + system-tray supervisor |
| Embedding store (JSON sidecar, full load + O(n) cosine) | **Active (v0.13)** | In-graph vectors + vector index, Kuzu & Neo4j (I15) |
| md parser | Deferred | Single-paper notes only |
| Neo4j migration | Deferred | No migration tool from Kuzu |
| Claim-level embeddings | Deferred | Paper-level embeddings only |

**Intentionally delegated to agents:** Gap clustering, Related Work drafts via `generate_related_work_outline`.

---

## Version roadmap

**Versioning policy**

Distribution has **two channels** — do not conflate them:

| Channel | Version | Audience | Install |
|---|---|---|---|
| **PyPI** | **1.0** | Developers / researchers | `pip install literature-graph` |
| **Installer** | **2.0** | End users (no Python) | `.exe` / `.dmg` / `.deb` from GitHub Releases |

| Series | Meaning |
|---|---|
| **0.x** | Pre-PyPI development releases (current: 0.12.0 → 0.13) |
| **1.0** | First stable **PyPI** release + documentation |
| **1.x** | Feature additions after 1.0 (semver minor); includes background daemon (v1.1) |
| **2.0** | **End-user distribution** — PyInstaller-frozen binaries, OS installers (Inno Setup / DMG / deb), PySide6 system-tray supervisor, logon autostart, GitHub Releases + WinGet (breaking API changes may ride along) |

```text
0.7 ✅ → … → 0.12 ✅ → 0.13 → 1.0 (PyPI) → 1.1 (daemon) → 1.x → 2.0 (installer)
  │                         │              │                │
  └─ pre-PyPI development   └─ now         └─ pip install   └─ frozen exe + OS installer
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

#### v1.1 — Background daemon

Single long-lived process for Zotero polling, optional folder watch, HTTP MCP, and a settings web UI. Separated as `src/litgraph/daemon/` (independent from core graph/extract). Use with HTTP MCP (`http://127.0.0.1:8766/mcp`) instead of stdio `serve-mcp` to avoid Kuzu lock conflicts (especially on Windows).

**Shipped**

- [x] `litgraph daemon` — FastAPI server on `127.0.0.1:8766` with settings page (`/`) and MCP mount (`/mcp`)
- [x] Zotero incremental sync — `ingested_versions` in sync state; `changed_only` skips unchanged items
- [x] Ingest queue — serializes ingest / build; `finder.reload()` after build
- [x] `extract_mode: auto | manual` — manual mode queues pending extract; `POST /api/daemon/extract`
- [x] Daemon settings API — `GET/PUT /api/daemon/settings`, `GET /api/daemon/status`, `POST /api/daemon/sync`
- [x] `daemon-http` MCP transport in setup wizard
- [x] Folder watch integration via `WatchOptions.write_guard` (optional `watch_folder` in config)
- [x] Tests — `tests/test_daemon.py`

**Polish (remaining)**

- [ ] MCP fallback during ingest/build — `503 syncing` or `cache/graph.json` snapshot (Kuzu single-writer)
- [ ] `litgraph setup` — first-run daemon start guide and HTTP MCP as default on Windows
- [ ] Zotero backoff / failure visibility in status API

#### v1.x — v2 prerequisites

Packaging groundwork before v2.0. Does not block IDEA items (I07, I14, CSV, etc.) in parallel.

| Item | Description |
|---|---|
| **I16 packaging spike** | PyInstaller proof-of-concept on Windows — bundle `litgraph daemon`, Kuzu + PyMuPDF native libs |
| **Frozen paths** | `sys._MEIPASS` support for static HTML, config resolution, default `.litgraph` paths |
| **Default project bootstrap** | First-run papers folder + `litgraph init` equivalent from settings UI |
| **Supervisor design** | `litgraph-tray` — PySide6 `QSystemTrayIcon`, subprocess control of frozen `litgraph-daemon.exe`, `webbrowser.open` for settings |
| **Release infra** | `scripts/package/` — version script, `dist/` layout, CI matrix (Windows / macOS / Linux) |

#### v1.2+ — Feature minors (TBD)

Assign remaining IDEA Matrix items — e.g. I07 (`paper_id_map` auto-gen), CSV connector (I02 remainder), I14 (Zotero write-back), claim-level embeddings.

### 2.0 — End-user distribution

**Goal:** Ship a self-contained install that does not require a pre-installed Python interpreter. User flow: download installer → install → system-tray app starts `litgraph daemon` → configure via browser at `http://127.0.0.1:8766/`.

#### Runtime architecture

```text
litgraph-tray (PySide6, frozen exe)
  ├─ spawns / supervises → litgraph-daemon.exe (PyInstaller one-folder or one-file)
  │     ├─ FastAPI + uvicorn  @ 127.0.0.1:8766
  │     ├─ GET  /              settings UI (bundled settings.html)
  │     ├─ *    /mcp           Streamable HTTP MCP (mcp.server.streamable_http)
  │     ├─ ZoteroScheduler     httpx → Zotero Web API, incremental ingested_versions
  │     ├─ IngestQueue         threading queue → parse / extract / build (Kuzu write)
  │     └─ optional watchdog   papers_dir folder watch
  ├─ system tray menu          start / stop / restart daemon, open settings URL
  └─ logon autostart           Windows: Startup folder or Task Scheduler entry created by installer
                               macOS: LaunchAgent plist
                               Linux: XDG autostart .desktop
```

#### Technology stack

| Layer | Technology | Notes |
|---|---|---|
| Daemon server | FastAPI, uvicorn, `litgraph.daemon.server` | Already implemented; bind `127.0.0.1` only |
| MCP transport | `mcp` SDK, Streamable HTTP | Mounted at `/mcp`; Cursor connects via `url` in mcp.json |
| Graph DB | Kuzu (embedded, `pip` dep) | Native `.dll` / `.so` must ship inside PyInstaller bundle |
| PDF parse | PyMuPDF (`fitz`) | Native lib; test in PyInstaller spike |
| Settings UI | Static HTML + `fetch` | `src/litgraph/daemon/static/settings.html`; no build step |
| Binary freeze | **PyInstaller** (`*.spec`) | Separate specs for `litgraph-daemon` and `litgraph-tray`; `COLLECT` one-folder layout preferred for Kuzu |
| Tray supervisor | **PySide6** (`QSystemTrayIcon`) | Small wrapper exe; alternative: Tauri 2 shell calling bundled daemon (evaluate in v1.x spike) |
| Windows installer | **Inno Setup** (`.iss`) | Bundles `dist/literaturegraph/` tree; optional logon task; uninstaller keeps `~/.litgraph` |
| macOS package | **create-dmg** or `hdiutil` | Signed `.app` inside `.dmg`; notarization via `notarytool` |
| Linux package | **dpkg-deb** + **AppImage** | `.deb` for apt; AppImage for distro-agnostic |
| Release CI | GitHub Actions | Matrix build per OS; artifacts uploaded on `v*` tag |
| Package index | **WinGet** (`winget-releaser` action) | Manifest points at GitHub Release `.exe` |
| Secrets / keys | `~/.litgraph/.env` | `python-dotenv`; first-run wizard writes `OPENAI_API_KEY`, `ZOTERO_API_KEY` |
| Code signing | Authenticode (Windows), codesign + notarize (macOS) | Required for SmartScreen / Gatekeeper; target v2.0 or v2.1 |

#### v1.x packaging spike (gate before v2.0)

- [ ] `literaturegraph-daemon.spec` — entry `litgraph.cli.main:app` subcommand `daemon`; `--collect-all kuzu`; hiddenimports for `uvicorn`, `fastapi`, `mcp`
- [ ] Verify Kuzu read/write and PyMuPDF parse on frozen Windows exe
- [ ] `sys._MEIPASS` path helpers for `daemon/static/`, `viz/static/`
- [ ] Measure one-folder bundle size; document minimum disk / RAM

**Phase A — PyInstaller bundle**

- [ ] `literaturegraph-daemon` — daemon + CLI (`litgraph` typer app) as frozen executables
- [ ] Data files in spec — `datas=[('src/litgraph/daemon/static', 'litgraph/daemon/static'), ...]`
- [ ] Runtime hook — set `LITGRAPH_PROJECT_ROOT` or prompt on first launch if no `.litgraph/config.yaml`
- [ ] Reuse `litgraph setup` / `mcp setup_wizard` logic for `~/.litgraph/.env` and Cursor mcp.json

**Phase B — Tray supervisor (`litgraph-tray`)**

- [ ] PySide6 `QSystemTrayIcon` + menu: Start, Stop, Restart, Open settings (`webbrowser.open('http://127.0.0.1:8766/')`)
- [ ] `subprocess.Popen` / `terminate` for `litgraph-daemon.exe`; restart on unexpected exit (exponential backoff)
- [ ] Detect port 8766 in use (`errno.EADDRINUSE`); surface PID / "another instance" in tray tooltip
- [ ] Log file tail — `~/.litgraph/logs/daemon.log` (rotate via `logging.handlers.RotatingFileHandler`)

**Phase C — OS installers & release pipeline**

- [ ] Windows — `scripts/package/literaturegraph-setup.iss` (Inno Setup); output `literaturegraph-setup-{version}.exe`
- [ ] macOS — `scripts/package/build_dmg.sh`; codesign + notarize in CI (`APPLE_*` secrets)
- [ ] Linux — `scripts/package/build_deb.sh`, `scripts/package/build_appimage.sh`
- [ ] `.github/workflows/release.yml` — tag `v2.0.0` triggers matrix build → GitHub Releases draft
- [ ] `.github/workflows/winget.yml` — on `release: released`, publish WinGet manifest
- [ ] Version source — `pyproject.toml` `[project].version`; propagated to Inno `#define MyAppVersion`

**Phase D — First-run & uninstall**

- [ ] Settings UI or tray wizard — papers folder path, `litgraph init` equivalent, Zotero API key, default `extract_mode: manual`
- [ ] Write Cursor MCP config — `{"url": "http://127.0.0.1:8766/mcp"}` via existing `build_daemon_http_mcp_config()`
- [ ] Inno uninstall — checkbox "Keep configuration and graph data"; remove only `{app}` binaries
- [ ] Document coexistence rule — do not run stdio `litgraph serve-mcp` alongside daemon (Kuzu file lock)

**v2.0 risks**

| Risk | Mitigation |
|---|---|
| Kuzu native libs fail to bundle | v1.x Windows PyInstaller PoC is a hard gate; pin kuzu version in spec |
| Large bundle size (Python + OpenAI client + kuzu) | ship without dev deps; default `extract_mode: manual` skips OpenAI at sync time |
| Active project root ambiguous | tray + settings UI: "active project" path stored in `~/.litgraph/config.yaml` or daemon section |
| stdio MCP lock conflicts | first-run writes HTTP MCP only; installer README warns against stdio |
| Windows SmartScreen | Authenticode signing on `literaturegraph-setup.exe` and bundled exes |

---

## Out of scope

- Free-form knowledge graphs (literature-review fixed schema only)
- Full PDF layout reconstruction
- Related Work draft generation or pre-clustering gaps inside LGC
- Graphiti as a runtime dependency
- Auth, billing, multi-tenant SaaS
- Neo4j embedded in-process (Bolt server only; optional manual setup)
- Team-shared graph server / multi-machine sync (future; Neo4j Server + auth)
- Mobile / iOS
- Zip-only distribution without system-tray supervisor or OS installer as the v2.0 completion target (full install = Inno Setup / DMG / deb + `litgraph-tray` required)

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
