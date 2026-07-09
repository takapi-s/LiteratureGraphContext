# LiteratureGraphContext

Structure paper PDFs into a knowledge graph (Paper, Method, Dataset, Claim, Limitation, Evidence) and expose it via MCP for literature review workflows.

Licensed under the [MIT License](LICENSE).

## Design philosophy

LiteratureGraphContext is a **structured evidence layer** for literature review—not an AI that writes your related work or discovers research gaps for you.

**What LGC owns**

- **Graph connections** — Papers link through shared tasks, methods, datasets, citations (`CITES`), contrasts (`CONTRASTS_WITH`), and extensions (`EXTENDS`). Multiple studies stay connected across topics instead of living in isolated PDFs.
- **Evidence-backed facts** — Claims, limitations, and contributions are stored with provenance: `paper_id`, page, section, and `evidence_text`.
- **MCP as the data plane** — Tools return structured lists, comparisons, and matrices grounded in the graph.

**What the connected agent owns**

- Interpreting limitations as research gaps
- Drafting related work prose
- Open-ended synthesis and recommendations

A typical agent flow:

```text
User: "What are the gaps in prediction research?"

  Agent → search_papers("prediction research")
        → find_limitations("prediction")   # or paper_id= from search
        → explore_paper_graph(paper_id, hops=1|2)
        → compare_papers([...])

  Agent synthesizes the answer, citing paper_id / page / evidence_text from MCP
```

LGC does not pre-compute narrative conclusions. It makes the graph and evidence reliable enough for agents to reason over. See [ROADMAP.md](ROADMAP.md) for how known limitations are prioritized under this model.

## Quick start

```bash
pip install -e ".[dev]"
litgraph init --papers-dir ./my-papers
litgraph scan ./my-papers
litgraph parse
litgraph extract
litgraph build
litgraph serve-mcp
```

## Where to put papers

Place PDF, BibTeX, and Markdown note files under your papers folder:

```text
my-papers/
  mobility_gnn_2024.pdf
  mobility_gnn_2024.bib
  mobility_gnn_2024_notes.md
```

### Configure the folder path

| Method | Command |
|---|---|
| At init | `litgraph init --papers-dir ./my-papers` |
| On scan (auto-save) | `litgraph scan ./my-papers` |
| Explicit set | `litgraph config set papers_dir ./my-papers` |
| Manual edit | `.litgraph/config.yaml` → `papers_dir` |

Relative paths are resolved from the project root. Absolute paths are also supported.

After `scan`, `parse`, `extract`, and `build` use the configured `papers_dir` when no path argument is given.

Verify MCP tools: `litgraph test-mcp`

## Supported file types

| Type | Role |
|---|---|
| `.pdf` | Full parse → LLM extract → graph |
| `.md` | Paper notes (`# Abstract`, `## Introduction`, etc.) → extract → graph |
| `.bib` | Metadata only (title, authors, venue, doi) merged into graph at `build` |

## Configuration

Each repository has its own project at `<repo>/.litgraph/` (config, cache, graph DB). Run `litgraph init` once per repository before other commands.

| Location | Purpose |
|---|---|
| `<repo>/.litgraph/config.yaml` | Project settings (`papers_dir`, LLM, database) |
| `<repo>/.litgraph/cache/`, `db/` | Per-project scan cache and graph |
| `~/.litgraph/.env` | Global API keys (shared across projects) |
| `~/.litgraph/logs/` | Global log files |

**Important:** `~/.litgraph` is for API keys and logs only—it is **not** a project. Commands like `scan`, `parse`, and `build` require an initialized project under your repository. If you see unexpected paths or split graph data, run `litgraph doctor`.

Project resolution order:

1. `LITGRAPH_PROJECT_ROOT` (MCP / IDE)
2. Walk up from cwd to find `<repo>/.litgraph/config.yaml` (skips `~/.litgraph`)

## MCP setup (Cursor)

```bash
litgraph mcp setup
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and known gaps.
