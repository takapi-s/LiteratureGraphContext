import json
from pathlib import Path

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


def test_run_setup_wizard_interactive_flow(tmp_path: Path, monkeypatch):
    """Wizard initializes project, saves LLM config, and writes .cursor/mcp.json."""
    import yaml

    monkeypatch.setattr(
        setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"])
    )
    # Isolate global env file so the API key step sees "already set".
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    answers = iter([
        "./papers",     # papers directory
        "openai",       # provider
        "gpt-4o-mini",  # model
        "cursor",       # client
    ])
    monkeypatch.setattr(
        setup_wizard.Prompt, "ask", staticmethod(lambda *a, **k: next(answers))
    )
    monkeypatch.setattr(
        setup_wizard.Confirm, "ask", staticmethod(lambda *a, **k: True)
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
