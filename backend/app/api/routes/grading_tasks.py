from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import GradingTaskCreate, GradingTaskUpdate
from app.services import grading_task_service, rubric_service, submission_service

router = APIRouter()


@router.get("")
def list_grading_tasks(
    course_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
    experiment_id: int | None = Query(default=None),
    include_ended: bool = Query(default=False),
    status: str | None = Query(default=None),
) -> dict:
    return {"ok": True, "data": grading_task_service.list_grading_tasks(course_id, class_id, experiment_id, include_ended, status)}


@router.post("")
def create_grading_task(payload: GradingTaskCreate) -> dict:
    try:
        task_id = grading_task_service.create_grading_task(
            payload.task_name,
            payload.course_id,
            payload.class_id,
            payload.experiment_id,
            payload.description,
        )
        rubric_total = rubric_service.get_total_score(payload.experiment_id)
        message = "批改任务已创建。"
        if rubric_total <= 0:
            message += " 当前实验任务尚未配置评分标准，后续 AI 初评前请先补充。"
        return {"ok": True, "message": message, "data": {"id": task_id, "rubric_total": rubric_total}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{task_id}")
def get_grading_task(task_id: int) -> dict:
    task = grading_task_service.get_grading_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="未找到批改任务。")
    task["summary"] = submission_service.get_task_summary(task_id)
    return {"ok": True, "data": task}


@router.put("/{task_id}")
def update_grading_task(task_id: int, payload: GradingTaskUpdate) -> dict:
    try:
        grading_task_service.update_grading_task(task_id, payload.task_name, payload.description, payload.status)
        return {"ok": True, "message": "批改任务已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{task_id}")
def delete_grading_task(task_id: int) -> dict:
    try:
        count = grading_task_service.count_task_submissions(task_id)
        if count > 0:
            raise ValueError("该批改任务下已有提交记录，当前版本不允许直接删除。")
        grading_task_service.delete_grading_task(task_id)
        return {"ok": True, "message": "批改任务已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{task_id}/summary")
def get_task_summary(task_id: int) -> dict:
    try:
        return {"ok": True, "data": submission_service.get_task_summary(task_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
