from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import archive_service

router = APIRouter()


@router.get("/course-class-units")
def list_course_class_archive_units(
    semester: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
) -> dict:
    return {
        "ok": True,
        "data": archive_service.list_course_class_archive_units(semester, course_id, class_id),
    }


@router.post("/course-class-units/archive")
def archive_course_class(course_id: int = Query(...), class_id: int = Query(...)) -> dict:
    try:
        result = archive_service.archive_course_class(course_id, class_id)
        return {"ok": True, "message": f"已归档 {result['updated_count']} 个批改任务。", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/course-class-units/restore")
def restore_course_class(course_id: int = Query(...), class_id: int = Query(...)) -> dict:
    try:
        result = archive_service.restore_course_class(course_id, class_id)
        return {"ok": True, "message": f"已恢复 {result['updated_count']} 个批改任务为进行中。", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
