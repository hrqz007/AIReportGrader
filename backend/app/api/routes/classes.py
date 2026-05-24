from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import CourseClassLinkCreate, TeachingClassCreate, TeachingClassUpdate
from app.services import class_service

router = APIRouter()


@router.get("")
def list_classes(course_id: int | None = Query(default=None)) -> dict:
    return {"ok": True, "data": class_service.list_classes(course_id)}


@router.post("")
def create_class(payload: TeachingClassCreate) -> dict:
    try:
        class_id = class_service.create_class(payload.class_name, payload.description, payload.course_id)
        return {"ok": True, "message": "教学班已创建。", "data": {"id": class_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{class_id}")
def get_class(class_id: int) -> dict:
    item = class_service.get_class(class_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到教学班。")
    return {"ok": True, "data": item}


@router.put("/{class_id}")
def update_class(class_id: int, payload: TeachingClassUpdate) -> dict:
    try:
        class_service.update_class(class_id, payload.class_name, payload.description)
        return {"ok": True, "message": "教学班已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{class_id}")
def delete_class(class_id: int) -> dict:
    try:
        class_service.delete_class(class_id)
        return {"ok": True, "message": "教学班已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/link")
def link_class_to_course(payload: CourseClassLinkCreate) -> dict:
    try:
        class_service.link_class_to_course(payload.class_id, payload.course_id)
        return {"ok": True, "message": "教学班已关联到课程。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/unlink")
def unlink_class_from_course(payload: CourseClassLinkCreate) -> dict:
    class_service.unlink_class_from_course(payload.class_id, payload.course_id)
    return {"ok": True, "message": "已取消教学班与课程的关联。"}

