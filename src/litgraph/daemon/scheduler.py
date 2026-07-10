"""Daemon scheduler, ingest queue, and Zotero polling loop."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

from litgraph.cli.config_manager import ResolvedContext
from litgraph.daemon.state import DaemonSettings, DaemonStatus, list_pending_extract, utc_now_iso


class IngestQueue:
    """Serialize write operations (sync, extract, folder watch batches)."""

    def __init__(self, on_syncing_change: Callable[[bool], None]) -> None:
        self._lock = threading.Lock()
        self._on_syncing_change = on_syncing_change

    def run(self, label: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            self._on_syncing_change(True)
            try:
                return fn()
            finally:
                self._on_syncing_change(False)


class DaemonScheduler:
    def __init__(
        self,
        ctx: ResolvedContext,
        *,
        settings: DaemonSettings,
        status: DaemonStatus,
        queue: IngestQueue,
        get_settings: Callable[[], DaemonSettings],
        on_after_write: Callable[[], None],
        on_status_change: Callable[[], None],
    ) -> None:
        self.ctx = ctx
        self.status = status
        self.queue = queue
        self._get_settings = get_settings
        self._on_after_write = on_after_write
        self._on_status_change = on_status_change
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_zotero_run = 0.0
        self._settings = settings

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="litgraph-daemon-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def trigger_sync(self) -> Dict[str, Any]:
        return self.queue.run("zotero-sync", self._run_zotero_sync)

    def trigger_extract(self, paper_ids: Optional[list[str]] = None) -> Dict[str, Any]:
        return self.queue.run("extract", lambda: self._run_extract(paper_ids))

    def _loop(self) -> None:
        self.status.running = True
        self._on_status_change()
        while not self._stop.is_set():
            settings = self._get_settings()
            if settings.zotero_enabled:
                interval = max(60, settings.zotero_interval_sec)
                if time.time() - self._last_zotero_run >= interval:
                    try:
                        self.queue.run("zotero-sync", self._run_zotero_sync)
                    except Exception as exc:
                        self.status.last_sync_error = str(exc)
                        self._on_status_change()
                    self._last_zotero_run = time.time()
            self._stop.wait(1.0)
        self.status.running = False
        self._on_status_change()

    def _run_zotero_sync(self) -> Dict[str, Any]:
        from litgraph.integrations.zotero import sync_zotero_with_pdfs

        settings = self._get_settings()
        extract = settings.extract_mode == "auto"
        result = sync_zotero_with_pdfs(
            self.ctx,
            changed_only=True,
            extract=extract,
            build=True,
            show_progress=False,
        )
        self.status.last_sync_at = utc_now_iso()
        self.status.last_sync_result = result
        self.status.last_sync_error = None
        if result.get("pdf_errors"):
            self.status.last_sync_error = "; ".join(result["pdf_errors"][:3])
        self._refresh_pending()
        self._on_after_write()
        self._on_status_change()
        return result

    def _run_extract(self, paper_ids: Optional[list[str]]) -> Dict[str, Any]:
        from litgraph.cli.helpers import build_paper_graph, extract_paper_ids

        targets = paper_ids or list_pending_extract(self.ctx)
        if not targets:
            result = {"extracted": 0, "skipped": 0, "message": "No pending papers"}
            self.status.last_extract_at = utc_now_iso()
            self.status.last_extract_result = result
            self._refresh_pending()
            self._on_status_change()
            return result

        extract_result = extract_paper_ids(
            self.ctx,
            targets,
            skip_confirm=True,
            show_progress=False,
        )
        build_result = build_paper_graph(self.ctx)
        result = {**extract_result, **build_result}
        self.status.last_extract_at = utc_now_iso()
        self.status.last_extract_result = result
        self._refresh_pending()
        self._on_after_write()
        self._on_status_change()
        return result

    def _refresh_pending(self) -> None:
        self.status.pending_extract = list_pending_extract(self.ctx)
