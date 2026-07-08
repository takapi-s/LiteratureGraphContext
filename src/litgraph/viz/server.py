"""Local graph visualization server (FastAPI + literature graph UI)."""

from __future__ import annotations

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


def _graph_payload(ctx: ResolvedContext) -> dict[str, Any]:
    store = _store_for(ctx, read_only=True)
    try:
        return to_playground_graph(store.export_graph_json())
    finally:
        store.close()


def run_viz_server(
    ctx: ResolvedContext,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    static_dir = _resolve_static_dir()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/graph")
    async def get_graph() -> dict[str, Any]:
        try:
            return _graph_payload(ctx)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse | HTMLResponse:
        if full_path and (static_dir / full_path).is_file():
            return FileResponse(static_dir / full_path)
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse("Visualization bundle missing index.html", status_code=404)

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
