"""Настройка логирования."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import LOG_DIR


def setup_logging(level: int = logging.INFO) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "app.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # Файл
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(level)
    root.addHandler(fh)

    # Консоль
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)
    root.addHandler(ch)

    logging.getLogger("app").info("Logging initialized → %s", log_file)