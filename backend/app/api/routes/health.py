from __future__ import annotations

from fastapi import APIRouter

from app.core.config import APP_NAME, get_db_path
from app.db.database import init_db
from app.services.docx_preview_service import get_preview_converter_status

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    db_path = init_db()
    return {
        "ok": True,
        "app": APP_NAME,
        "database": str(db_path),
        "configured_database": str(get_db_path()),
        "docx_preview_converter": get_preview_converter_status(),
    }
