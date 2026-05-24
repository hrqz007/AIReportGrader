from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import RubricItemCreate, RubricItemUpdate
from app.services import rubric_service

router = APIRouter()


@router.get("")
def list_rubric_items(experiment_id: int = Query(...)) -> dict:
    items = rubric_service.list_rubric_items(experiment_id)
    return {
        "ok": True,
        "data": {
            "items": items,
            "total_score": rubric_service.get_total_score(experiment_id),
        },
    }


@router.post("")
def create_rubric_item(payload: RubricItemCreate) -> dict:
    try:
        item_id = rubric_service.create_rubric_item(
            payload.experiment_id,
            payload.item_name,
            payload.max_score,
            payload.description,
            payload.deduction_rules,
            payload.requires_review,
            payload.sort_order,
        )
        return {"ok": True, "message": "评分项已创建。", "data": {"id": item_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{item_id}")
def update_rubric_item(item_id: int, payload: RubricItemUpdate) -> dict:
    try:
        rubric_service.update_rubric_item(
            item_id,
            payload.item_name,
            payload.max_score,
            payload.description,
            payload.deduction_rules,
            payload.requires_review,
            payload.sort_order,
        )
        return {"ok": True, "message": "评分项已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{item_id}")
def delete_rubric_item(item_id: int) -> dict:
    try:
        rubric_service.delete_rubric_item(item_id)
        return {"ok": True, "message": "评分项已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/template")
def create_common_template(experiment_id: int = Query(...)) -> dict:
    try:
        count = rubric_service.create_common_report_rubric_template(experiment_id)
        return {"ok": True, "message": f"已生成 {count} 个通用评分项。", "data": {"count": count}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

