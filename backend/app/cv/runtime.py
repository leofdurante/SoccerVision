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

    On CUDA we request FP16 via `quantize=16` (the replacement for the
    deprecated `half=True` flag). CPU stays on default FP32.
    """
    global _kwargs
    if _kwargs is not None:
        return _kwargs

    kwargs: dict = {"device": "cpu"}
    try:
        import torch

        if torch.cuda.is_available():
            kwargs = {"device": 0, "quantize": 16}
    except Exception:
        logger.debug("torch unavailable; YOLO stays on CPU", exc_info=True)

    _kwargs = kwargs
    logger.info("YOLO inference %s", kwargs)
    return _kwargs
