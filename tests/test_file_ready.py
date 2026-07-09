"""Tests for file readiness helpers."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from litgraph.utils.file_ready import wait_for_file_ready


def test_wait_for_file_ready_accepts_stable_nonempty_file(tmp_path):
    target = tmp_path / "paper.pdf"
    target.write_bytes(b"%PDF-1.4")

    assert wait_for_file_ready(target, poll_interval=0.05, stable_checks=2) is True


def test_wait_for_file_ready_waits_for_growing_file(tmp_path):
    target = tmp_path / "paper.pdf"
    target.write_bytes(b"")

    def grow_file() -> None:
        time.sleep(0.15)
        target.write_bytes(b"%PDF-1.4")

    threading.Thread(target=grow_file, daemon=True).start()

    assert wait_for_file_ready(
        target,
        poll_interval=0.05,
        stable_checks=2,
        max_wait=2.0,
    ) is True


def test_wait_for_file_ready_times_out_on_empty_file(tmp_path):
    target = tmp_path / "empty.pdf"
    target.write_bytes(b"")

    assert wait_for_file_ready(
        target,
        poll_interval=0.05,
        stable_checks=2,
        max_wait=0.3,
    ) is False
