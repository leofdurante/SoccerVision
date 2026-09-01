"""YOLO inference device selection.

Ultralytics defaults to CPU unless `device` is passed, even when a GPU is
present. CUDA + fp16 is an order of magnitude faster on a 1080p clip;
we detect once per process and reuse the kwargs on every `predict`/`track`.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("soccervision.cv.runtime")

_kwargs: dict | None = None


def reset_yolo_runtime_cache() -> None:
    """Test helper: forget the cached device choice."""
    global _kwargs
    _kwargs = None


def yolo_runtime_kwargs() -> dict:
    """Arguments to forward to Ultralytics `predict` / `track`.

    `half` is only set on CUDA — it errors or silently degrades on CPU.
    """
    global _kwargs
    if _kwargs is not None:
        return _kwargs

    device: str | int = "cpu"
    half = False
    try:
        import torch

        if torch.cuda.is_available():
            device = 0
            half = True
    except Exception:
        logger.debug("torch unavailable; YOLO stays on CPU", exc_info=True)

    _kwargs = {"device": device, "half": half}
    logger.info("YOLO inference device=%s half=%s", device, half)
    return _kwargs
