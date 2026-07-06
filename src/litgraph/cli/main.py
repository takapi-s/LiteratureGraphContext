"""LiteratureGraph CLI."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

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
) -> None:
    """Parse PDFs, Markdown notes, and BibTeX metadata into cache."""
    ctx = config_manager.resolve_context()
    result = helpers.parse_papers(ctx, only_changed=not all_files)
    console.print(
        f"Parsed {result['parsed']} paper(s), {result.get('bib_files', 0)} bib file(s)."
    )


@app.command("extract")
def extract_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip external API confirmation"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider override"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model override"),
    background: bool = typer.Option(False, "--background", help="Run extraction in background job"),
) -> None:
    """Extract structured data from parsed papers using LLM."""
    ctx = config_manager.resolve_context()
    if background:
        job_id = helpers.extract_papers_async(ctx, skip_confirm=yes, provider=provider, model=model)
        console.print(f"Started extraction job: {job_id}")
        return
    result = helpers.extract_papers(ctx, skip_confirm=yes, provider=provider, model=model)
    if result.get("cancelled"):
        console.print("[yellow]Extraction cancelled.[/yellow]")
        return
    console.print(f"Extracted {result.get('extracted', 0)} paper(s) via {result.get('provider')}.")


@app.command("build")
def build_cmd() -> None:
    """Build Kuzu graph from extracted JSON."""
    ctx = config_manager.resolve_context()
    result = helpers.build_paper_graph(ctx)
    console.print(f"Indexed {result.get('papers_indexed', 0)} paper(s), nodes={result.get('nodes', 0)}.")


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
