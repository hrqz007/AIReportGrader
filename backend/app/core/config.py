from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "实验智评 V2"
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def _runtime_path(env_name: str, default: Path) -> Path:
    configured = os.getenv(env_name)
    if configured:
        return Path(configured).expanduser().resolve()
    return default


DATA_DIR = _runtime_path("AIGRADER_DATA_DIR", BACKEND_ROOT / "data")
UPLOADS_DIR = _runtime_path("AIGRADER_UPLOADS_DIR", BACKEND_ROOT / "uploads")
EXPORTS_DIR = _runtime_path("AIGRADER_EXPORTS_DIR", BACKEND_ROOT / "exports")


def get_db_path() -> Path:
    configured = os.getenv("AIGRADER_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DATA_DIR / "app.db"


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
