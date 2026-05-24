from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models.schemas import SubmissionMatchUpdate
from app.services import file_service, submission_service
from app.utils.filename_parser import parse_student_from_filename

router = APIRouter()


@router.get("")
def list_submissions(task_id: int = Query(...), match_status: str | None = Query(default=None)) -> dict:
    return {"ok": True, "data": submission_service.list_submissions(task_id, match_status)}


@router.get("/parse-summary/{task_id}")
def get_parse_summary(task_id: int) -> dict:
    return {"ok": True, "data": submission_service.get_parse_summary(task_id)}


@router.get("/{submission_id}")
def get_submission(submission_id: int) -> dict:
    submission = submission_service.get_submission_detail(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="未找到提交记录。")
    return {"ok": True, "data": submission}


@router.post("/upload")
def upload_reports(task_id: int = Query(...), files: list[UploadFile] = File(...)) -> dict:
    results: list[dict] = []
    for uploaded_file in files:
        original_filename = uploaded_file.filename or ""
        if not file_service.is_supported_report_file(original_filename):
            results.append(
                {
                    "original_filename": original_filename,
                    "ok": False,
                    "error": "当前版本支持 .docx、.doc 和 .pdf 文件。",
                    "match_status": submission_service.UNMATCHED,
                }
            )
            continue

        try:
            parsed = parse_student_from_filename(original_filename)
            match = submission_service.build_match_result(
                task_id,
                parsed.get("student_no") or "",
                parsed.get("student_name") or "",
            )
            stored_path = file_service.save_upload_file(uploaded_file, task_id, parsed.get("student_no") or None)
            submission_id = submission_service.create_submission(
                task_id=task_id,
                original_filename=original_filename,
                stored_file_path=stored_path,
                parsed_student_no=parsed.get("student_no"),
                parsed_student_name=parsed.get("student_name"),
                student_id=match["student"]["id"] if match["student"] else None,
                student_no=match.get("student_no"),
                student_name=match.get("student_name"),
                anonymous_id=match.get("anonymous_id"),
                match_status=match["match_status"],
            )
            results.append(
                {
                    "ok": True,
                    "submission_id": submission_id,
                    "original_filename": original_filename,
                    "parsed_student_no": parsed.get("student_no"),
                    "parsed_student_name": parsed.get("student_name"),
                    "student_name": match.get("student_name"),
                    "anonymous_id": match.get("anonymous_id"),
                    "match_status": match["match_status"],
                    "stored_file_path": str(stored_path),
                    "parse_status": submission_service.PARSE_NOT_STARTED,
                    "ai_status": submission_service.AI_NOT_STARTED,
                    "review_status": submission_service.REVIEW_NOT_STARTED,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "original_filename": original_filename,
                    "ok": False,
                    "error": str(exc),
                    "match_status": submission_service.UNMATCHED,
                }
            )

    success = sum(1 for item in results if item.get("ok"))
    failed = len(results) - success
    return {"ok": True, "message": f"上传处理完成：成功 {success} 份，失败 {failed} 份。", "data": results}


@router.put("/{submission_id}/match")
def update_submission_match(submission_id: int, payload: SubmissionMatchUpdate) -> dict:
    try:
        submission_service.update_submission_match(submission_id, payload.student_id, payload.match_status)
        return {"ok": True, "message": "提交记录已绑定学生。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{submission_id}/confirm-duplicate")
def confirm_duplicate(submission_id: int) -> dict:
    result = submission_service.confirm_duplicate_as_active(submission_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message") or "操作失败。")
    return result


@router.post("/{submission_id}/parse")
def parse_submission(submission_id: int) -> dict:
    result = submission_service.parse_submission(submission_id)
    return {"ok": bool(result.get("ok")), "message": "解析完成。" if result.get("ok") else "解析失败。", "data": result}


@router.post("/parse-task")
def parse_task_submissions(task_id: int = Query(...), reparse: bool = Query(default=False)) -> dict:
    result = submission_service.parse_submissions_by_task(task_id, reparse=reparse)
    return {
        "ok": True,
        "message": f"批量解析完成：成功 {result['success']} 份，失败 {result['failed']} 份，跳过 {result['skipped']} 份。",
        "data": result,
    }


@router.delete("/{submission_id}")
def delete_submission(submission_id: int) -> dict:
    try:
        submission_service.delete_submission(submission_id)
        return {"ok": True, "message": "提交记录已删除。"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch-delete")
def delete_submissions(submission_ids: list[int]) -> dict:
    try:
        count = submission_service.delete_submissions(submission_ids)
        return {"ok": True, "message": f"已删除 {count} 条提交记录。", "data": {"count": count}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
