"""Local graph visualization server (FastAPI + literature graph UI)."""

from __future__ import annotations

import json
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Optional

from litgraph.cli.config_manager import ResolvedContext
from litgraph.graph.graph_builder import _store_for
from litgraph.viz.api_adapter import to_playground_graph

_STATIC_BUNDLED = Path(__file__).parent / "dist"
_STATIC_DEV = Path(__file__).resolve().parents[3] / "website" / "dist"


def _resolve_static_dir() -> Path:
    if _STATIC_BUNDLED.is_dir() and (_STATIC_BUNDLED / "index.html").is_file():
        return _STATIC_BUNDLED
    if _STATIC_DEV.is_dir() and (_STATIC_DEV / "index.html").is_file():
        return _STATIC_DEV
    raise FileNotFoundError(
        "Visualization bundle not found. Run: cd website && npm ci && npm run build "
        "then copy website/dist to src/litgraph/viz/dist (or run scripts/build_viz.ps1)."
    )


def _is_kuzu_fallback_error(exc: BaseException) -> bool:
    msg = str(exc)
    return (
        "Could not set lock" in msg
        or "IO exception" in msg
        or "Cannot read from file" in msg
    )


def _load_graph_json_snapshot(ctx: ResolvedContext) -> dict[str, Any]:
    graph_path = ctx.cache_dir / "graph.json"
    if not graph_path.is_file():
        raise FileNotFoundError(
            f"Kuzu database is unavailable and no graph snapshot was found at {graph_path}"
        )
    return json.loads(graph_path.read_text(encoding="utf-8"))


def _graph_payload(ctx: ResolvedContext) -> dict[str, Any]:
    try:
        store = _store_for(ctx, read_only=True)
        try:
            raw = store.export_graph_json()
        finally:
            store.close()
    except Exception as exc:
        if not _is_kuzu_fallback_error(exc):
            raise
        raw = _load_graph_json_snapshot(ctx)
    return to_playground_graph(raw)


def register_viz_routes(app: Any, ctx: ResolvedContext) -> None:
    """Mount ``/api/graph``, ``/assets``, ``/viz``, and SPA routes on ``app``.

    The bundled SPA uses absolute ``/assets`` and ``/api/graph`` paths, so those
    stay at the server root. ``/viz`` redirects to ``/explore``.
    """
    from fastapi import HTTPException
    from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    try:
        static_dir = _resolve_static_dir()
    except FileNotFoundError:
        @app.get("/viz")
        async def viz_missing() -> HTMLResponse:
            return HTMLResponse(
                "Visualization bundle missing. Run scripts/build_viz.ps1",
                status_code=503,
            )

        return

    @app.get("/api/graph")
    async def get_graph() -> dict[str, Any]:
        try:
            return _graph_payload(ctx)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="viz_assets")

    @app.get("/viz")
    @app.get("/viz/")
    async def viz_entry() -> RedirectResponse:
        return RedirectResponse(url="/explore", status_code=307)

    @app.get("/explore")
    async def explore_spa() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse | HTMLResponse:
        # Daemon hub routes must not be swallowed by the SPA catch-all.
        first = full_path.split("/", 1)[0]
        if first in {
            "home",
            "settings",
            "mcp",
            "api",
            "ui",
            "docs",
            "openapi.json",
            "redoc",
        }:
            raise HTTPException(status_code=404, detail="Not found")
        if full_path and (static_dir / full_path).is_file():
            return FileResponse(static_dir / full_path)
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse("Visualization bundle missing index.html", status_code=404)


def run_viz_server(
    ctx: ResolvedContext,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    register_viz_routes(app, ctx)

    backend = f"http://{host}:{port}"
    params = urllib.parse.urlencode({"backend": backend})
    url = f"{backend}/explore?{params}"

    if open_browser:
        import threading
        import time

        def _open() -> None:
            time.sleep(1.0)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
