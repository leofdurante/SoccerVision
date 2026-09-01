"""Structured logging setup.

Never log secrets (API keys, tokens, credentials) — only IDs, stages,
durations, and counts.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. reloader re-import) — avoid duplicate handlers.
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third-party loggers.
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
