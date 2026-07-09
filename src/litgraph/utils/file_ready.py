"""Wait until filesystem writes finish before parsing."""

from __future__ import annotations

import time
from pathlib import Path


def wait_for_file_ready(
    path: Path,
    *,
    min_size: int = 1,
    stable_checks: int = 2,
    poll_interval: float = 0.25,
    max_wait: float = 30.0,
) -> bool:
    """Return True when *path* exists, is at least *min_size* bytes, and size is stable."""
    deadline = time.monotonic() + max_wait
    last_size: int | None = None
    stable = 0
    while time.monotonic() < deadline:
        if not path.exists():
            time.sleep(poll_interval)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            time.sleep(poll_interval)
            continue
        if size < min_size:
            stable = 0
            last_size = size
            time.sleep(poll_interval)
            continue
        if last_size == size:
            stable += 1
            if stable >= stable_checks:
                return True
        else:
            stable = 0
        last_size = size
        time.sleep(poll_interval)
    return False
