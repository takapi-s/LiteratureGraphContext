"""Interactive onboarding wizard (project, LLM, keys, Zotero, MCP, first index)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt

from litgraph.cli import config_manager, helpers

console = Console(stderr=True)

_PROVIDERS = ("openai", "anthropic", "gemini", "ollama")

_PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

_PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.2",
}

_SERVER_NAME = "literature-graph-context"


def _default_mcp_transport() -> str:
    """Windows defaults to daemon-http to avoid stdio Kuzu lock conflicts."""
    return "daemon-http" if sys.platform == "win32" else "stdio"


def resolve_litgraph_mcp_command() -> tuple[str, list[str]]:
    """Return (command, args) to run `litgraph serve-mcp` on any platform."""
    litgraph = shutil.which("litgraph")
    if litgraph:
        return litgraph, ["serve-mcp"]
    return sys.executable, ["-m", "litgraph", "serve-mcp"]


def build_mcp_client_config(project_root: Path) -> dict:
    """Build a Cursor / Claude Desktop MCP config for the given project."""
    command, args = resolve_litgraph_mcp_command()
    return {
        "mcpServers": {
            _SERVER_NAME: {
                "command": command,
                "args": args,
                "env": {
                    "LITGRAPH_PROJECT_ROOT": str(project_root.resolve()),
                },
            }
        }
    }


def build_daemon_http_mcp_config(project_root: Path, port: int = 8766) -> dict:
    """Build MCP config pointing at a running ``litgraph daemon`` HTTP endpoint."""
    _ = project_root  # reserved for future per-project daemon routing
    return {
        "mcpServers": {
            _SERVER_NAME: {
                "url": f"http://127.0.0.1:{port}/mcp",
            }
        }
    }


def _merge_mcp_entry(target: Path, entry: dict) -> Path:
    existing: dict = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, OSError):
            existing = {}
    servers = existing.setdefault("mcpServers", {})
    servers[_SERVER_NAME] = entry
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")
    return target


def _merge_mcp_config(target: Path, project_root: Path) -> Path:
    """Write or merge the litgraph server entry into an MCP config JSON file."""
    entry = build_mcp_client_config(project_root)["mcpServers"][_SERVER_NAME]
    return _merge_mcp_entry(target, entry)


def configure_mcp_client(project_root: Path | None = None) -> Path:
    """Non-interactive: write mcp.json in the project root (legacy behavior)."""
    root = project_root or Path.cwd()
    return _merge_mcp_config(root / "mcp.json", root)


def _claude_desktop_config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _ensure_project(root: Path, papers_dir: Optional[Path] = None) -> Path:
    """Return the .litgraph dir, initializing the project interactively if needed."""
    litgraph_dir = root / config_manager.PROJECT_DIR_NAME
    if (litgraph_dir / "config.yaml").is_file():
        console.print(f"[green]Project found:[/green] {litgraph_dir}")
        return litgraph_dir
    console.print(f"[yellow]No .litgraph project in {root}.[/yellow]")
    if papers_dir is not None:
        papers_path = papers_dir if papers_dir.is_absolute() else root / papers_dir
    else:
        papers_raw = Prompt.ask("Papers directory", default="./papers")
        papers_path = Path(papers_raw)
        if not papers_path.is_absolute():
            papers_path = root / papers_path
    papers_path.mkdir(parents=True, exist_ok=True)
    litgraph_dir = config_manager.init_project(root, papers_dir=str(papers_path))
    console.print(f"[green]Initialized[/green] {litgraph_dir}")
    return litgraph_dir


def _configure_llm(litgraph_dir: Path, root: Path) -> str:
    config = config_manager.load_project_config(litgraph_dir)
    current_provider = str(config.get("llm_provider", "openai"))
    provider = Prompt.ask(
        "LLM provider",
        choices=list(_PROVIDERS),
        default=current_provider if current_provider in _PROVIDERS else "openai",
    )
    default_model = (
        str(config.get("llm_model"))
        if provider == current_provider and config.get("llm_model")
        else _PROVIDER_DEFAULT_MODELS[provider]
    )
    model = Prompt.ask("LLM model", default=default_model)
    config_manager.save_config_value(litgraph_dir, "llm_provider", provider, root)
    config_manager.save_config_value(litgraph_dir, "llm_model", model, root)
    console.print(f"[green]Saved[/green] llm_provider={provider}, llm_model={model}")
    return provider


def _append_env_line(env_file: Path, key: str, value: str) -> None:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    lines = existing.splitlines() if existing else []
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{key}=") and not line.strip().startswith("#"):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        if new_lines and new_lines[-1] != "":
            new_lines.append(f"{key}={value}")
        else:
            new_lines.append(f"{key}={value}")
    text = "\n".join(new_lines)
    if text and not text.endswith("\n"):
        text += "\n"
    env_file.write_text(text, encoding="utf-8")


def _configure_api_key(provider: str) -> None:
    env_key = _PROVIDER_ENV_KEYS.get(provider)
    if not env_key:
        console.print("[dim]Ollama runs locally; no API key needed.[/dim]")
        return
    config_manager.load_env()
    if os.getenv(env_key):
        console.print(f"[green]{env_key} already set.[/green]")
        return
    console.print(f"[yellow]{env_key} is not set.[/yellow]")
    if not Confirm.ask(f"Store {env_key} in {config_manager.GLOBAL_ENV_FILE}?", default=True):
        console.print(f"[dim]Skipped. Set {env_key} in your environment before extracting.[/dim]")
        return
    value = Prompt.ask(env_key, password=True)
    if value.strip():
        _append_env_line(config_manager.GLOBAL_ENV_FILE, env_key, value.strip())
        os.environ[env_key] = value.strip()
        console.print(f"[green]Saved[/green] {env_key} to {config_manager.GLOBAL_ENV_FILE}")
    else:
        console.print("[dim]Empty input; skipped.[/dim]")


def _configure_zotero() -> bool:
    """Optionally collect Zotero API key; user ID is resolved automatically."""
    from litgraph.integrations.zotero import (
        _is_numeric_user_id,
        resolve_user_id_from_api_key,
    )

    config_manager.load_env()
    existing_key = (os.getenv("ZOTERO_API_KEY") or "").strip()
    existing_uid = (os.getenv("ZOTERO_USER_ID") or "").strip()
    if existing_key and _is_numeric_user_id(existing_uid):
        console.print("[green]Zotero credentials already set.[/green]")
        return Confirm.ask("Use Zotero as a paper source?", default=False)

    if existing_key and existing_uid and not _is_numeric_user_id(existing_uid):
        console.print(
            f"[yellow]ZOTERO_USER_ID={existing_uid!r} looks like a username, "
            "not the numeric API user ID. Resolving from API key…[/yellow]"
        )
        try:
            uid = resolve_user_id_from_api_key(existing_key)
        except Exception as exc:
            console.print(f"[red]Could not resolve user ID:[/red] {exc}")
            if not Confirm.ask("Enter a new Zotero API key?", default=True):
                return False
            existing_key = ""
        else:
            _append_env_line(config_manager.GLOBAL_ENV_FILE, "ZOTERO_USER_ID", uid)
            os.environ["ZOTERO_USER_ID"] = uid
            console.print(f"[green]Resolved[/green] ZOTERO_USER_ID={uid}")
            return Confirm.ask("Use Zotero as a paper source?", default=True)

    if existing_key and not existing_uid:
        try:
            uid = resolve_user_id_from_api_key(existing_key)
        except Exception as exc:
            console.print(f"[red]Could not resolve user ID from existing key:[/red] {exc}")
            existing_key = ""
        else:
            _append_env_line(config_manager.GLOBAL_ENV_FILE, "ZOTERO_USER_ID", uid)
            os.environ["ZOTERO_USER_ID"] = uid
            console.print(f"[green]Resolved[/green] ZOTERO_USER_ID={uid} from existing API key")
            return Confirm.ask("Use Zotero as a paper source?", default=True)

    if not Confirm.ask("Configure Zotero sync?", default=False):
        return False

    console.print(
        "[dim]Create a private key at https://www.zotero.org/settings/keys "
        f"(library read access). Stored in {config_manager.GLOBAL_ENV_FILE}. "
        "User ID is resolved automatically — do not enter your username.[/dim]"
    )
    api_key = Prompt.ask("ZOTERO_API_KEY", password=True).strip()
    if not api_key:
        console.print("[dim]Empty key; skipped Zotero.[/dim]")
        return False
    try:
        uid = resolve_user_id_from_api_key(api_key)
    except Exception as exc:
        console.print(f"[red]Zotero key validation failed:[/red] {exc}")
        return False
    _append_env_line(config_manager.GLOBAL_ENV_FILE, "ZOTERO_API_KEY", api_key)
    _append_env_line(config_manager.GLOBAL_ENV_FILE, "ZOTERO_USER_ID", uid)
    os.environ["ZOTERO_API_KEY"] = api_key
    os.environ["ZOTERO_USER_ID"] = uid
    console.print(
        f"[green]Saved[/green] Zotero API key and user ID {uid} "
        f"to {config_manager.GLOBAL_ENV_FILE}"
    )
    return True


def _configure_client(root: Path) -> Optional[Path]:
    target_choice = Prompt.ask(
        "MCP client",
        choices=["cursor", "claude-desktop", "generic", "skip"],
        default="cursor",
    )
    if target_choice == "skip":
        console.print("[dim]Skipped MCP client config.[/dim]")
        return None
    if target_choice == "cursor":
        target = root / ".cursor" / "mcp.json"
    elif target_choice == "claude-desktop":
        target = _claude_desktop_config_path()
    else:
        target = root / "mcp.json"

    default_transport = _default_mcp_transport()
    transport = Prompt.ask(
        "MCP transport",
        choices=["stdio", "daemon-http"],
        default=default_transport,
    )
    if transport == "daemon-http":
        port_raw = Prompt.ask("Daemon HTTP port", default="8766").strip() or "8766"
        try:
            port = int(port_raw)
        except ValueError:
            port = 8766
        entry = build_daemon_http_mcp_config(root, port=port)["mcpServers"][_SERVER_NAME]
        out = _merge_mcp_entry(target, entry)
        console.print(f"[green]Wrote[/green] {out}")
        console.print(
            "[dim]Start the daemon in another terminal:[/dim] litgraph daemon "
            f"--port {port}"
        )
        console.print(
            "[dim]Do not run stdio serve-mcp at the same time; use only the daemon "
            "HTTP endpoint to avoid Kuzu lock conflicts.[/dim]"
        )
        return out

    out = _merge_mcp_config(target, root)
    console.print(f"[green]Wrote[/green] {out}")
    return out


def _papers_status(root: Path) -> tuple[Path, int, bool]:
    litgraph_dir = root / config_manager.PROJECT_DIR_NAME
    config = config_manager.load_project_config(litgraph_dir)
    papers_dir = Path(str(config.get("papers_dir", "papers")))
    if not papers_dir.is_absolute():
        papers_dir = root / papers_dir
    pdf_count = sum(1 for _ in papers_dir.glob("*.pdf")) if papers_dir.is_dir() else 0
    db_dir = litgraph_dir / "db"
    has_graph = (litgraph_dir / "graph.json").exists() or (
        db_dir.is_dir() and any(db_dir.iterdir())
    )
    return papers_dir, pdf_count, has_graph


def _run_first_index(root: Path, *, use_zotero: bool) -> None:
    papers_dir, pdf_count, has_graph = _papers_status(root)
    console.print("\n[bold]Status[/bold]")
    console.print(f"  papers_dir: {papers_dir} ({pdf_count} PDF(s))")
    console.print(f"  graph:      {'ready' if has_graph else 'not built'}")

    if use_zotero:
        if not Confirm.ask("Sync Zotero library with PDFs now?", default=True):
            console.print("[dim]Later: litgraph import zotero-sync --with-pdfs[/dim]")
            return
        ctx = config_manager.resolve_context(root)
        from litgraph.integrations.zotero import sync_zotero_with_pdfs

        try:
            result = sync_zotero_with_pdfs(ctx, full_sync=False, build=True)
        except Exception as exc:
            console.print(f"[red]Zotero sync failed:[/red] {exc}")
            console.print("[dim]Fix credentials or retry: litgraph import zotero-sync --with-pdfs[/dim]")
            return
        console.print(
            f"Synced {result.get('synced', 0)} bib entries; "
            f"ingested {result.get('pdfs_ingested', 0)} PDF(s)."
        )
        if result.get("pdf_errors"):
            for err in result["pdf_errors"][:5]:
                console.print(f"[yellow]{err}[/yellow]")
        return

    if pdf_count == 0 and not has_graph:
        console.print(
            "\n[yellow]No PDFs found yet.[/yellow] Add files to the papers directory, then run:"
        )
        console.print("  litgraph index")
        return

    if not Confirm.ask("Run first index now (scan → parse → extract → build)?", default=True):
        console.print("[dim]Later: litgraph index[/dim]")
        return

    ctx = config_manager.resolve_context(root)
    result = helpers.index_papers(ctx, skip_confirm=False, show_progress=True)
    if result.get("cancelled"):
        console.print("[yellow]Extraction cancelled; graph not rebuilt.[/yellow]")
        console.print("[dim]Later: litgraph index -y[/dim]")
        return
    built = result.get("build") or {}
    console.print(
        f"[green]Indexed[/green] {built.get('papers_indexed', 0)} paper(s): "
        f"nodes={built.get('nodes', 0)}, edges={built.get('edges', 0)}."
    )


def _final_hints(root: Path, mcp_out: Optional[Path]) -> None:
    _, _, has_graph = _papers_status(root)
    if not has_graph:
        console.print("\n[dim]When ready:[/dim] litgraph index -y")
        console.print("[dim]No API key yet?[/dim] litgraph index -y --no-extract")
    else:
        console.print("\n[dim]Verify MCP tools with:[/dim] litgraph test-mcp")
    console.print(
        "\n[dim]Full walkthrough:[/dim] docs/TUTORIAL.md "
        "(setup → index → MCP → viz → Zotero)"
    )
    if sys.platform == "win32":
        console.print(
            "[dim]Windows: prefer[/dim] litgraph daemon "
            "[dim]+ daemon-http MCP (avoids Kuzu lock conflicts).[/dim]"
        )
        console.print(
            "[dim]Autostart: Task Scheduler → At log on →[/dim] litgraph daemon"
        )
    else:
        console.print(
            "[dim]Optional long-running hub:[/dim] litgraph daemon "
            "[dim](Zotero auto-sync + settings UI + HTTP MCP)[/dim]"
        )
    if mcp_out is not None:
        console.print("[dim]Restart your MCP client to pick up the new configuration.[/dim]")


def run_setup_wizard(
    project_root: Path | None = None,
    yes: bool = False,
    papers_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Interactive onboarding: project, LLM, API key, Zotero, MCP, first index."""
    root = (project_root or Path.cwd()).resolve()
    if yes:
        litgraph_dir = root / config_manager.PROJECT_DIR_NAME
        if not (litgraph_dir / "config.yaml").is_file():
            papers = papers_dir or Path("./papers")
            papers_path = papers if papers.is_absolute() else root / papers
            papers_path.mkdir(parents=True, exist_ok=True)
            config_manager.init_project(root, papers_dir=str(papers_path))
            console.print(f"[green]Initialized[/green] {litgraph_dir}")
        return configure_mcp_client(root)

    console.print("[bold]LiteratureGraphContext setup[/bold]\n")
    litgraph_dir = _ensure_project(root, papers_dir=papers_dir)
    provider = _configure_llm(litgraph_dir, root)
    _configure_api_key(provider)
    use_zotero = _configure_zotero()
    out = _configure_client(root)
    _run_first_index(root, use_zotero=use_zotero)
    _final_hints(root, out)
    return out
