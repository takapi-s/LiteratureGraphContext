"""Quickstart smoke test — mirrors docs/TUTORIAL.md §§1–5 (no LLM / API keys)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PDF = REPO_ROOT / "examples" / "papers" / "mobility_gnn_2024.pdf"
EXAMPLE_BIB = REPO_ROOT / "examples" / "papers" / "mobility_gnn_2024.bib"


def _litgraph_cmd() -> list[str]:
    """Prefer the installed console script; fall back to ``python -m litgraph``."""
    return [sys.executable, "-m", "litgraph"]


def _run(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LITGRAPH_PROJECT_ROOT"] = str(cwd)
    # Ensure src layout works when not installed editable in some CI layouts.
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    cmd = _litgraph_cmd() + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


@pytest.mark.skipif(not EXAMPLE_PDF.is_file(), reason="example PDF missing from checkout")
def test_tutorial_quickstart_cli_sequence(tmp_path: Path) -> None:
    """Run the non-interactive Tutorial path: version → init → doctor → index → setup → test-mcp."""
    papers = tmp_path / "papers"
    papers.mkdir()
    shutil.copy(EXAMPLE_PDF, papers / EXAMPLE_PDF.name)
    shutil.copy(EXAMPLE_BIB, papers / EXAMPLE_BIB.name)

    ver = _run(tmp_path, "version")
    assert ver.stdout.strip() or ver.stderr.strip()

    _run(tmp_path, "init", "--papers-dir", "./papers")
    assert (tmp_path / ".litgraph" / "config.yaml").is_file()

    doctor = _run(tmp_path, "doctor")
    doctor_text = doctor.stdout + doctor.stderr
    assert "Active project" in doctor_text
    assert "PDF" in doctor_text

    index = _run(tmp_path, "index", "-y", "--no-extract")
    index_text = index.stdout + index.stderr
    assert "parsed" in index_text.lower() or "Indexed" in index_text

    setup = _run(tmp_path, "setup", "--papers-dir", "./papers", "--yes")
    mcp_json = tmp_path / "mcp.json"
    assert mcp_json.is_file(), setup.stdout + setup.stderr
    mcp = json.loads(mcp_json.read_text(encoding="utf-8"))
    assert "mcpServers" in mcp
    assert any("literature-graph" in name for name in mcp["mcpServers"])

    smoke = _run(tmp_path, "test-mcp", "--path", str(tmp_path))
    smoke_text = (smoke.stdout + smoke.stderr).replace("\r", "")
    assert "Passed:" in smoke_text
    assert "Failed: 0" in smoke_text


def test_index_no_extract_parses_after_scan(tmp_path: Path, monkeypatch) -> None:
    """Regression: ``litgraph index`` must not lose changed files to a second scan."""
    from litgraph.cli.config_manager import init_project, resolve_context
    from litgraph.cli.helpers import index_papers

    monkeypatch.delenv("LITGRAPH_PROJECT_ROOT", raising=False)
    init_project(tmp_path, papers_dir="papers")
    papers = tmp_path / "papers"
    papers.mkdir(exist_ok=True)
    dest = papers / EXAMPLE_PDF.name
    shutil.copy(EXAMPLE_PDF, dest)
    assert dest.is_file() and dest.stat().st_size > 0

    ctx = resolve_context(tmp_path)
    assert ctx.project_root == tmp_path.resolve()
    assert ctx.papers_dir.resolve() == papers.resolve()

    result = index_papers(ctx, no_extract=True, skip_confirm=True)
    assert result["scan"]["total"] >= 1, result["scan"]
    assert result["scan"]["changed"] >= 1, result["scan"]
    assert result["parse"]["parsed"] >= 1, result["parse"]
    assert result["build"].get("papers_indexed", 0) >= 1, result["build"]
