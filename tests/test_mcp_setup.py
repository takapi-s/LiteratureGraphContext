import json
from pathlib import Path
from unittest.mock import MagicMock

from litgraph.mcp import setup_wizard


def test_build_mcp_client_config_uses_env_not_cwd(tmp_path: Path):
    config = setup_wizard.build_mcp_client_config(tmp_path)

    server = config["mcpServers"]["literature-graph-context"]
    assert server["command"] != "bash"
    assert server["args"] == ["serve-mcp"] or server["args"][-2:] == ["litgraph", "serve-mcp"]
    assert server["env"]["LITGRAPH_PROJECT_ROOT"] == str(tmp_path.resolve())
    assert "cwd" not in server
    assert "serve-mcp" in server["args"]


def test_configure_mcp_client_writes_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"]))

    out = setup_wizard.configure_mcp_client(tmp_path)
    assert out == tmp_path / "mcp.json"

    data = json.loads(out.read_text(encoding="utf-8"))
    server = data["mcpServers"]["literature-graph-context"]
    assert server["command"] == "/usr/bin/litgraph"
    assert server["args"] == ["serve-mcp"]
    assert server["env"]["LITGRAPH_PROJECT_ROOT"] == str(tmp_path.resolve())


def test_resolve_litgraph_mcp_command_falls_back_to_python_module(monkeypatch):
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda _name: None)
    monkeypatch.setattr(setup_wizard.sys, "executable", "/usr/bin/python3")

    command, args = setup_wizard.resolve_litgraph_mcp_command()
    assert command == "/usr/bin/python3"
    assert args == ["-m", "litgraph", "serve-mcp"]


def test_merge_mcp_config_preserves_other_servers(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"])
    )
    target = tmp_path / ".cursor" / "mcp.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"mcpServers": {"other-server": {"command": "foo", "args": []}}}),
        encoding="utf-8",
    )

    out = setup_wizard._merge_mcp_config(target, tmp_path)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "other-server" in data["mcpServers"]
    assert "literature-graph-context" in data["mcpServers"]


def test_run_setup_wizard_yes_is_noninteractive(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"])
    )
    out = setup_wizard.run_setup_wizard(tmp_path, yes=True)
    assert out == tmp_path / "mcp.json"
    assert json.loads(out.read_text(encoding="utf-8"))["mcpServers"]
    assert (tmp_path / ".litgraph" / "config.yaml").is_file()


def test_run_setup_wizard_interactive_flow(tmp_path: Path, monkeypatch):
    """Wizard initializes project, saves LLM config, and writes .cursor/mcp.json."""
    import yaml

    monkeypatch.setattr(
        setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"])
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    answers = iter([
        "./papers",     # papers directory
        "openai",       # provider
        "gpt-4o-mini",  # model
        "cursor",       # MCP client
        "stdio",        # MCP transport
    ])
    monkeypatch.setattr(
        setup_wizard.Prompt, "ask", staticmethod(lambda *a, **k: next(answers))
    )
    # Zotero? no; first index? no (no PDFs anyway — still asked only if PDFs exist)
    confirm_answers = iter([False])  # configure Zotero? no
    monkeypatch.setattr(
        setup_wizard.Confirm, "ask", staticmethod(lambda *a, **k: next(confirm_answers))
    )

    out = setup_wizard.run_setup_wizard(tmp_path)

    assert out == tmp_path / ".cursor" / "mcp.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mcpServers"]["literature-graph-context"]["env"][
        "LITGRAPH_PROJECT_ROOT"
    ] == str(tmp_path.resolve())

    config = yaml.safe_load(
        (tmp_path / ".litgraph" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config["llm_provider"] == "openai"
    assert config["llm_model"] == "gpt-4o-mini"
    assert (tmp_path / "papers").is_dir()


def test_append_env_line_updates_existing(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=old\nBAR=keep\n", encoding="utf-8")
    setup_wizard._append_env_line(env_file, "FOO", "new")
    text = env_file.read_text(encoding="utf-8")
    assert "FOO=new" in text
    assert "BAR=keep" in text
    assert text.count("FOO=") == 1


def test_index_papers_pipeline(tmp_path: Path, monkeypatch):
    from litgraph.cli import helpers
    from litgraph.cli.config_manager import ResolvedContext

    ctx = ResolvedContext(
        project_root=tmp_path,
        litgraph_dir=tmp_path / ".litgraph",
        config={"papers_dir": "papers", "llm_provider": "openai", "llm_model": "gpt-4o-mini"},
        db_path=tmp_path / ".litgraph" / "db" / "literature.kuzu",
        cache_dir=tmp_path / ".litgraph" / "cache",
    )
    monkeypatch.setattr(
        helpers,
        "scan_papers",
        lambda *a, **k: {"total": 1, "changed": 1, "unchanged": 0, "removed": 0},
    )
    monkeypatch.setattr(
        helpers,
        "parse_papers",
        lambda *a, **k: {"parsed": 1, "bib_files": 0, "errors": []},
    )
    monkeypatch.setattr(
        helpers,
        "extract_papers",
        lambda *a, **k: {"extracted": 1, "skipped": 0, "provider": "openai"},
    )
    monkeypatch.setattr(
        helpers,
        "build_paper_graph",
        lambda *a, **k: {"papers_indexed": 1, "nodes": 3, "edges": 2},
    )

    result = helpers.index_papers(ctx, skip_confirm=True)
    assert result["scan"]["total"] == 1
    assert result["parse"]["parsed"] == 1
    assert result["extract"]["extracted"] == 1
    assert result["build"]["papers_indexed"] == 1


def test_index_papers_no_extract(tmp_path: Path, monkeypatch):
    from litgraph.cli import helpers
    from litgraph.cli.config_manager import ResolvedContext

    ctx = ResolvedContext(
        project_root=tmp_path,
        litgraph_dir=tmp_path / ".litgraph",
        config={"papers_dir": "papers"},
        db_path=tmp_path / ".litgraph" / "db" / "literature.kuzu",
        cache_dir=tmp_path / ".litgraph" / "cache",
    )
    monkeypatch.setattr(helpers, "scan_papers", lambda *a, **k: {"total": 0, "changed": 0})
    monkeypatch.setattr(helpers, "parse_papers", lambda *a, **k: {"parsed": 0, "bib_files": 0})
    extract_mock = MagicMock()
    monkeypatch.setattr(helpers, "extract_papers", extract_mock)
    monkeypatch.setattr(helpers, "build_paper_graph", lambda *a, **k: {"papers_indexed": 0})

    result = helpers.index_papers(ctx, no_extract=True)
    extract_mock.assert_not_called()
    assert result["extract"].get("skipped_step") is True
