from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.services import system_data_service

router = APIRouter()


@router.get("/overview")
def get_system_overview() -> dict:
    return {"ok": True, "data": system_data_service.get_system_overview()}


@router.post("/backup")
def create_backup(
    include_api_keys: bool = Query(default=True),
    include_exports: bool = Query(default=False),
) -> dict:
    path = system_data_service.create_system_backup(
        include_api_keys=include_api_keys,
        include_exports=include_exports,
    )
    return {"ok": True, "message": "备份包已生成。", "data": {"path": str(path), "filename": path.name}}


@router.get("/backup/download")
def download_backup(
    include_api_keys: bool = Query(default=True),
    include_exports: bool = Query(default=False),
) -> FileResponse:
    path = system_data_service.create_system_backup(
        include_api_keys=include_api_keys,
        include_exports=include_exports,
    )
    return FileResponse(path=path, media_type="application/zip", filename=path.name)


@router.post("/backup/validate")
async def validate_backup(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    path = system_data_service.save_uploaded_backup(data)
    result = system_data_service.validate_backup_zip(path)
    result["saved_path"] = str(path)
    return {"ok": result["ok"], "message": result["message"], "data": result}


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), confirm_text: str = Query(default="")) -> dict:
    if confirm_text.strip() != "确认恢复":
        return {"ok": False, "message": "请输入“确认恢复”后再执行恢复。", "data": None}
    data = await file.read()
    path = system_data_service.save_uploaded_backup(data)
    result = system_data_service.restore_system_backup(path)
    return {"ok": result["ok"], "message": result["message"], "data": result}


@router.post("/clear/grading")
def clear_grading_data(confirm_text: str = Query(default="")) -> dict:
    if confirm_text.strip() != "清空批改数据":
        return {"ok": False, "message": "请输入“清空批改数据”后再执行。", "data": None}
    result = system_data_service.clear_grading_data()
    return {"ok": result["ok"], "message": result["message"], "data": result}


@router.post("/clear/business")
def clear_business_data(
    include_ai_configs: bool = Query(default=False),
    confirm_text: str = Query(default=""),
) -> dict:
    expected = "清空全部数据"
    if confirm_text.strip() != expected:
        return {"ok": False, "message": f"请输入“{expected}”后再执行。", "data": None}
    result = system_data_service.clear_business_data(include_ai_configs=include_ai_configs)
    return {"ok": result["ok"], "message": result["message"], "data": result}

