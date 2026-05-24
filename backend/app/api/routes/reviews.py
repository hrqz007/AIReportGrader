from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from app.models.schemas import ReviewSave
from app.services.docx_preview_service import docx_to_best_preview, get_docx_pdf_preview_path
from app.services import review_service

router = APIRouter()


@router.get("/summary/{task_id}")
def get_review_summary(task_id: int) -> dict:
    return {"ok": True, "data": review_service.get_review_summary(task_id)}


@router.get("/submissions")
def list_review_submissions(task_id: int = Query(...), review_status: str | None = Query(default=None)) -> dict:
    return {"ok": True, "data": review_service.list_review_submissions(task_id, review_status)}


@router.get("/submissions/{submission_id}")
def get_review_detail(submission_id: int) -> dict:
    return {"ok": True, "data": review_service.get_review_detail(submission_id)}


@router.get("/submissions/{submission_id}/download-original")
def download_original_report(submission_id: int) -> FileResponse:
    try:
        path, filename = review_service.get_original_report_file(submission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=path,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        filename=filename,
    )


@router.get("/submissions/{submission_id}/preview-original", response_class=HTMLResponse)
def preview_original_report(submission_id: int) -> HTMLResponse:
    try:
        path, _filename = review_service.get_original_report_file(submission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pdf_url = f"/api/reviews/submissions/{submission_id}/preview-original-pdf"
    return HTMLResponse(docx_to_best_preview(path, pdf_url))


@router.get("/submissions/{submission_id}/preview-original-pdf")
def preview_original_report_pdf(submission_id: int) -> FileResponse:
    try:
        path, filename = review_service.get_original_report_file(submission_id)
        pdf_path = get_docx_pdf_preview_path(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{filename.rsplit('.', 1)[0]}.pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/submissions/{submission_id}/images/{image_index}")
def get_submission_image(submission_id: int, image_index: int) -> FileResponse:
    try:
        path = review_service.get_submission_image_file(submission_id, image_index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/submissions/{submission_id}/initialize")
def initialize_teacher_scores(submission_id: int, force: bool = Query(default=False)) -> dict:
    return review_service.initialize_teacher_scores_from_ai(submission_id, force=force)


@router.post("/submissions/{submission_id}/save")
def save_teacher_scores(submission_id: int, payload: ReviewSave) -> dict:
    return review_service.save_teacher_scores(
        submission_id,
        [item.model_dump() for item in payload.score_rows],
        overall_comment=payload.overall_comment,
        reviewer_name=payload.reviewer_name,
        mark_completed=payload.mark_completed,
    )


@router.post("/submissions/{submission_id}/reset")
def reset_review(submission_id: int) -> dict:
    return review_service.reset_review(submission_id)
