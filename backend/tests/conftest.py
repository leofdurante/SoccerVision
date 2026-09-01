"""Test environment setup.

Runs at collection time (module-level code, not a fixture) so it takes
effect BEFORE any test module does `from app.core.config import
get_settings` or `from app.main import app` — those establish the
SQLAlchemy engine and settings singleton on first import, so the
environment must be in place first. Real env vars (os.environ) take
precedence over `.env` file values in pydantic-settings, so this
reliably isolates tests from the developer's local `.env`/dev database.
"""

from __future__ import annotations

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="soccervision_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp_dir}/uploads"
os.environ["OUTPUT_DIR"] = f"{_tmp_dir}/processed"
os.environ["AI_API_KEY"] = ""  # force the deterministic rule-based insight fallback in tests
os.environ["MODEL_PATH"] = "yolov8n.pt"  # keep the integration test on the small weights
os.environ["CONFIDENCE_THRESHOLD"] = "0.25"
os.environ["PROCESSING_FPS"] = "5"
