"""LiteratureGraph CLI."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import json
import typer
from rich.console import Console

from litgraph import __version__
from litgraph.cli import config_manager, helpers
from litgraph.mcp.setup_wizard import configure_mcp_client

app = typer.Typer(name="litgraph", help="LiteratureGraphContext: papers to knowledge graph.")
config_app = typer.Typer(help="Project configuration commands.")
mcp_app = typer.Typer(help="MCP configuration commands.")
query_app = typer.Typer(help="Query the literature graph.")
app.add_typer(config_app, name="config")
app.add_typer(mcp_app, name="mcp")
app.add_typer(query_app, name="query")
console = Console(stderr=True)


@app.callback()
def main() -> None:
    config_manager.load_env()


@app.command("init")
def init_cmd(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project root"),
    papers_dir: Optional[Path] = typer.Option(None, "--papers-dir", help="Default papers directory"),
) -> None:
    """Initialize .litgraph project configuration."""
    root = path.resolve()
    papers = str(papers_dir) if papers_dir else None
    litgraph_dir = config_manager.init_project(root, papers_dir=papers)
    console.print(f"[green]Initialized[/green] {litgraph_dir}")


@app.command("scan")
def scan_cmd(
    papers_path: Optional[Path] = typer.Argument(None, help="Papers directory (optional)"),
) -> None:
    """Scan papers folder and update file hash cache."""
    ctx = config_manager.resolve_context()
    result = helpers.scan_papers(ctx, papers_path, persist_dir=papers_path is not None)
    console.print(
        f"Scanned {result['total']} files ({result['changed']} changed) in {result['papers_dir']}."
    )


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g. papers_dir)"),
    value: str = typer.Argument(..., help="Config value"),
) -> None:
    """Set a project config value."""
    ctx = config_manager.resolve_context()
    if key == "papers_dir":
        stored = config_manager.save_papers_dir(ctx, Path(value))
        console.print(f"[green]papers_dir[/green] = {stored}")
        return
    config_manager.save_config_value(ctx.litgraph_dir, key, value, ctx.project_root)
    console.print(f"[green]{key}[/green] updated.")


@app.command("parse")
def parse_cmd(
    all_files: bool = typer.Option(False, "--all", help="Parse all files, not only changed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show per-paper section and reference details"),
) -> None:
    """Parse PDFs, Markdown notes, and BibTeX metadata into cache."""
    ctx = config_manager.resolve_context()
    result = helpers.parse_papers(ctx, only_changed=not all_files, verbose=verbose)
    console.print(
        f"Parsed {result['parsed']} paper(s), {result.get('bib_files', 0)} bib file(s)."
    )


@app.command("extract")
def extract_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip external API confirmation"),
    force: bool = typer.Option(False, "--force", help="Re-extract papers that already have cache"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider override"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model override"),
    background: bool = typer.Option(False, "--background", help="Run extraction in background job"),
) -> None:
    """Extract structured data from parsed papers using LLM."""
    ctx = config_manager.resolve_context()
    if background:
        job_id = helpers.extract_papers_async(
            ctx, skip_confirm=yes, provider=provider, model=model, force=force,
        )
        console.print(f"Started extraction job: {job_id}")
        return
    result = helpers.extract_papers(
        ctx,
        skip_confirm=yes,
        provider=provider,
        model=model,
        force=force,
        show_progress=True,
    )
    if result.get("cancelled"):
        console.print("[yellow]Extraction cancelled.[/yellow]")
        return
    extracted = result.get("extracted", 0)
    skipped = result.get("skipped", 0)
    if skipped:
        console.print(
            f"Extracted {extracted} paper(s), skipped {skipped} already up to date "
            f"via {result.get('provider')}."
        )
    else:
        console.print(f"Extracted {extracted} paper(s) via {result.get('provider')}.")


@app.command("build")
def build_cmd(
    enrich_s2: bool = typer.Option(False, "--enrich-s2", help="Enrich metadata via Semantic Scholar"),
) -> None:
    """Build graph from extracted JSON and bib metadata."""
    ctx = config_manager.resolve_context()
    result = helpers.build_paper_graph(ctx, enrich_s2=enrich_s2)
    console.print(
        f"Indexed {result.get('papers_indexed', 0)} paper(s), "
        f"nodes={result.get('nodes', 0)}, edges={result.get('edges', 0)}, "
        f"cites_from_references={result.get('cites_from_references', 0)}."
    )


@app.command("watch")
def watch_cmd(
    auto_extract: bool = typer.Option(
        False,
        "--auto-extract",
        help="Run LLM extraction on new/changed papers (off by default)",
    ),
    no_build: bool = typer.Option(False, "--no-build", help="Skip graph rebuild after changes"),
    sync_on_start: bool = typer.Option(False, "--sync-on-start", help="Process pending changes before watching"),
    polling: bool = typer.Option(False, "--polling", help="Use polling observer (or set LITGRAPH_WATCH_POLLING=1)"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip external API confirmation (automatic with --auto-extract)",
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider for --auto-extract"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model for --auto-extract"),
    enrich_s2: bool = typer.Option(False, "--enrich-s2", help="Enrich metadata via Semantic Scholar on rebuild"),
) -> None:
    """Watch papers directory; queues changes while a batch is processing."""
    ctx = config_manager.resolve_context()

    def _on_result(result: dict) -> None:
        parsed = result.get("parsed", 0)
        removed = result.get("removed_paper_ids", [])
        pending = result.get("pending_extract", [])
        extracted = result.get("extracted", 0)
        extract_skipped = result.get("extract_skipped", 0)
        if parsed:
            console.print(f"[green]Parsed {parsed} paper(s).[/green]")
        if extracted:
            if extract_skipped:
                console.print(
                    f"[green]Extracted {extracted} paper(s), "
                    f"skipped {extract_skipped} already up to date.[/green]"
                )
            else:
                console.print(f"[green]Extracted {extracted} paper(s).[/green]")
        if removed:
            console.print(f"[yellow]Removed {len(removed)} paper(s) from graph.[/yellow]")
        if result.get("bib_updated"):
            console.print("[green]Bib metadata updated.[/green]")
        if result.get("papers_indexed") is not None and result.get("papers_indexed", 0) > 0:
            console.print(f"[green]Graph rebuilt: {result['papers_indexed']} paper(s) indexed.[/green]")
        if pending and not auto_extract:
            console.print(
                f"[yellow]{len(pending)} paper(s) parsed but not in graph "
                f"(run litgraph extract): {', '.join(pending)}[/yellow]"
            )
        if result.get("cancelled"):
            console.print("[yellow]Auto-extract cancelled.[/yellow]")

    auto_yes = yes or auto_extract
    console.print(
        f"Watching {ctx.papers_dir} "
        f"(auto_extract={'on' if auto_extract else 'off'}, build={'on' if not no_build else 'off'}"
        f"{', auto-yes' if auto_yes and auto_extract else ''}). "
        "Press Ctrl+C to stop."
    )
    helpers.run_papers_watcher(
        ctx,
        auto_extract=auto_extract,
        auto_build=not no_build,
        sync_on_start=sync_on_start,
        skip_confirm=auto_yes,
        provider=provider,
        model=model,
        enrich_s2=enrich_s2,
        polling=polling,
        on_result=_on_result,
    )


@app.command("viz")
def viz_cmd(
    port: int = typer.Option(8765, "--port"),
    no_browser: bool = typer.Option(False, "--no-browser"),
) -> None:
    """Launch local Web UI for graph visualization."""
    ctx = config_manager.resolve_context()
    console.print(f"[green]Starting graph viewer on http://127.0.0.1:{port}[/green]")
    helpers.launch_visualizer(ctx, port=port, open_browser=not no_browser)


jobs_app = typer.Typer(help="Background job commands.")
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def jobs_list() -> None:
    """List background jobs."""
    for job in helpers.list_jobs():
        console.print_json(json.dumps(job, ensure_ascii=False))


@jobs_app.command("status")
def jobs_status(job_id: str = typer.Argument(..., help="Job ID")) -> None:
    """Check background job status."""
    console.print_json(json.dumps(helpers.check_job_status(job_id), ensure_ascii=False))


import_app = typer.Typer(help="Import external libraries.")
app.add_typer(import_app, name="import")


@import_app.command("zotero")
def import_zotero(
    export_path: Path = typer.Argument(..., help="Zotero JSON export file"),
) -> None:
    """Import a Zotero JSON export into bib cache."""
    from litgraph.integrations.zotero import import_zotero_export

    ctx = config_manager.resolve_context()
    entries = import_zotero_export(export_path.resolve(), ctx.bib_cache_dir)
    console.print(f"Imported {len(entries)} entries from Zotero export.")


@import_app.command("zotero-sync")
def import_zotero_sync(
    collection: Optional[str] = typer.Option(None, "--collection", help="Zotero collection key"),
    full: bool = typer.Option(False, "--full", help="Full resync instead of incremental"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild graph after sync"),
) -> None:
    """Sync Zotero library via Web API (requires ZOTERO_USER_ID and ZOTERO_API_KEY)."""
    from litgraph.integrations.zotero import sync_zotero_library

    ctx = config_manager.resolve_context()
    result = sync_zotero_library(
        ctx.bib_cache_dir,
        collection_key=collection,
        full_sync=full,
    )
    console.print(
        f"Synced {result.get('synced', 0)} entries (version {result.get('last_version')})."
    )
    if rebuild:
        build_result = helpers.build_paper_graph(ctx)
        console.print(f"Rebuilt graph: {build_result.get('papers_indexed', 0)} paper(s).")


@query_app.command("papers")
def query_papers(
    method: Optional[str] = typer.Option(None, "--method"),
    task: Optional[str] = typer.Option(None, "--task"),
) -> None:
    """Query papers by method or task."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "papers", method=method, task=task)
    helpers.print_query_result(result)


@query_app.command("limitations")
def query_limitations(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Find limitations related to a topic."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "limitations", topic=topic)
    helpers.print_query_result(result)


@query_app.command("compare")
def query_compare(
    paper_ids: List[str] = typer.Argument(..., help="Paper IDs to compare"),
) -> None:
    """Compare papers side by side."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "compare", paper_ids=paper_ids)
    helpers.print_query_result(result)


@query_app.command("matrix")
def query_matrix(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Build a literature matrix for a topic."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "matrix", topic=topic)
    helpers.print_query_result(result)


@query_app.command("paper")
def query_paper(
    paper_id: str = typer.Argument(..., help="Paper ID"),
) -> None:
    """Summarize a paper."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "paper", paper_id=paper_id)
    helpers.print_query_result(result)


@query_app.command("claim")
def query_claim(
    claim_id: str = typer.Argument(..., help="Claim ID"),
) -> None:
    """Get evidence for a claim."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "claim", claim_id=claim_id)
    helpers.print_query_result(result)


@query_app.command("neighbors")
def query_neighbors(
    paper_id: str = typer.Option(..., "--paper-id"),
    include_summary: bool = typer.Option(False, "--include-summary"),
) -> None:
    """List graph neighbors (CITES, CONTRASTS_WITH, EXTENDS) for a paper."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "neighbors", paper_id=paper_id, include_summary=include_summary)
    helpers.print_query_result(result)


@query_app.command("outline")
def query_outline(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Generate related work section outline."""
    ctx = config_manager.resolve_context()
    result = helpers.run_query(ctx, "outline", topic=topic)
    helpers.print_query_result(result)


@app.command("serve-mcp")
def serve_mcp() -> None:
    """Start MCP stdio server."""
    from litgraph.mcp.server import MCPServer

    MCPServer().run()


@mcp_app.command("setup")
def mcp_setup() -> None:
    """Generate mcp.json for Cursor / Claude Desktop."""
    out = configure_mcp_client()
    console.print(f"[green]Wrote[/green] {out}")


@app.command("version")
def version_cmd() -> None:
    console.print(__version__)
