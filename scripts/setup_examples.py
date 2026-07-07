"""Prepare examples/papers demo graph (no live LLM required)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from litgraph.cli.config_manager import init_project, resolve_context
from litgraph.cli.helpers import build_paper_graph, parse_papers, scan_papers
from tests.fixtures.extracted_fixtures import write_fixtures


def _ensure_pdfs() -> Path:
    papers_dir = ROOT / "examples" / "papers"
    if not any(papers_dir.glob("*.pdf")):
        from scripts.generate_demo_pdfs import main as generate_pdfs

        generate_pdfs()
    return papers_dir


def _ensure_bib(papers_dir: Path) -> None:
    sample = ROOT / "tests" / "fixtures" / "sample.bib"
    target = papers_dir / "mobility_gnn_2024.bib"
    if sample.exists() and not target.exists():
        shutil.copy(sample, target)


def main() -> None:
    papers_dir = _ensure_pdfs()
    _ensure_bib(papers_dir)

    init_project(ROOT, papers_dir="examples/papers")
    ctx = resolve_context(ROOT)

    scan = scan_papers(ctx, persist_dir=False)
    parsed = parse_papers(ctx, only_changed=False)
    write_fixtures(ctx.extracted_cache_dir)
    built = build_paper_graph(ctx)

    print("Examples demo ready.")
    print(f"  papers_dir : {ctx.papers_dir}")
    print(f"  scanned    : {scan['total']} file(s)")
    print(f"  parsed     : {parsed['parsed']} paper(s), {parsed.get('bib_files', 0)} bib file(s)")
    print(f"  indexed    : {built.get('papers_indexed', 0)} paper(s)")
    print(f"  nodes/edges: {built.get('nodes', 0)} / {built.get('edges', 0)}")
    print()
    print("Next:")
    print("  litgraph viz                    # CGC Playground UI (build first if needed)")
    print("  powershell scripts/build_viz.ps1")
    print("  litgraph serve-mcp")
    print("  litgraph query papers --method GNN")


if __name__ == "__main__":
    main()
