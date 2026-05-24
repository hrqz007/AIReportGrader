from __future__ import annotations

import json
from pathlib import Path

from app.db.database import execute, fetch_all, fetch_one, get_connection
from app.services import anonymizer, file_service, report_parser


MATCHED = "已匹配"
UNMATCHED = "未匹配"
NAME_MISMATCH = "姓名不一致"
DUPLICATE = "重复提交"
OBSOLETE_DUPLICATE = "重复作废"

AI_NOT_STARTED = "未初评"
REVIEW_NOT_STARTED = "未复核"
REVIEW_DONE = "已复核"
PARSE_NOT_STARTED = "未解析"
PARSE_DONE = "解析完成"
PARSE_FAILED = "解析失败"


def create_submission(
    task_id: int,
    original_filename: str,
    stored_file_path: str | Path,
    parsed_student_no: str | None = None,
    parsed_student_name: str | None = None,
    student_id: int | None = None,
    student_no: str | None = None,
    student_name: str | None = None,
    anonymous_id: str | None = None,
    match_status: str = UNMATCHED,
) -> int:
    return execute(
        """
        INSERT INTO submissions (
            task_id, grading_task_id, student_id, student_no, student_name, anonymous_id,
            original_filename, stored_file_path, matched_student_no, matched_student_name,
            parsed_student_no, parsed_student_name, match_status, ai_status, review_status,
            parse_status, uploaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            task_id,
            task_id,
            student_id,
            student_no,
            student_name,
            anonymous_id,
            original_filename,
            str(stored_file_path),
            student_no,
            student_name,
            parsed_student_no,
            parsed_student_name,
            match_status,
            AI_NOT_STARTED,
            REVIEW_NOT_STARTED,
            PARSE_NOT_STARTED,
        ),
    )


def list_submissions(task_id: int, match_status: str | None = None) -> list[dict]:
    params: list[object] = [task_id]
    status_clause = ""
    if match_status and match_status != "全部":
        status_clause = "AND s.match_status = ?"
        params.append(match_status)
    return fetch_all(
        f"""
        SELECT s.*
        FROM submissions s
        WHERE COALESCE(s.task_id, s.grading_task_id) = ?
        {status_clause}
        ORDER BY s.uploaded_at DESC, s.id DESC
        """,
        tuple(params),
    )


def get_submission(submission_id: int) -> dict | None:
    return fetch_one("SELECT * FROM submissions WHERE id = ?", (submission_id,))


def get_submission_detail(submission_id: int) -> dict | None:
    submission = get_submission(submission_id)
    if not submission:
        return None
    submission["text_length"] = len(submission.get("plain_text") or "")
    try:
        submission["image_count"] = len(json.loads(submission.get("image_paths") or "[]"))
    except json.JSONDecodeError:
        submission["image_count"] = 0
    try:
        submission["detected_flags_data"] = json.loads(submission.get("detected_flags") or "{}")
    except json.JSONDecodeError:
        submission["detected_flags_data"] = {}
    return submission


def delete_submission(submission_id: int) -> None:
    delete_submissions([submission_id])


def delete_submissions(submission_ids: list[int]) -> int:
    ids = [int(item) for item in submission_ids if int(item) > 0]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, original_filename, review_status
            FROM submissions
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        ).fetchall()
        reviewed = [row for row in rows if row["review_status"] == REVIEW_DONE]
        if reviewed:
            names = "、".join((row["original_filename"] or f"提交记录 {row['id']}") for row in reviewed[:5])
            if len(reviewed) > 5:
                names += " 等"
            raise ValueError(f"已复核报告不能直接删除：{names}。请先确认成绩处理方式，避免误删最终成绩。")
        conn.execute(f"DELETE FROM teacher_scores WHERE submission_id IN ({placeholders})", tuple(ids))
        conn.execute(f"DELETE FROM ai_scores WHERE submission_id IN ({placeholders})", tuple(ids))
        cursor = conn.execute(f"DELETE FROM submissions WHERE id IN ({placeholders})", tuple(ids))
        conn.commit()
        return int(cursor.rowcount or 0)


def update_submission_match(submission_id: int, student_id: int, match_status: str = MATCHED) -> None:
    student = fetch_one("SELECT * FROM students WHERE id = ?", (student_id,))
    if student is None:
        raise ValueError("未找到要绑定的学生。")
    execute(
        """
        UPDATE submissions
        SET student_id = ?,
            student_no = ?,
            student_name = ?,
            anonymous_id = ?,
            matched_student_no = ?,
            matched_student_name = ?,
            match_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            student["id"],
            student["student_no"],
            student["student_name"] or student["name"],
            student["anonymous_id"],
            student["student_no"],
            student["student_name"] or student["name"],
            match_status,
            submission_id,
        ),
    )


def confirm_duplicate_as_active(submission_id: int) -> dict:
    submission = get_submission(submission_id)
    if submission is None:
        return {"ok": False, "message": "未找到提交记录。"}
    if not submission.get("student_id"):
        return {"ok": False, "message": "该提交尚未绑定学生，不能确认使用。"}

    task_id = int(submission.get("task_id") or submission.get("grading_task_id"))
    student_id = int(submission["student_id"])
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE submissions
            SET match_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE COALESCE(task_id, grading_task_id) = ?
              AND student_id = ?
              AND id != ?
            """,
            (OBSOLETE_DUPLICATE, task_id, student_id, submission_id),
        )
        conn.execute(
            """
            UPDATE submissions
            SET match_status = ?,
                ai_status = ?,
                review_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (MATCHED, AI_NOT_STARTED, REVIEW_NOT_STARTED, submission_id),
        )
        conn.commit()
    return {"ok": True, "message": "已将该报告设为有效提交，其他重复提交已标记为重复作废。", "obsolete_count": int(cursor.rowcount or 0)}


def has_existing_submission_for_student(task_id: int, student_id: int) -> bool:
    row = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM submissions
        WHERE COALESCE(task_id, grading_task_id) = ?
          AND student_id = ?
          AND match_status != ?
        """,
        (task_id, student_id, OBSOLETE_DUPLICATE),
    )
    return int(row["count"] or 0) > 0


def find_student_for_task(task_id: int, student_no: str | None) -> dict | None:
    if not student_no:
        return None
    task = fetch_one("SELECT * FROM grading_tasks WHERE id = ?", (task_id,))
    if task is None:
        return None
    row = fetch_one(
        """
        SELECT *
        FROM students
        WHERE course_id = ? AND class_id = ? AND student_no = ?
        """,
        (task["course_id"], task["class_id"], student_no),
    )
    return row


def build_match_result(task_id: int, parsed_student_no: str, parsed_student_name: str) -> dict:
    student = find_student_for_task(task_id, parsed_student_no)
    if student is None:
        return {
            "student": None,
            "match_status": UNMATCHED,
            "student_no": None,
            "student_name": None,
            "anonymous_id": None,
        }

    roster_name = student.get("student_name") or student.get("name") or ""
    if has_existing_submission_for_student(task_id, int(student["id"])):
        status = DUPLICATE
    elif parsed_student_name and parsed_student_name != roster_name:
        status = NAME_MISMATCH
    else:
        status = MATCHED
    return {
        "student": student,
        "match_status": status,
        "student_no": student.get("student_no"),
        "student_name": roster_name,
        "anonymous_id": student.get("anonymous_id"),
    }


def get_task_summary(task_id: int) -> dict[str, int]:
    task = fetch_one("SELECT * FROM grading_tasks WHERE id = ?", (task_id,))
    if task is None:
        raise ValueError("未找到批改任务。")
    student_count = fetch_one(
        "SELECT COUNT(*) AS count FROM students WHERE course_id = ? AND class_id = ?",
        (task["course_id"], task["class_id"]),
    )["count"]
    if int(student_count or 0) == 0:
        student_count = fetch_one("SELECT COUNT(*) AS count FROM class_students WHERE class_id = ?", (task["class_id"],))["count"]

    rows = fetch_all(
        """
        SELECT match_status, ai_status, review_status, COUNT(*) AS count
        FROM submissions
        WHERE COALESCE(task_id, grading_task_id) = ?
        GROUP BY match_status, ai_status, review_status
        """,
        (task_id,),
    )
    total = sum(int(row["count"] or 0) for row in rows)
    matched = sum(int(row["count"] or 0) for row in rows if row["match_status"] == MATCHED)
    unmatched = sum(int(row["count"] or 0) for row in rows if row["match_status"] in {UNMATCHED, NAME_MISMATCH, DUPLICATE})
    duplicate = sum(int(row["count"] or 0) for row in rows if row["match_status"] == DUPLICATE)
    ai_done = sum(int(row["count"] or 0) for row in rows if row["ai_status"] == "初评完成")
    reviewed = sum(int(row["count"] or 0) for row in rows if row["review_status"] == "已复核")
    return {
        "student_count": int(student_count or 0),
        "upload_count": total,
        "matched_count": matched,
        "unmatched_count": unmatched,
        "duplicate_count": duplicate,
        "ai_done_count": ai_done,
        "reviewed_count": reviewed,
    }


def parse_submission(submission_id: int) -> dict:
    submission = get_submission(submission_id)
    if submission is None:
        raise ValueError("未找到提交记录。")

    task_id = int(submission.get("task_id") or submission.get("grading_task_id"))
    stored_file_path = file_service.resolve_stored_file_path(submission.get("stored_file_path"))
    try:
        if not stored_file_path.exists():
            raise FileNotFoundError(f"报告文件不存在：{stored_file_path}")

        plain_text = report_parser.parse_report_text(stored_file_path)
        image_output_dir = file_service.task_images_dir(task_id, submission_id)
        image_paths = report_parser.extract_report_images(stored_file_path, image_output_dir)

        student_no = submission.get("student_no")
        student_name = submission.get("student_name")
        class_name = None
        if submission.get("student_id"):
            student = fetch_one("SELECT * FROM students WHERE id = ?", (submission["student_id"],))
            if student:
                student_no = student.get("student_no") or student_no
                student_name = student.get("student_name") or student.get("name") or student_name
                class_name = student.get("class_name")

        detected_flags = anonymizer.detect_sensitive_info(
            plain_text,
            student_no=student_no,
            student_name=student_name,
            class_name=class_name,
        )
        anonymized_text = anonymizer.anonymize_text(
            plain_text,
            student_no=student_no,
            student_name=student_name,
            class_name=class_name,
        )

        execute(
            """
            UPDATE submissions
            SET plain_text = ?,
                anonymized_text = ?,
                image_paths = ?,
                detected_flags = ?,
                parse_status = ?,
                parse_error = NULL,
                parsed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                plain_text,
                anonymized_text,
                json.dumps(image_paths, ensure_ascii=False),
                json.dumps(detected_flags, ensure_ascii=False),
                PARSE_DONE,
                submission_id,
            ),
        )
        return {
            "ok": True,
            "submission_id": submission_id,
            "parse_status": PARSE_DONE,
            "text_length": len(plain_text),
            "image_count": len(image_paths),
            "detected_flags": detected_flags,
        }
    except Exception as exc:
        error_message = str(exc)
        execute(
            """
            UPDATE submissions
            SET parse_status = ?,
                parse_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (PARSE_FAILED, error_message, submission_id),
        )
        return {
            "ok": False,
            "submission_id": submission_id,
            "parse_status": PARSE_FAILED,
            "text_length": 0,
            "image_count": 0,
            "detected_flags": {},
            "parse_error": error_message,
        }


def parse_submissions_by_task(task_id: int, reparse: bool = False) -> dict:
    submissions = list_submissions(task_id)
    total = len(submissions)
    success = 0
    failed = 0
    skipped = 0
    allowed_statuses = {MATCHED, NAME_MISMATCH}

    for submission in submissions:
        if submission.get("match_status") not in allowed_statuses:
            skipped += 1
            continue
        if not reparse and submission.get("parse_status") == PARSE_DONE:
            skipped += 1
            continue
        result = parse_submission(int(submission["id"]))
        if result.get("ok"):
            success += 1
        else:
            failed += 1
    return {"total": total, "success": success, "failed": failed, "skipped": skipped}


def get_parse_summary(task_id: int) -> dict[str, int]:
    submissions = list_submissions(task_id)
    image_total = 0
    for submission in submissions:
        try:
            image_total += len(json.loads(submission.get("image_paths") or "[]"))
        except json.JSONDecodeError:
            pass
    return {
        "total": len(submissions),
        "matched": sum(1 for item in submissions if item.get("match_status") in {MATCHED, NAME_MISMATCH}),
        "not_parsed": sum(1 for item in submissions if item.get("parse_status") in {None, "", PARSE_NOT_STARTED}),
        "parsed": sum(1 for item in submissions if item.get("parse_status") == PARSE_DONE),
        "failed": sum(1 for item in submissions if item.get("parse_status") == PARSE_FAILED),
        "image_total": image_total,
    }
