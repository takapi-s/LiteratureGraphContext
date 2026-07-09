"""LiteratureGraph CLI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional

import json
import typer
from rich.console import Console

from litgraph import __version__
from litgraph.cli import config_manager, helpers
from litgraph.cli.config_manager import ProjectNotFoundError, ResolvedContext, workspace_from_env
from litgraph.mcp.setup_wizard import run_setup_wizard

app = typer.Typer(name="litgraph", help="LiteratureGraphContext: papers to knowledge graph.")
config_app = typer.Typer(help="Project configuration commands.")
mcp_app = typer.Typer(help="MCP configuration commands.")
query_app = typer.Typer(help="Query the literature graph.")
app.add_typer(config_app, name="config")
app.add_typer(mcp_app, name="mcp")
app.add_typer(query_app, name="query")
console = Console(stderr=True)
_workspace_option = typer.Option(
    workspace_from_env(),
    "--workspace",
    "-w",
    help="Workspace id for scoped graph operations (default: default)",
)


def _ctx(*, quiet: bool = False, workspace: Optional[str] = None) -> ResolvedContext:
    """Resolve project context or exit with an actionable error message."""
    ws = workspace if workspace is not None else _active_workspace()
    try:
        ctx = config_manager.resolve_context(workspace_id=ws)
    except ProjectNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if not quiet:
        papers = ctx.config.get("papers_dir", "papers")
        console.print(
            f"[dim][litgraph] project: {ctx.project_root} "
            f"(papers_dir: {papers}, workspace: {ctx.workspace_id})[/dim]"
        )
    return ctx


@app.callback()
def main(
    workspace: str = _workspace_option,
) -> None:
    config_manager.load_env()
    # workspace is resolved per-command via _ctx(workspace=workspace)
    main._workspace = workspace  # type: ignore[attr-defined]


def _active_workspace() -> Optional[str]:
    return getattr(main, "_workspace", None)


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


_LEGACY_PROJECT_ARTIFACTS = (
    "config.yaml",
    "graph.json",
    "paper_registry.json",
)


def _count_pdfs(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob("*.pdf"))


def _legacy_home_project_artifacts() -> list[str]:
    global_dir = config_manager.GLOBAL_CONFIG_DIR
    found: list[str] = []
    for name in _LEGACY_PROJECT_ARTIFACTS:
        if (global_dir / name).exists():
            found.append(name)
    for subdir in ("cache", "db"):
        path = global_dir / subdir
        if path.is_dir() and any(path.iterdir()):
            found.append(f"{subdir}/")
    return found


@app.command("doctor")
def doctor_cmd() -> None:
    """Diagnose project resolution and legacy ~/.litgraph project artifacts."""
    env_root = os.getenv("LITGRAPH_PROJECT_ROOT", "").strip()
    if env_root:
        console.print(f"[cyan]LITGRAPH_PROJECT_ROOT[/cyan]: {env_root}")
    else:
        console.print("[cyan]LITGRAPH_PROJECT_ROOT[/cyan]: (not set)")

    console.print(
        f"[cyan]Global config[/cyan]: {config_manager.GLOBAL_CONFIG_DIR} "
        "(API keys and logs only; not a project)"
    )

    try:
        ctx = config_manager.resolve_context()
    except ProjectNotFoundError as exc:
        console.print(f"\n[yellow]No active project:[/yellow] {exc}")
        ctx = None
    else:
        pdf_count = _count_pdfs(ctx.papers_dir)
        graph_path = ctx.litgraph_dir / "graph.json"
        db_dir = ctx.litgraph_dir / "db"
        has_graph = graph_path.exists() or (
            db_dir.is_dir() and any(db_dir.iterdir())
        )
        console.print("\n[green]Active project[/green]")
        console.print(f"  root:       {ctx.project_root}")
        console.print(f"  litgraph:   {ctx.litgraph_dir}")
        console.print(f"  papers_dir: {ctx.papers_dir} ({pdf_count} PDF(s))")
        console.print(f"  graph:      {'ready' if has_graph else 'not built'}")

    legacy = _legacy_home_project_artifacts()
    if legacy:
        console.print(
            "\n[yellow]Legacy project artifacts in ~/.litgraph[/yellow] "
            "(should not be used as a project):"
        )
        for item in legacy:
            console.print(f"  - {item}")
        console.print(
            "\n[dim]Recommended: initialize a repo-local project and rebuild there:[/dim]"
        )
        console.print("  cd /path/to/your/repo")
        console.print("  litgraph init --papers-dir ./papers")
        console.print("  litgraph scan ./papers && litgraph parse && litgraph extract -y && litgraph build")
        console.print(
            "\n[dim]If you had graph data only under ~/.litgraph, copy artifacts manually "
            "after verifying papers_dir paths, then remove legacy project files "
            "from ~/.litgraph (keep .env and logs/).[/dim]"
        )
    else:
        console.print("\n[green]No legacy project artifacts in ~/.litgraph[/green]")

    if ctx is None and not legacy:
        console.print(
            "\n[dim]Run litgraph init --papers-dir ./papers in your repository to get started.[/dim]"
        )


@app.command("scan")
def scan_cmd(
    papers_path: Optional[Path] = typer.Argument(None, help="Papers directory (optional)"),
) -> None:
    """Scan papers folder and update file hash cache."""
    ctx = _ctx()
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
    ctx = _ctx()
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
    ctx = _ctx()
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
    ctx = _ctx()
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
    failed = result.get("failed") or []
    if skipped:
        console.print(
            f"Extracted {extracted} paper(s), skipped {skipped} already up to date "
            f"via {result.get('provider')}."
        )
    else:
        console.print(f"Extracted {extracted} paper(s) via {result.get('provider')}.")
    if failed:
        console.print(f"[red]Failed to extract {len(failed)} paper(s):[/red]")
        for item in failed:
            console.print(f"  - {item.get('paper_id')}: {item.get('error')}")


@app.command("build")
def build_cmd(
    enrich_s2: bool = typer.Option(False, "--enrich-s2", help="Enrich metadata via Semantic Scholar"),
) -> None:
    """Build graph from extracted JSON and bib metadata."""
    ctx = _ctx()
    result = helpers.build_paper_graph(ctx, enrich_s2=enrich_s2)
    console.print(
        f"Indexed {result.get('papers_indexed', 0)} paper(s), "
        f"nodes={result.get('nodes', 0)}, edges={result.get('edges', 0)}, "
        f"cites_from_references={result.get('cites_from_references', 0)}."
    )


@app.command("rebuild")
def rebuild_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    with_extract: bool = typer.Option(False, "--with-extract", help="Run LLM extract before build"),
    force_extract: bool = typer.Option(False, "--force-extract", help="Force re-extract all papers (implies --with-extract)"),
    enrich_s2: bool = typer.Option(False, "--enrich-s2", help="Enrich metadata via Semantic Scholar on rebuild"),
    clear_parsed: bool = typer.Option(False, "--clear-parsed", help="Delete parsed cache before parsing"),
    clear_extracted: bool = typer.Option(False, "--clear-extracted", help="Delete extracted cache before extracting/building"),
    clear_embeddings: bool = typer.Option(True, "--clear-embeddings/--keep-embeddings", help="Clear embedding cache (default: clear)"),
) -> None:
    """Delete local DB artifacts and rebuild from scan → parse → (optional) extract → build.

    Notes:
    - For Kuzu backend, this removes the local DB directory under .litgraph/db.
    - For Neo4j backend, the DB is remote; this command will NOT delete the remote DB.
    """
    ctx = _ctx()
    backend = str(ctx.config.get("database") or "kuzu")
    do_extract = with_extract or force_extract

    targets = []
    if backend == "kuzu":
        targets.append(str(ctx.litgraph_dir / "db"))
    targets.append(str(ctx.litgraph_dir / "graph.json"))
    targets.append(str(ctx.litgraph_dir / "cache" / "entity_catalog.json"))
    if clear_embeddings:
        targets.append(str(ctx.litgraph_dir / "cache" / "embeddings.json"))
    if clear_parsed:
        targets.append(str(ctx.litgraph_dir / "cache" / "parsed"))
    if clear_extracted:
        targets.append(str(ctx.litgraph_dir / "cache" / "extracted"))

    if not yes:
        message = (
            "This will delete local LitGraph artifacts and rebuild.\n\n"
            f"Backend: {backend}\n"
            + ("(Kuzu DB under .litgraph/db will be deleted)\n" if backend == "kuzu" else "(Remote DB will NOT be deleted)\n")
            + "\nDelete targets:\n  - "
            + "\n  - ".join(targets)
            + "\n\nProceed?"
        )
        if not typer.confirm(message, default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Delete selected artifacts.
    if backend == "kuzu":
        shutil.rmtree(ctx.litgraph_dir / "db", ignore_errors=True)
        (ctx.litgraph_dir / "db").mkdir(parents=True, exist_ok=True)

    for path in [
        ctx.litgraph_dir / "graph.json",
        ctx.litgraph_dir / "cache" / "entity_catalog.json",
        ctx.litgraph_dir / "cache" / "embeddings.json",
    ]:
        if path.exists() and (path.name != "embeddings.json" or clear_embeddings):
            try:
                path.unlink()
            except OSError:
                pass

    if clear_parsed:
        shutil.rmtree(ctx.litgraph_dir / "cache" / "parsed", ignore_errors=True)
    if clear_extracted:
        shutil.rmtree(ctx.litgraph_dir / "cache" / "extracted", ignore_errors=True)

    # Ensure cache dirs exist.
    (ctx.litgraph_dir / "cache" / "parsed").mkdir(parents=True, exist_ok=True)
    (ctx.litgraph_dir / "cache" / "extracted").mkdir(parents=True, exist_ok=True)

    # Re-run pipeline.
    scan = helpers.scan_papers(ctx, None, persist_dir=False)
    console.print(f"Scanned {scan['total']} files ({scan['changed']} changed).")
    parsed = helpers.parse_papers(ctx, only_changed=False, verbose=False)
    console.print(f"Parsed {parsed.get('parsed', 0)} paper(s), {parsed.get('bib_files', 0)} bib file(s).")

    if do_extract:
        result = helpers.extract_papers(
            ctx,
            skip_confirm=yes,
            force=force_extract,
            show_progress=True,
        )
        if result.get("cancelled"):
            console.print("[yellow]Extraction cancelled.[/yellow]")
            return
        console.print(
            f"Extracted {result.get('extracted', 0)} paper(s), skipped {result.get('skipped', 0)}."
        )

    built = helpers.build_paper_graph(ctx, enrich_s2=enrich_s2)
    console.print(
        f"[green]Rebuilt[/green] {built.get('papers_indexed', 0)} paper(s): "
        f"nodes={built.get('nodes', 0)}, edges={built.get('edges', 0)}."
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
    ctx = _ctx()

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
    ctx = _ctx()
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

    ctx = _ctx()
    entries = import_zotero_export(export_path.resolve(), ctx.bib_cache_dir)
    console.print(f"Imported {len(entries)} entries from Zotero export.")


@import_app.command("zotero-sync")
def import_zotero_sync(
    collection: Optional[str] = typer.Option(None, "--collection", help="Zotero collection key"),
    full: bool = typer.Option(False, "--full", help="Full resync instead of incremental"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild graph after sync"),
    with_pdfs: bool = typer.Option(False, "--with-pdfs", help="Fetch and ingest PDF attachments after bib sync"),
) -> None:
    """Sync Zotero library via Web API (requires ZOTERO_USER_ID and ZOTERO_API_KEY)."""
    from litgraph.integrations.zotero import sync_zotero_library, sync_zotero_with_pdfs

    ctx = _ctx()
    if with_pdfs:
        result = sync_zotero_with_pdfs(
            ctx,
            collection_key=collection,
            full_sync=full,
            build=rebuild,
        )
        console.print(
            f"Synced {result.get('synced', 0)} bib entries; "
            f"ingested {result.get('pdfs_ingested', 0)} PDF(s), "
            f"skipped {result.get('pdfs_skipped', 0)}."
        )
        if result.get("pdf_errors"):
            for err in result["pdf_errors"][:5]:
                console.print(f"[yellow]{err}[/yellow]")
        return

    result = sync_zotero_library(
        ctx.bib_cache_dir,
        collection_key=collection,
        full_sync=full,
        config=ctx.config,
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
    ctx = _ctx()
    result = helpers.run_query(ctx, "papers", method=method, task=task)
    helpers.print_query_result(result)


@query_app.command("limitations")
def query_limitations(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Find limitations related to a topic."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "limitations", topic=topic)
    helpers.print_query_result(result)


@query_app.command("compare")
def query_compare(
    paper_ids: List[str] = typer.Argument(..., help="Paper IDs to compare"),
) -> None:
    """Compare papers side by side."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "compare", paper_ids=paper_ids)
    helpers.print_query_result(result)


@query_app.command("matrix")
def query_matrix(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Build a literature matrix for a topic."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "matrix", topic=topic)
    helpers.print_query_result(result)


@query_app.command("paper")
def query_paper(
    paper_id: str = typer.Argument(..., help="Paper ID"),
) -> None:
    """Summarize a paper."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "paper", paper_id=paper_id)
    helpers.print_query_result(result)


@query_app.command("claim")
def query_claim(
    claim_id: str = typer.Argument(..., help="Claim ID"),
) -> None:
    """Get evidence for a claim."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "claim", claim_id=claim_id)
    helpers.print_query_result(result)


@query_app.command("neighbors")
def query_neighbors(
    paper_id: str = typer.Option(..., "--paper-id"),
    include_summary: bool = typer.Option(False, "--include-summary"),
) -> None:
    """List graph neighbors (CITES, CONTRASTS_WITH, EXTENDS) for a paper."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "neighbors", paper_id=paper_id, include_summary=include_summary)
    helpers.print_query_result(result)


@query_app.command("search")
def query_search(
    query: str = typer.Option(..., "--query"),
    top_k: int = typer.Option(10, "--top-k"),
) -> None:
    """Search papers by natural-language query."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "search", topic=query)
    helpers.print_query_result(result)


@query_app.command("expand")
def query_expand(
    paper_id: str = typer.Option(..., "--paper-id"),
    hops: int = typer.Option(2, "--hops"),
) -> None:
    """Expand the literature graph from a seed paper."""
    ctx = _ctx()
    finder = helpers._finder(ctx)
    result = finder.expand_paper_graph(paper_id, hops=hops)
    helpers.print_query_result(result)


@query_app.command("outline")
def query_outline(
    topic: str = typer.Option(..., "--topic"),
) -> None:
    """Generate related work section outline."""
    ctx = _ctx()
    result = helpers.run_query(ctx, "outline", topic=topic)
    helpers.print_query_result(result)


@app.command("test-mcp")
def test_mcp_cmd(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project root"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print failed payloads"),
) -> None:
    """Smoke-test all MCP tools against the project graph."""
    from litgraph.mcp.test_runner import run_mcp_smoke_tests

    result = run_mcp_smoke_tests(path.resolve(), verbose=verbose)
    if result["failed"]:
        raise typer.Exit(code=1)


@app.command("serve-mcp")
def serve_mcp(
    http: bool = typer.Option(False, "--http", help="Use Streamable HTTP transport instead of stdio"),
    host: str = typer.Option("127.0.0.1", "--host", help="HTTP bind host (with --http)"),
    port: int = typer.Option(8000, "--port", help="HTTP bind port (with --http)"),
) -> None:
    """Start MCP server (stdio by default, or HTTP with --http)."""
    from litgraph.mcp.server import MCPServer

    MCPServer().run(http=http, host=host, port=port)


@mcp_app.command("setup")
def mcp_setup(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project root"),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Non-interactive: write mcp.json in the project root"
    ),
) -> None:
    """Interactive MCP onboarding (project, LLM, API key, client config)."""
    out = run_setup_wizard(path.resolve(), yes=yes)
    if yes:
        console.print(f"[green]Wrote[/green] {out}")


@app.command("version")
def version_cmd() -> None:
    console.print(__version__)
