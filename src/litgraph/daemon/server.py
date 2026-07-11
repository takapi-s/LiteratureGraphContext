"""FastAPI server for the LiteratureGraph background daemon."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from litgraph.daemon.runtime import DaemonRuntime
from litgraph.daemon.secrets import apply_secrets_update, secrets_status
from litgraph.daemon.state import (
    common_css_path,
    home_page_path,
    list_pending_extract,
    render_daemon_html,
    settings_page_path,
    static_dir,
)
from litgraph.mcp.http_mount import mcp_http_lifespan, register_mcp_http_route
from litgraph.viz.server import register_viz_routes


def create_daemon_app(runtime: DaemonRuntime) -> Any:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    bind_host = runtime.settings.http_host
    bind_port = runtime.settings.http_port
    transport_holder: list[Any] = []

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.status.pending_extract = list_pending_extract(runtime.ctx)
        async with mcp_http_lifespan(runtime.mcp_bridge) as transport:
            transport_holder[:] = [transport]
            runtime.scheduler.start()
            runtime.start_folder_watch()
            try:
                yield
            finally:
                runtime.shutdown()

    app = FastAPI(title="LiteratureGraph Daemon", lifespan=lifespan)
    register_mcp_http_route(app, transport_holder)

    @app.get("/ui/common.css")
    async def common_css() -> FileResponse:
        css = common_css_path()
        if not css.is_file():
            raise HTTPException(status_code=404, detail="common.css missing")
        return FileResponse(css, media_type="text/css; charset=utf-8")

    # Remaining static assets (if any); explicit CSS route above wins first.
    app.mount("/ui", StaticFiles(directory=static_dir()), name="daemon_ui")

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/home", status_code=307)

    @app.get("/home")
    async def home_page() -> HTMLResponse:
        page = home_page_path()
        if not page.is_file():
            raise HTTPException(status_code=404, detail="Home page missing")
        return HTMLResponse(render_daemon_html(page))

    @app.get("/settings")
    async def settings_page() -> HTMLResponse:
        page = settings_page_path()
        if not page.is_file():
            raise HTTPException(status_code=404, detail="Settings page missing")
        return HTMLResponse(render_daemon_html(page))

    @app.get("/api/daemon/settings")
    async def get_settings() -> Dict[str, Any]:
        return runtime.settings.to_dict()

    @app.put("/api/daemon/settings")
    async def put_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "http_host",
            "http_port",
            "zotero_enabled",
            "zotero_interval_sec",
            "extract_mode",
            "watch_folder",
            "watch_auto_extract",
        }
        patch = {k: v for k, v in payload.items() if k in allowed}
        settings = runtime.update_settings(patch)
        return settings.to_dict()

    @app.get("/api/daemon/secrets")
    async def get_secrets() -> Dict[str, Any]:
        return secrets_status(runtime.ctx)

    @app.put("/api/daemon/secrets")
    async def put_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return apply_secrets_update(runtime.ctx, payload or {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/daemon/status")
    async def get_status() -> Dict[str, Any]:
        runtime.status.pending_extract = list_pending_extract(runtime.ctx)
        payload = runtime.status.to_dict()
        payload["project_root"] = str(runtime.ctx.project_root)
        payload["workspace_id"] = runtime.ctx.workspace_id
        payload["mcp_url"] = f"http://{bind_host}:{bind_port}/mcp"
        payload["home_url"] = f"http://{bind_host}:{bind_port}/home"
        payload["settings_url"] = f"http://{bind_host}:{bind_port}/settings"
        payload["viz_url"] = f"http://{bind_host}:{bind_port}/viz"
        return payload

    @app.post("/api/daemon/sync")
    async def trigger_sync() -> Dict[str, Any]:
        if runtime.status.syncing:
            raise HTTPException(status_code=503, detail="Sync already in progress")
        try:
            return runtime.scheduler.trigger_sync()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/daemon/extract")
    async def trigger_extract(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if runtime.status.syncing:
            raise HTTPException(status_code=503, detail="Sync already in progress")
        paper_ids = None
        if payload and isinstance(payload.get("paper_ids"), list):
            paper_ids = [str(pid) for pid in payload["paper_ids"]]
        try:
            return runtime.scheduler.trigger_extract(paper_ids)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.exception_handler(OSError)
    async def bind_error_handler(_request, exc: OSError):
        if getattr(exc, "errno", None) in (98, 10048):
            return JSONResponse(
                status_code=409,
                content={
                    "error": "daemon_already_running",
                    "hint": f"Another process is already bound to {bind_host}:{bind_port}",
                },
            )
        raise exc

    # SPA catch-all must be registered last so /home, /settings, /api/* win.
    register_viz_routes(app, runtime.ctx)
    return app


def run_daemon_server(
    runtime: DaemonRuntime,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    import uvicorn

    bind_host = host or runtime.settings.http_host
    bind_port = port or runtime.settings.http_port
    if host is not None or port is not None:
        runtime.settings.http_host = bind_host
        runtime.settings.http_port = bind_port
    app = create_daemon_app(runtime)
    uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")
