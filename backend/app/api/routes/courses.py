from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import CourseCreate, CourseUpdate
from app.services import course_service

router = APIRouter()


@router.get("")
def list_courses() -> dict:
    return {"ok": True, "data": course_service.list_courses()}


@router.post("")
def create_course(payload: CourseCreate) -> dict:
    try:
        course_id = course_service.create_course(
            payload.course_name,
            payload.course_type,
            payload.semester,
            payload.description,
        )
        return {"ok": True, "message": "课程已创建。", "data": {"id": course_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{course_id}")
def get_course(course_id: int) -> dict:
    course = course_service.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="未找到课程。")
    return {"ok": True, "data": course}


@router.put("/{course_id}")
def update_course(course_id: int, payload: CourseUpdate) -> dict:
    try:
        course_service.update_course(
            course_id,
            payload.course_name,
            payload.course_type,
            payload.semester,
            payload.description,
        )
        return {"ok": True, "message": "课程已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{course_id}")
def delete_course(course_id: int) -> dict:
    try:
        course_service.delete_course(course_id)
        return {"ok": True, "message": "课程已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

