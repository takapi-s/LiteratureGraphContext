"""Daemon runtime wiring MCP service, scheduler, and status."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from litgraph.cli.config_manager import ResolvedContext, load_env
from litgraph.daemon.scheduler import DaemonScheduler, IngestQueue
from litgraph.daemon.state import DaemonSettings, DaemonStatus, load_daemon_settings, save_daemon_settings
from litgraph.mcp.tool_service import MCPToolService


class DaemonMCPBridge:
    """Expose daemon-guarded MCP tool dispatch to the HTTP MCP transport."""

    def __init__(self, runtime: "DaemonRuntime") -> None:
        self._runtime = runtime

    @property
    def tools(self):
        return self._runtime.service.tools

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._runtime.handle_tool_call(name, args)

    def format_tool_result(self, name: str, result: Dict[str, Any]) -> str:
        return self._runtime.service.format_tool_result(name, result)

    def close(self) -> None:
        return None


class DaemonRuntime:
    def __init__(self, ctx: ResolvedContext) -> None:
        load_env()
        self.ctx = ctx
        self.settings = load_daemon_settings(ctx)
        self.status = DaemonStatus()
        self.service = MCPToolService(ctx.project_root, workspace_id=ctx.workspace_id)
        self.mcp_bridge = DaemonMCPBridge(self)
        self._syncing = False
        self._folder_watcher = None
        self.queue = IngestQueue(on_syncing_change=self.set_syncing)
        self.scheduler = DaemonScheduler(
            ctx,
            settings=self.settings,
            status=self.status,
            queue=self.queue,
            get_settings=lambda: self.settings,
            on_after_write=self.reload_finder,
            on_status_change=self._noop,
        )

    def set_status_listener(self, listener: Callable[[], None]) -> None:
        self.scheduler._on_status_change = listener or self._noop

    @staticmethod
    def _noop() -> None:
        return None

    def set_syncing(self, syncing: bool) -> None:
        self._syncing = syncing
        self.status.syncing = syncing

    def reload_finder(self) -> None:
        self.service.reload_finder()
        from litgraph.daemon.state import list_pending_extract

        self.status.pending_extract = list_pending_extract(self.ctx)

    def update_settings(self, patch: Dict[str, Any]) -> DaemonSettings:
        current = self.settings.to_dict()
        current.update(patch)
        self.settings = DaemonSettings.from_dict(current)
        save_daemon_settings(self.ctx, self.settings)
        self.restart_folder_watch()
        return self.settings

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if self._syncing:
            return {
                "error": "syncing",
                "hint": (
                    "LiteratureGraph is ingesting or rebuilding the graph. "
                    "Retry in a moment or check the daemon status page."
                ),
            }
        return self.service.handle_tool_call(name, args)

    def start_folder_watch(self) -> None:
        self.stop_folder_watch()
        if not self.settings.watch_folder:
            return
        from litgraph.core.watcher import PapersWatcher, WatchOptions

        auto_extract = self.settings.watch_auto_extract or self.settings.extract_mode == "auto"

        def write_guard(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
            return self.queue.run("folder-watch", fn)

        options = WatchOptions(
            auto_extract=auto_extract,
            auto_build=True,
            skip_confirm=True,
            write_guard=write_guard,
            on_result=lambda _result: self.reload_finder(),
        )
        watcher = PapersWatcher(self.ctx, options=options)
        watcher.start(block=False)
        self._folder_watcher = watcher

    def stop_folder_watch(self) -> None:
        if self._folder_watcher is not None:
            self._folder_watcher.stop()
            self._folder_watcher = None

    def restart_folder_watch(self) -> None:
        self.start_folder_watch()

    def shutdown(self) -> None:
        self.scheduler.stop()
        self.stop_folder_watch()
        self.service.close()
