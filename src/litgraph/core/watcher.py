"""Live file watching for the papers directory."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from litgraph.cli.config_manager import ResolvedContext
from litgraph.scanner.file_scanner import SUPPORTED_EXTENSIONS
from litgraph.scanner.ignore import build_ignore_spec, should_ignore

POLLING_ENV_VAR = "LITGRAPH_WATCH_POLLING"
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


def should_use_polling_observer(use_polling: Optional[bool] = None) -> bool:
    if use_polling is not None:
        return use_polling
    return os.getenv(POLLING_ENV_VAR, "").strip().lower() in TRUE_ENV_VALUES


@dataclass
class WatchOptions:
    auto_extract: bool = False
    auto_build: bool = True
    sync_on_start: bool = False
    skip_confirm: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    enrich_s2: bool = False
    on_result: Optional[Callable[[dict], None]] = None


class PapersEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        ctx: ResolvedContext,
        options: WatchOptions,
        watch_root: Path,
        ignore_spec,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.options = options
        self.watch_root = watch_root.resolve()
        self.ignore_spec = ignore_spec
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._pending_changed: Set[Path] = set()
        self._pending_deleted: Set[Path] = set()
        self._worker: Optional[threading.Thread] = None
        self._shutdown = False

    def _is_supported(self, path: str | Path) -> bool:
        path_obj = Path(path)
        return path_obj.suffix.lower() in SUPPORTED_EXTENSIONS

    def _should_process(self, path: str | Path) -> bool:
        path_obj = Path(path)
        if not self._is_supported(path_obj):
            return False
        return not should_ignore(path_obj, self.watch_root, self.ignore_spec)

    def _queue(self, path: str | Path, deleted: bool) -> None:
        resolved = Path(path).resolve()
        with self._wake:
            if deleted:
                self._pending_deleted.add(resolved)
                self._pending_changed.discard(resolved)
            else:
                if resolved not in self._pending_deleted:
                    self._pending_changed.add(resolved)
            self._wake.notify()

    def start_worker(self) -> None:
        with self._wake:
            if self._worker and self._worker.is_alive():
                return
            self._shutdown = False
            self._worker = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="litgraph-watch-worker",
            )
            self._worker.start()

    def _worker_loop(self) -> None:
        from litgraph.cli.helpers import process_watch_changes

        while True:
            with self._wake:
                while (
                    not self._shutdown
                    and not self._pending_changed
                    and not self._pending_deleted
                ):
                    self._wake.wait()
                if self._shutdown:
                    return
                changed = sorted(self._pending_changed)
                deleted = sorted(self._pending_deleted)
                self._pending_changed.clear()
                self._pending_deleted.clear()

            if not changed and not deleted:
                continue

            try:
                result = process_watch_changes(
                    self.ctx,
                    changed_paths=changed,
                    deleted_paths=deleted,
                    auto_extract=self.options.auto_extract,
                    auto_build=self.options.auto_build,
                    skip_confirm=self.options.skip_confirm,
                    provider=self.options.provider,
                    model=self.options.model,
                    enrich_s2=self.options.enrich_s2,
                )
            except Exception:
                from litgraph.utils.logging import get_logger

                get_logger(__name__).exception(
                    "Failed to process watch changes for %d changed, %d deleted file(s)",
                    len(changed),
                    len(deleted),
                )
                continue
            if self.options.on_result:
                self.options.on_result(result)

    def stop_worker(self) -> None:
        with self._wake:
            self._shutdown = True
            self._wake.notify_all()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    def on_created(self, event) -> None:
        if not event.is_directory and self._should_process(event.src_path):
            self._queue(event.src_path, deleted=False)

    def on_modified(self, event) -> None:
        if not event.is_directory and self._should_process(event.src_path):
            self._queue(event.src_path, deleted=False)

    def on_deleted(self, event) -> None:
        if not event.is_directory and self._is_supported(event.src_path):
            self._queue(event.src_path, deleted=True)

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            self._queue(event.src_path, deleted=True)
        if self._should_process(event.dest_path):
            self._queue(event.dest_path, deleted=False)


class PapersWatcher:
    def __init__(
        self,
        ctx: ResolvedContext,
        options: Optional[WatchOptions] = None,
        use_polling: Optional[bool] = None,
    ) -> None:
        self.ctx = ctx
        self.options = options or WatchOptions()
        self.watch_root = ctx.papers_dir.resolve()
        observer_cls = PollingObserver if should_use_polling_observer(use_polling) else Observer
        self.observer = observer_cls()
        self.ignore_spec, _ = build_ignore_spec(self.watch_root)
        self.handler = PapersEventHandler(ctx, self.options, self.watch_root, self.ignore_spec)

    def sync_on_start(self) -> dict:
        from litgraph.cli.helpers import sync_papers_directory

        return sync_papers_directory(
            self.ctx,
            auto_extract=self.options.auto_extract,
            auto_build=self.options.auto_build,
            skip_confirm=self.options.skip_confirm,
            provider=self.options.provider,
            model=self.options.model,
            enrich_s2=self.options.enrich_s2,
        )

    def start(self, block: bool = True) -> None:
        if not self.watch_root.exists():
            self.watch_root.mkdir(parents=True, exist_ok=True)

        if self.options.sync_on_start:
            result = self.sync_on_start()
            if self.options.on_result:
                self.options.on_result(result)

        self.handler.start_worker()
        self.observer.schedule(self.handler, str(self.watch_root), recursive=True)
        self.observer.start()

        if not block:
            return

        try:
            while self.observer.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self.handler.stop_worker()
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)
