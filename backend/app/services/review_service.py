from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db.database import fetch_all, fetch_one, get_connection
from app.services.file_service import resolve_stored_file_path

AI_DONE = "初评完成"
AI_FAILED = "初评失败"
REVIEW_NOT_STARTED = "未复核"
REVIEW_DONE = "已复核"
MATCHED = "已匹配"
NAME_MISMATCH = "姓名不一致"
OBSOLETE_DUPLICATE = "重复作废"


def list_review_submissions(task_id: int, review_status: str | None = None) -> list[dict]:
    params: list[Any] = [
        REVIEW_NOT_STARTED,
        REVIEW_DONE,
        REVIEW_NOT_STARTED,
        REVIEW_DONE,
        task_id,
        MATCHED,
        NAME_MISMATCH,
        AI_DONE,
        OBSOLETE_DUPLICATE,
    ]
    status_clause = ""
    if review_status and review_status != "全部":
        status_clause = "AND COALESCE(s.review_status, ?) = ?"
        params.extend([REVIEW_NOT_STARTED, review_status])
    rows = fetch_all(
        f"""
        SELECT
            s.*,
            CASE WHEN COALESCE(s.review_status, ?) = ? THEN COALESCE(s.teacher_total_score, ts.total_score) ELSE NULL END AS final_teacher_total_score,
            CASE WHEN COALESCE(s.review_status, ?) = ? THEN COALESCE(s.teacher_overall_comment, ts.feedback) ELSE NULL END AS final_teacher_comment,
            ts.confirmed_at AS teacher_confirmed_at
        FROM submissions s
        LEFT JOIN teacher_scores ts ON ts.submission_id = s.id
        WHERE COALESCE(s.task_id, s.grading_task_id) = ?
          AND COALESCE(s.match_status, '') IN (?, ?)
          AND COALESCE(s.ai_status, '') = ?
          AND COALESCE(s.match_status, '') != ?
          {status_clause}
        ORDER BY
          CASE COALESCE(s.review_status, '{REVIEW_NOT_STARTED}') WHEN '{REVIEW_NOT_STARTED}' THEN 0 ELSE 1 END,
          s.student_no ASC,
          s.id ASC
        """,
        tuple(params),
    )
    return [dict(row) for row in rows]


def get_review_summary(task_id: int) -> dict:
    submissions = list_review_submissions(task_id)
    total = len(submissions)
    reviewed = sum(1 for item in submissions if item.get("review_status") == REVIEW_DONE)
    scores = [float(item["final_teacher_total_score"]) for item in submissions if item.get("final_teacher_total_score") is not None]
    return {
        "total": total,
        "ai_done": sum(1 for item in submissions if item.get("ai_status") == AI_DONE),
        "ai_failed": sum(1 for item in submissions if item.get("ai_status") == AI_FAILED),
        "pending": total - reviewed,
        "reviewed": reviewed,
        "average": round(sum(scores) / len(scores), 2) if scores else None,
    }


def get_review_detail(submission_id: int) -> dict | None:
    submission = fetch_one(
        """
        SELECT s.*,
               gt.task_name,
               c.course_name,
               tc.class_name AS task_class_name,
               e.experiment_name
        FROM submissions s
        LEFT JOIN grading_tasks gt ON gt.id = COALESCE(s.task_id, s.grading_task_id)
        LEFT JOIN courses c ON c.id = gt.course_id
        LEFT JOIN teaching_classes tc ON tc.id = gt.class_id
        LEFT JOIN experiments e ON e.id = gt.experiment_id
        WHERE s.id = ?
        """,
        (submission_id,),
    )
    if not submission:
        return None
    ai_scores = fetch_all("SELECT * FROM ai_scores WHERE submission_id = ? ORDER BY id ASC", (submission_id,))
    teacher_score = fetch_one("SELECT * FROM teacher_scores WHERE submission_id = ?", (submission_id,))
    teacher_items = _loads_json(teacher_score.get("item_scores_json") if teacher_score else None, [])
    return {
        "submission": submission,
        "ai_scores": ai_scores,
        "teacher_score": teacher_score,
        "teacher_items": teacher_items,
        "image_paths": _loads_json(submission.get("image_paths"), []),
        "detected_flags": _loads_json(submission.get("detected_flags"), {}),
    }


def get_original_report_file(submission_id: int) -> tuple[Path, str]:
    submission = fetch_one("SELECT original_filename, stored_file_path FROM submissions WHERE id = ?", (submission_id,))
    if not submission:
        raise FileNotFoundError("未找到提交记录。")
    path = resolve_stored_file_path(submission.get("stored_file_path"))
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("原始 Word 报告文件不存在。")
    filename = submission.get("original_filename") or path.name
    return path, filename


def get_submission_image_file(submission_id: int, image_index: int) -> Path:
    submission = fetch_one("SELECT image_paths FROM submissions WHERE id = ?", (submission_id,))
    if not submission:
        raise FileNotFoundError("未找到提交记录。")
    image_paths = _loads_json(submission.get("image_paths"), [])
    if image_index < 1 or image_index > len(image_paths):
        raise FileNotFoundError("未找到指定截图。")
    path = resolve_stored_file_path(image_paths[image_index - 1])
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("截图文件不存在。")
    return path


def initialize_teacher_scores_from_ai(submission_id: int, force: bool = False) -> dict:
    detail = get_review_detail(submission_id)
    if not detail:
        return {"ok": False, "message": "未找到提交记录。"}
    if detail["teacher_score"] and not force:
        return {"ok": True, "message": "已存在教师复核记录。"}
    if not detail["ai_scores"]:
        return {"ok": False, "message": "当前报告没有 AI 分项建议分，无法初始化教师确认分。"}
    rows = []
    for score in detail["ai_scores"]:
        ai_score = float(score.get("ai_score") or 0)
        rows.append(
            {
                "rubric_item_id": score.get("rubric_item_id"),
                "item_name": score.get("item_name") or "",
                "max_score": float(score.get("max_score") or 0),
                "ai_score": ai_score,
                "teacher_score": ai_score,
                "teacher_comment": "",
                "deduction_reason": score.get("deduction_reason") or "",
                "confidence": score.get("confidence") or "",
                "need_teacher_review": bool(score.get("need_teacher_review")),
            }
        )
    return save_teacher_scores(submission_id, rows, overall_comment="", reviewer_name="", mark_completed=False)


def save_teacher_scores(
    submission_id: int,
    score_rows: list[dict],
    overall_comment: str | None = None,
    reviewer_name: str | None = None,
    mark_completed: bool = True,
) -> dict:
    submission = fetch_one("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    if not submission:
        return {"ok": False, "message": "未找到提交记录。"}
    normalized_rows = []
    total = 0.0
    invalid_items = []
    for row in score_rows:
        max_score = float(row.get("max_score") or 0)
        ai_score = float(row.get("ai_score") or 0)
        teacher_score = float(row.get("teacher_score") or 0)
        if teacher_score < 0 or teacher_score > max_score:
            invalid_items.append(f"{row.get('item_name') or '未命名评分项'}：填写 {teacher_score}，满分 {max_score}")
            continue
        total += teacher_score
        normalized_rows.append(
            {
                "rubric_item_id": row.get("rubric_item_id"),
                "item_name": row.get("item_name") or "",
                "max_score": max_score,
                "ai_score": ai_score,
                "teacher_score": round(teacher_score, 2),
                "teacher_comment": row.get("teacher_comment") or "",
                "is_modified": abs(teacher_score - ai_score) > 0.001,
                "deduction_reason": row.get("deduction_reason") or "",
                "confidence": row.get("confidence") or "",
                "need_teacher_review": bool(row.get("need_teacher_review")),
            }
        )
    if invalid_items:
        return {"ok": False, "message": "教师确认分必须在 0 到该项满分之间：" + "；".join(invalid_items)}
    task_id = int(submission.get("task_id") or submission.get("grading_task_id"))
    status = REVIEW_DONE if mark_completed else REVIEW_NOT_STARTED
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO teacher_scores (submission_id, task_id, total_score, item_scores_json, feedback, reviewer_name)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(submission_id) DO UPDATE SET
                task_id = excluded.task_id,
                total_score = excluded.total_score,
                item_scores_json = excluded.item_scores_json,
                feedback = excluded.feedback,
                reviewer_name = excluded.reviewer_name,
                confirmed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (submission_id, task_id, round(total, 2), json.dumps(normalized_rows, ensure_ascii=False), overall_comment or "", reviewer_name or ""),
        )
        conn.execute(
            """
            UPDATE submissions
            SET review_status = ?,
                teacher_total_score = ?,
                teacher_overall_comment = ?,
                reviewed_at = CASE WHEN ? = ? THEN CURRENT_TIMESTAMP ELSE reviewed_at END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, round(total, 2), overall_comment or "", status, REVIEW_DONE, submission_id),
        )
        conn.commit()
    return {"ok": True, "message": "教师确认分已保存。", "total_score": round(total, 2)}


def reset_review(submission_id: int) -> dict:
    with get_connection() as conn:
        conn.execute("DELETE FROM teacher_scores WHERE submission_id = ?", (submission_id,))
        conn.execute(
            """
            UPDATE submissions
            SET review_status = ?,
                teacher_total_score = NULL,
                teacher_overall_comment = NULL,
                reviewed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (REVIEW_NOT_STARTED, submission_id),
        )
        conn.commit()
    return {"ok": True, "message": "该报告复核状态已重置。"}


def _loads_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
