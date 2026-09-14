from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR: Path = Path.home() / ".config" / "whisper-code"
LOG_FILE: Path = LOG_DIR / "whisper.log"


def setup_logger(level: str | None = None) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger: logging.Logger = logging.getLogger("whisper")
    logger.setLevel(logging.DEBUG)

    fmt: logging.Formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh: logging.FileHandler = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    if level is not None:
        sh.setLevel(getattr(logging, level.upper(), logging.INFO))
    elif sys.stdout.isatty():
        sh.setLevel(logging.DEBUG)
    else:
        sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("whisper")
