import json
from pathlib import Path

from litgraph.mcp import setup_wizard


def test_build_mcp_client_config_uses_cwd_not_bash(tmp_path: Path):
    config = setup_wizard.build_mcp_client_config(tmp_path)

    server = config["mcpServers"]["literature-graph-context"]
    assert server["command"] != "bash"
    assert server["args"] == ["serve-mcp"] or server["args"][-2:] == ["litgraph", "serve-mcp"]
    assert server["cwd"] == str(tmp_path.resolve())
    assert "serve-mcp" in server["args"]


def test_configure_mcp_client_writes_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(setup_wizard, "resolve_litgraph_mcp_command", lambda: ("/usr/bin/litgraph", ["serve-mcp"]))

    out = setup_wizard.configure_mcp_client(tmp_path)
    assert out == tmp_path / "mcp.json"

    data = json.loads(out.read_text(encoding="utf-8"))
    server = data["mcpServers"]["literature-graph-context"]
    assert server["command"] == "/usr/bin/litgraph"
    assert server["args"] == ["serve-mcp"]
    assert server["cwd"] == str(tmp_path.resolve())


def test_resolve_litgraph_mcp_command_falls_back_to_python_module(monkeypatch):
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda _name: None)
    monkeypatch.setattr(setup_wizard.sys, "executable", "/usr/bin/python3")

    command, args = setup_wizard.resolve_litgraph_mcp_command()
    assert command == "/usr/bin/python3"
    assert args == ["-m", "litgraph", "serve-mcp"]
