# LiteratureGraphContext

Structure paper PDFs into a knowledge graph (Paper, Method, Dataset, Claim, Limitation, Evidence) and expose it via MCP for literature review workflows.

Licensed under the [MIT License](LICENSE).

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

## Supported file types

| Type | Role |
|---|---|
| `.pdf` | Full parse → LLM extract → graph |
| `.md` | Paper notes (`# Abstract`, `## Introduction`, etc.) → extract → graph |
| `.bib` | Metadata only (title, authors, venue, doi) merged into graph at `build` |

## Configuration

Project config lives in `.litgraph/config.yaml`. API keys go in `.env` or `~/.litgraph/.env`.

## MCP setup (Cursor)

```bash
litgraph mcp setup
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and known gaps.
