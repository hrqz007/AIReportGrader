from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import scoring_service

router = APIRouter()


@router.get("/summary/{task_id}")
def get_ai_summary(task_id: int) -> dict:
    return {"ok": True, "data": scoring_service.get_ai_summary(task_id)}


@router.get("/scores/{submission_id}")
def list_ai_scores(submission_id: int) -> dict:
    return {"ok": True, "data": scoring_service.list_ai_scores(submission_id)}


@router.post("/submissions/{submission_id}/score")
def score_submission(
    submission_id: int,
    rescore: bool = Query(default=True),
    use_vision: bool = Query(default=False),
    image_mode: str = Query(default="first_3"),
    image_indices: str | None = Query(default=None),
) -> dict:
    selected_indices = _parse_image_indices(image_indices)
    return scoring_service.score_submission(
        submission_id,
        rescore=rescore,
        use_vision=use_vision,
        image_mode=image_mode,
        image_indices=selected_indices,
    )


@router.post("/tasks/{task_id}/score")
def score_task(
    task_id: int,
    rescore_completed: bool = Query(default=False),
    use_vision: bool = Query(default=False),
    image_mode: str = Query(default="first_3"),
) -> dict:
    result = scoring_service.score_task(
        task_id,
        rescore_completed=rescore_completed,
        use_vision=use_vision,
        image_mode=image_mode,
    )
    return {"ok": True, "message": f"批量初评完成：成功 {result['success']} 份，失败 {result['failed']} 份，跳过 {result['skipped']} 份。", "data": result}


@router.post("/submissions/{submission_id}/reset")
def reset_submission_ai_status(submission_id: int) -> dict:
    return scoring_service.reset_submission_ai_status(submission_id)


@router.post("/test-default")
def test_default_config() -> dict:
    return scoring_service.test_default_config()


def _parse_image_indices(value: str | None) -> list[int]:
    if not value:
        return []
    indices: list[int] = []
    for part in value.split(","):
        try:
            index = int(part.strip())
        except ValueError:
            continue
        if index > 0:
            indices.append(index)
    return indices
