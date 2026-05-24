from __future__ import annotations

from app.db.database import fetch_all, get_connection, sqlite_utc_to_local_text
from app.services.grading_task_service import TASK_ACTIVE, TASK_ARCHIVED, TASK_ENDED


def list_course_class_archive_units(
    semester: str | None = None,
    course_id: int | None = None,
    class_id: int | None = None,
) -> list[dict]:
    """Return archive units grouped by semester + course + teaching class.

    The archive unit intentionally operates on grading tasks only. Courses,
    teaching classes, rosters, submissions, scores and uploaded files remain
    unchanged so the operation is reversible.
    """
    conditions = ["(c.deleted_at IS NULL OR TRIM(c.deleted_at) = '')"]
    params: list[int | str] = []
    if semester:
        conditions.append("c.semester = ?")
        params.append(semester)
    if course_id is not None:
        conditions.append("c.id = ?")
        params.append(course_id)
    if class_id is not None:
        conditions.append("tc.id = ?")
        params.append(class_id)
    where_clause = f"WHERE {' AND '.join(conditions)}"

    rows = fetch_all(
        f"""
        WITH active_links AS (
            SELECT course_id, class_id
            FROM course_class_links
            WHERE deleted_at IS NULL OR TRIM(deleted_at) = ''
            UNION
            SELECT course_id, class_id
            FROM grading_tasks
        ),
        task_stats AS (
            SELECT
                gt.course_id,
                gt.class_id,
                COUNT(*) AS task_count,
                SUM(CASE WHEN gt.status = ? THEN 1 ELSE 0 END) AS active_task_count,
                SUM(CASE WHEN gt.status = ? THEN 1 ELSE 0 END) AS ended_task_count,
                SUM(CASE WHEN gt.status = ? THEN 1 ELSE 0 END) AS archived_task_count,
                MAX(gt.updated_at) AS latest_task_updated_at
            FROM grading_tasks gt
            GROUP BY gt.course_id, gt.class_id
        ),
        submission_stats AS (
            SELECT
                gt.course_id,
                gt.class_id,
                COUNT(s.id) AS submission_count
            FROM grading_tasks gt
            LEFT JOIN submissions s ON COALESCE(s.task_id, s.grading_task_id) = gt.id
            GROUP BY gt.course_id, gt.class_id
        ),
        course_roster_stats AS (
            SELECT
                course_id,
                class_id,
                COUNT(*) AS course_student_count
            FROM students
            GROUP BY course_id, class_id
        ),
        class_roster_stats AS (
            SELECT
                class_id,
                COUNT(*) AS class_student_count
            FROM class_students
            GROUP BY class_id
        )
        SELECT
            c.id AS course_id,
            c.course_name,
            c.semester,
            tc.id AS class_id,
            tc.class_name,
            COALESCE(crs.course_student_count, 0) AS course_student_count,
            COALESCE(cls.class_student_count, 0) AS class_student_count,
            COALESCE(ts.task_count, 0) AS task_count,
            COALESCE(ts.active_task_count, 0) AS active_task_count,
            COALESCE(ts.ended_task_count, 0) AS ended_task_count,
            COALESCE(ts.archived_task_count, 0) AS archived_task_count,
            COALESCE(ss.submission_count, 0) AS submission_count,
            ts.latest_task_updated_at
        FROM active_links link
        JOIN courses c ON c.id = link.course_id
        JOIN teaching_classes tc ON tc.id = link.class_id
        LEFT JOIN task_stats ts ON ts.course_id = c.id AND ts.class_id = tc.id
        LEFT JOIN submission_stats ss ON ss.course_id = c.id AND ss.class_id = tc.id
        LEFT JOIN course_roster_stats crs ON crs.course_id = c.id AND crs.class_id = tc.id
        LEFT JOIN class_roster_stats cls ON cls.class_id = tc.id
        {where_clause}
        ORDER BY c.semester DESC, c.course_name ASC, tc.class_name ASC
        """,
        (TASK_ACTIVE, TASK_ENDED, TASK_ARCHIVED, *params),
    )
    return [_normalize_archive_unit(row) for row in rows]


def archive_course_class(course_id: int, class_id: int) -> dict:
    """Archive all active/ended grading tasks under one course-class unit."""
    return _update_course_class_task_status(
        course_id=course_id,
        class_id=class_id,
        target_status=TASK_ARCHIVED,
        source_statuses=(TASK_ACTIVE, TASK_ENDED),
    )


def restore_course_class(course_id: int, class_id: int) -> dict:
    """Restore archived grading tasks under one course-class unit to active."""
    return _update_course_class_task_status(
        course_id=course_id,
        class_id=class_id,
        target_status=TASK_ACTIVE,
        source_statuses=(TASK_ARCHIVED,),
    )


def _update_course_class_task_status(
    course_id: int,
    class_id: int,
    target_status: str,
    source_statuses: tuple[str, ...],
) -> dict:
    placeholders = ",".join("?" for _ in source_statuses)
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            UPDATE grading_tasks
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE course_id = ?
              AND class_id = ?
              AND status IN ({placeholders})
            """,
            (target_status, course_id, class_id, *source_statuses),
        )
        conn.commit()
        changed = int(cursor.rowcount or 0)
    return {"updated_count": changed, "target_status": target_status}


def _normalize_archive_unit(row: dict) -> dict:
    data = dict(row)
    data["latest_task_updated_at"] = sqlite_utc_to_local_text(data.get("latest_task_updated_at")) or data.get("latest_task_updated_at")
    data["task_count"] = int(data.get("task_count") or 0)
    data["active_task_count"] = int(data.get("active_task_count") or 0)
    data["ended_task_count"] = int(data.get("ended_task_count") or 0)
    data["archived_task_count"] = int(data.get("archived_task_count") or 0)
    data["submission_count"] = int(data.get("submission_count") or 0)
    data["course_student_count"] = int(data.get("course_student_count") or 0)
    data["class_student_count"] = int(data.get("class_student_count") or 0)
    data["archive_state"] = _archive_state(data)
    return data


def _archive_state(data: dict) -> str:
    if data["task_count"] <= 0:
        return "暂无批改任务"
    if data["archived_task_count"] == data["task_count"]:
        return "已归档"
    if data["archived_task_count"] > 0:
        return "部分归档"
    return "未归档"
