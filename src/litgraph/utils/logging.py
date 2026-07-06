"""Logging utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from litgraph.cli.config_manager import GLOBAL_CONFIG_DIR, ensure_global_config_dir


def setup_logging(level: int = logging.INFO) -> None:
    ensure_global_config_dir()
    log_path = GLOBAL_CONFIG_DIR / "logs" / "litgraph.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
