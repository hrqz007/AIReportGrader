from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.services import export_service

router = APIRouter()


@router.get("/preview/{task_id}")
def preview_export_data(task_id: int, mode: str = Query(default="reviewed_only")) -> dict:
    data = export_service.build_export_data(task_id, mode=mode)
    return {
        "ok": True,
        "data": {
            "task": data["task"],
            "summary": data["summary"],
            "grades": data["grades"],
            "items": data["items"],
            "unfinished": data["unfinished"],
        },
    }


@router.get("/analysis/{task_id}")
def get_analysis_data(task_id: int, mode: str = Query(default="reviewed_only")) -> dict:
    data = export_service.build_export_data(task_id, mode=mode)
    return {
        "ok": True,
        "data": {
            "task": data["task"],
            "summary": data["summary"],
            "distribution": data["distribution"],
            "rubric_analysis": data["rubric_analysis"],
            "pass_fail": data["pass_fail"],
            "ai_diff": data["ai_diff"],
        },
    }


@router.get("/grades-excel/{task_id}")
def download_grades_excel(task_id: int, mode: str = Query(default="reviewed_only")) -> FileResponse:
    path = export_service.export_grades_to_excel(task_id, mode=mode)
    return _download(path)


@router.get("/analysis-excel/{task_id}")
def download_analysis_excel(task_id: int, mode: str = Query(default="reviewed_only")) -> FileResponse:
    path = export_service.export_analysis_to_excel(task_id, mode=mode)
    return _download(path)


def _download(path: Path) -> FileResponse:
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )
