from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import AIProviderCreate, AIProviderUpdate
from app.services import ai_provider_service

router = APIRouter()


@router.get("")
def list_configs() -> dict:
    configs = [ai_provider_service.public_config(item) for item in ai_provider_service.list_configs()]
    return {"ok": True, "data": configs}


@router.get("/default")
def get_default_config() -> dict:
    config = ai_provider_service.get_default_config()
    return {"ok": True, "data": ai_provider_service.public_config(config) if config else None}


@router.post("")
def create_config(payload: AIProviderCreate) -> dict:
    try:
        config_id = ai_provider_service.create_config(payload.model_dump())
        return {"ok": True, "message": "AI 配置已创建。", "data": {"id": config_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{config_id}")
def update_config(config_id: int, payload: AIProviderUpdate) -> dict:
    try:
        ai_provider_service.update_config(config_id, payload.model_dump())
        return {"ok": True, "message": "AI 配置已保存。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{config_id}")
def delete_config(config_id: int) -> dict:
    ai_provider_service.delete_config(config_id)
    return {"ok": True, "message": "AI 配置已删除。"}


@router.post("/{config_id}/test")
def test_config(config_id: int) -> dict:
    return ai_provider_service.test_config(config_id)
