from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.models.schemas import StudentCreate, StudentUpdate
from app.services import student_service

router = APIRouter()


@router.get("/template")
def download_student_template() -> Response:
    content = student_service.generate_student_template_excel()
    headers = {"Content-Disposition": "attachment; filename*=UTF-8''student_roster_template.xlsx"}
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/class-roster")
def list_class_students(class_id: int = Query(...)) -> dict:
    return {"ok": True, "data": student_service.list_class_students(class_id)}


@router.post("/class-roster/import")
async def import_class_students(
    class_id: int = Query(...),
    mode: str = Query(default="append"),
    file: UploadFile = File(...),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的学生名单文件。")
    suffix = Path(file.filename).suffix or ".xlsx"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        result = student_service.import_class_students_from_excel(class_id, tmp_path, mode=mode)
        return {"ok": True, "message": "学生名单导入完成。", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.post("/class-roster")
def create_class_student(class_id: int, payload: StudentCreate) -> dict:
    try:
        student_id = student_service.create_class_student(
            class_id,
            payload.student_no,
            payload.student_name,
            payload.class_name,
        )
        return {"ok": True, "message": "学生已添加到班级基础名单。", "data": {"id": student_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/class-roster/{student_id}")
def update_class_student(student_id: int, payload: StudentUpdate) -> dict:
    try:
        student_service.update_class_student(student_id, payload.student_no, payload.student_name, payload.class_name)
        return {"ok": True, "message": "班级基础名单学生已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/class-roster/{student_id}")
def delete_class_student(student_id: int) -> dict:
    try:
        student_service.delete_class_student(student_id)
        return {"ok": True, "message": "班级基础名单学生已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/class-roster/export")
def export_class_students(class_id: int = Query(...)) -> FileResponse:
    path = student_service.export_class_students_to_excel(class_id)
    return _download_excel(path)


@router.get("/course-roster")
def list_course_students(course_id: int = Query(...), class_id: int | None = Query(default=None)) -> dict:
    return {"ok": True, "data": student_service.list_course_students(course_id, class_id)}


@router.post("/course-roster")
def create_course_student(course_id: int, class_id: int, payload: StudentCreate) -> dict:
    try:
        student_id = student_service.create_course_student(
            course_id,
            class_id,
            payload.student_no,
            payload.student_name,
            payload.class_name,
        )
        return {"ok": True, "message": "学生已添加到课程名单副本。", "data": {"id": student_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/course-roster/{student_id}")
def update_course_student(student_id: int, payload: StudentUpdate) -> dict:
    try:
        student_service.update_course_student(student_id, payload.student_no, payload.student_name, payload.class_name)
        return {"ok": True, "message": "课程名单学生已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/course-roster/{student_id}")
def delete_course_student(student_id: int) -> dict:
    try:
        student_service.delete_course_student(student_id)
        return {"ok": True, "message": "课程名单学生已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/course-roster/export")
def export_course_students(course_id: int = Query(...), class_id: int | None = Query(default=None)) -> FileResponse:
    path = student_service.export_course_students_to_excel(course_id, class_id)
    return _download_excel(path)


@router.post("/course-roster/sync-from-class")
def sync_course_roster_from_class(course_id: int, class_id: int) -> dict:
    result = student_service.sync_course_roster_from_class(class_id, course_id)
    return {"ok": True, "message": "已从班级基础名单补齐课程名单副本。", "data": result}


def _download_excel(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )
