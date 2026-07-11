# LiteratureGraphContext Tutorial

End-to-end guide from install to MCP-backed literature review.  
For design philosophy and a short quick start, see the [README](../README.md). For planned work, see [ROADMAP.md](../ROADMAP.md).

**Audience:** researchers and developers who want `pip install literature-graph` and a working Cursor (or other MCP client) setup.

---

## Table of contents

1. [Install](#1-install)
2. [Project setup](#2-project-setup)
3. [Index papers](#3-index-papers)
4. [Connect MCP](#4-connect-mcp)
5. [Try MCP tools](#5-try-mcp-tools)
6. [Visualize the graph](#6-visualize-the-graph)
7. [Zotero (optional)](#7-zotero-optional)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Install

Requires **Python 3.10+**.

```bash
pip install literature-graph
```

From a clone of this repository (development):

```bash
pip install -e ".[dev]"
```

Check the CLI:

```bash
litgraph version
```

**Expected:** a version string (for example `1.0.1`).

---

## 2. Project setup

Each repository is its own project under `<repo>/.litgraph/`. API keys live in `~/.litgraph/.env` (global), not inside the project.

### Interactive (recommended)

```bash
mkdir my-lit-review && cd my-lit-review
mkdir papers
# Put at least one PDF under ./papers, then:
litgraph setup --papers-dir ./papers
```

The wizard walks through:

- Project init (`.litgraph/config.yaml`)
- LLM provider / API keys → `~/.litgraph/.env`
- Optional Zotero credentials
- MCP client config (`mcp.json` or Cursor / Claude Desktop)
- Optional first index

### Non-interactive

```bash
litgraph init --papers-dir ./papers
litgraph setup --papers-dir ./papers --yes
```

`--yes` writes a stdio MCP entry to `./mcp.json` without prompts. For Cursor transport choices (stdio vs daemon HTTP), use the interactive wizard.

### Where things live

| Path | Purpose |
|---|---|
| `<repo>/.litgraph/config.yaml` | Project settings (`papers_dir`, LLM, database) |
| `<repo>/.litgraph/cache/`, `db/` | Scan/parse/extract cache and Kuzu graph |
| `~/.litgraph/.env` | API keys (`OPENAI_API_KEY`, `ZOTERO_*`, …) |
| `~/.litgraph/logs/` | Global logs |

**Important:** `~/.litgraph` is **not** a project. Always run commands from a directory that has `.litgraph/config.yaml`, or set `LITGRAPH_PROJECT_ROOT`.

Verify resolution:

```bash
litgraph doctor
```

**Expected:** an “Active project” block with `root`, `papers_dir`, and PDF count.

---

## 3. Index papers

Place files under your papers folder:

```text
papers/
  example_paper.pdf
  example_paper.bib      # optional metadata
  example_paper_notes.md # optional notes
```

| Extension | Role |
|---|---|
| `.pdf` | Parse → LLM extract → graph |
| `.md` | Notes with section headings → extract → graph |
| `.bib` | Metadata merged at build |

### Full pipeline

```bash
litgraph index -y
```

`-y` skips the external-API confirmation prompt. Pipeline:

```text
scan → parse → extract (LLM) → build (graph)
```

**Expected:** a summary of scanned / parsed / extracted papers and a successful build.

### Without LLM extract (no API key yet)

```bash
litgraph index -y --no-extract
```

This still parses PDFs/Markdown and builds Paper nodes from parse cache (title / structure) plus any BibTeX metadata. Claims, limitations, and rich evidence need a later extract:

```bash
litgraph extract -y
litgraph build
```

CI runs this no-API path in `tests/test_quickstart_smoke.py` so the Tutorial commands stay honest.

### Re-index after adding PDFs

```bash
litgraph index -y
```

Only changed files are re-parsed by default. Force a full re-extract with `--force` / `--all` when needed (see `litgraph index --help`).

---

## 4. Connect MCP

LiteratureGraphContext exposes the graph to AI assistants over **MCP**. Kuzu (the default embedded DB) allows **one writer** at a time. Treat that as a hard rule when choosing a transport.

### Kuzu single-writer policy

| Process | Role | Notes |
|---|---|---|
| `litgraph index` / `build` / `watch` / `daemon` | May **write** | Do not run two writers on the same project |
| `litgraph serve-mcp` (stdio) | **Read-only** | Cursor may spawn this; avoid overlapping with `watch` / `daemon` writes |
| `litgraph viz` | **Read-only** | Safe alongside stdio MCP |
| `litgraph daemon` | **Write** hub + HTTP MCP | Prefer this on Windows for long-running sync |

**Do not** run `litgraph serve-mcp` (stdio) and `litgraph daemon` against the same project at the same time.

### Option A — stdio (simple)

```bash
litgraph serve-mcp
```

Or let Cursor start it via `mcp.json` written by `litgraph setup`. Typical entry:

```json
{
  "mcpServers": {
    "literature-graph": {
      "command": "litgraph",
      "args": ["serve-mcp"]
    }
  }
}
```

Restart the MCP client after changing config.

### Option B — daemon HTTP (recommended on Windows)

One long-lived process: settings UI, optional Zotero polling, folder watch, and MCP at `/mcp`.

```bash
litgraph daemon
```

- Home: `http://127.0.0.1:8766/` → `/home` (entry to Settings / Graph / MCP)
- Settings: `http://127.0.0.1:8766/settings` (sync, extract, API keys)
- Graph: `http://127.0.0.1:8766/viz`
- MCP endpoint: `http://127.0.0.1:8766/mcp`

In `litgraph setup`, choose **daemon-http** so the client uses a URL instead of spawning stdio:

```json
{
  "mcpServers": {
    "literature-graph": {
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

Start the daemon **before** the MCP client connects. Keep `ZOTERO_API_KEY` / `ZOTERO_USER_ID` in `~/.litgraph/.env` if you use auto-sync.

Standalone HTTP without the full daemon (no settings UI / Zotero scheduler):

```bash
litgraph serve-mcp --http --port 8000
```

---

## 5. Try MCP tools

Smoke-test against the project graph (no Cursor required):

```bash
litgraph test-mcp
```

**Expected:** all tools pass. Failures usually mean the graph was never built (`litgraph index -y`) or the project root is wrong (`litgraph doctor`).

### Core tools

| Tool | Use when |
|---|---|
| `list_papers` | See what is indexed |
| `search_papers` | Ambiguous topic → get `paper_id` first |
| `summarize_paper` | Tasks, methods, claims, limitations + evidence |
| `compare_papers` | Side-by-side on task / method / dataset / … |
| `find_limitations` | Topic or paper-scoped limitations with evidence |
| `explore_paper_graph` | Citation / contrast / extend neighbors (`hops`) |
| `watch_papers_directory` | Start/stop/status folder auto-ingest |

### Typical agent flow

```text
User: "What are the gaps in mobility prediction?"

  search_papers("mobility prediction")
  find_limitations(topic="mobility prediction")
  explore_paper_graph(paper_id, hops=1)
  compare_papers([id_a, id_b])

  → Answer citing paper_id, page, section, evidence_text
```

LGC returns structured evidence. The connected agent interprets gaps and writes prose.

---

## 6. Visualize the graph

```bash
litgraph viz
```

Opens `http://127.0.0.1:8765` (override with `--port`). Use `--no-browser` if you only need the server.

**Expected:** a paper-centric graph UI. If the DB is locked by a writer, stop `watch` / `daemon` or wait for ingest to finish, then retry.

---

## 7. Zotero (optional)

Credentials (preferred in `~/.litgraph/.env`):

```bash
ZOTERO_API_KEY=...
ZOTERO_USER_ID=...   # numeric library id, not your username
```

`litgraph setup` can resolve the user id from the API key.

### Bib sync only

```bash
litgraph import zotero-sync
```

### Bib + PDF attachments → ingest → optional rebuild

```bash
litgraph import zotero-sync --with-pdfs --rebuild
```

- Incremental by default; use `--full` for a full resync.
- Items without a PDF attachment may still ingest if the Zotero URL maps to arXiv or a direct PDF link.

### Background auto-sync

```bash
litgraph daemon
```

Configure interval and `extract_mode` (`auto` / `manual`) on the settings page (`/`). Manual mode queues extract until you trigger it from the UI/API.

---

## 8. Troubleshooting

### `No active project` / unexpected paths

```bash
litgraph doctor
litgraph init --papers-dir ./papers
```

Or set:

```bash
export LITGRAPH_PROJECT_ROOT=/path/to/your/repo   # Windows: set LITGRAPH_PROJECT_ROOT=...
```

### Kuzu lock / “Could not set lock”

Another process holds the DB (`daemon`, `watch`, or a stuck `serve-mcp`).

1. Stop extra writers (`Ctrl+C` on daemon/watch).
2. Prefer **one** of: stdio MCP **or** daemon HTTP — not both.
3. Retry `litgraph index` / `viz` / `test-mcp`.

### MCP tools empty or failing

```bash
litgraph doctor          # graph: ready?
litgraph index -y        # or index -y --no-extract then extract later
litgraph test-mcp -v
```

### Extract skipped / no claims

Ensure `OPENAI_API_KEY` (or your configured provider key) is in `~/.litgraph/.env`, then:

```bash
litgraph extract -y
litgraph build
```

### Zotero sync skips everything

- Confirm `ZOTERO_USER_ID` is numeric.
- Attachments may be missing; check item URLs for arXiv/PDF fallbacks.
- Use `--full` once, then rely on incremental sync.

### Windows: Cursor + stdio lock conflicts

Use `litgraph daemon` + **daemon-http** in setup (section 4, option B). Optionally register `litgraph daemon` in Task Scheduler (At log on), with *Start in* set to the project root.

---

## Next steps

- [README](../README.md) — design philosophy and config reference  
- [ROADMAP.md](../ROADMAP.md) — v0.13 structuring, v1.0 PyPI, daemon polish  
- Programmatic use: `from litgraph import LitgraphContext` (see package API after install)

When in doubt: `litgraph doctor` → `litgraph index -y` → `litgraph test-mcp`.
