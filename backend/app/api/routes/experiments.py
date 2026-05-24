from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ExperimentClone, ExperimentCreate, ExperimentUpdate
from app.services import experiment_service

router = APIRouter()


@router.get("")
def list_experiments(course_id: int | None = Query(default=None)) -> dict:
    return {"ok": True, "data": experiment_service.list_experiments(course_id)}


@router.post("")
def create_experiment(payload: ExperimentCreate) -> dict:
    try:
        experiment_id = experiment_service.create_experiment(
            payload.course_id,
            payload.experiment_name,
            payload.experiment_objectives,
            payload.experiment_requirements,
            payload.required_screenshots,
            payload.key_evaluation_points,
            payload.common_errors,
            payload.special_notes,
        )
        return {"ok": True, "message": "实验任务已创建。", "data": {"id": experiment_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/clone")
def clone_experiment(payload: ExperimentClone) -> dict:
    try:
        result = experiment_service.clone_experiment_with_rubrics(
            payload.source_experiment_id,
            payload.target_course_id,
            payload.experiment_name,
        )
        return {"ok": True, "message": "历史实验任务和评分标准已复制到当前课程。", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{experiment_id}")
def get_experiment(experiment_id: int) -> dict:
    experiment = experiment_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="未找到实验任务。")
    return {"ok": True, "data": experiment}


@router.put("/{experiment_id}")
def update_experiment(experiment_id: int, payload: ExperimentUpdate) -> dict:
    try:
        experiment_service.update_experiment(
            experiment_id,
            payload.experiment_name,
            payload.experiment_objectives,
            payload.experiment_requirements,
            payload.required_screenshots,
            payload.key_evaluation_points,
            payload.common_errors,
            payload.special_notes,
        )
        return {"ok": True, "message": "实验任务已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: int) -> dict:
    try:
        experiment_service.delete_experiment(experiment_id)
        return {"ok": True, "message": "实验任务已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{experiment_id}/dependencies")
def count_experiment_dependencies(experiment_id: int) -> dict:
    return {"ok": True, "data": experiment_service.count_experiment_dependencies(experiment_id)}
