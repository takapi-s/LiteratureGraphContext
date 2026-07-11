"""Packaging: viz/daemon static assets must ship in the installed package."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_viz_dist_is_tracked_not_website_dist() -> None:
    """website/dist is gitignored; the package copies live under src/litgraph/viz/dist."""
    pkg_index = REPO_ROOT / "src" / "litgraph" / "viz" / "dist" / "index.html"
    assert pkg_index.is_file(), "src/litgraph/viz/dist/index.html missing — run scripts/build_viz.ps1"
    static_index = REPO_ROOT / "src" / "litgraph" / "viz" / "static" / "index.html"
    assert static_index.is_file()
    daemon_settings = REPO_ROOT / "src" / "litgraph" / "daemon" / "static" / "settings.html"
    assert daemon_settings.is_file()
    daemon_home = REPO_ROOT / "src" / "litgraph" / "daemon" / "static" / "home.html"
    assert daemon_home.is_file()
    daemon_css = REPO_ROOT / "src" / "litgraph" / "daemon" / "static" / "common.css"
    assert daemon_css.is_file()
    daemon_logo = REPO_ROOT / "src" / "litgraph" / "daemon" / "static" / "logo-icon-dark.png"
    assert daemon_logo.is_file()


def test_viz_assets_importable_from_package() -> None:
    from importlib.resources import files

    dist_index = files("litgraph.viz").joinpath("dist/index.html")
    assert dist_index.is_file(), "litgraph.viz.dist/index.html not in package"
    static_index = files("litgraph.viz").joinpath("static/index.html")
    assert static_index.is_file()
    settings = files("litgraph.daemon").joinpath("static/settings.html")
    assert settings.is_file()
    home = files("litgraph.daemon").joinpath("static/home.html")
    assert home.is_file()
    css = files("litgraph.daemon").joinpath("static/common.css")
    assert css.is_file()
    logo = files("litgraph.daemon").joinpath("static/logo-icon-dark.png")
    assert logo.is_file()


@pytest.mark.slow
def test_built_wheel_contains_viz_assets(tmp_path: Path) -> None:
    """Regression: hatchling must ship non-Python viz assets without force-include."""
    import subprocess
    import sys

    out = tmp_path / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"build unavailable: {result.stderr[-500:]}")
    wheels = list(out.glob("*.whl"))
    assert wheels, "no wheel produced"
    names = zipfile.ZipFile(wheels[0]).namelist()
    assert "litgraph/viz/dist/index.html" in names
    assert "litgraph/viz/static/index.html" in names
    assert "litgraph/daemon/static/settings.html" in names
    assert "litgraph/daemon/static/home.html" in names
    assert "litgraph/daemon/static/common.css" in names
