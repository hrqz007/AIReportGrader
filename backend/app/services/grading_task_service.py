from __future__ import annotations

from app.db.database import execute, fetch_all, fetch_one, sqlite_utc_to_local_text

TASK_ACTIVE = "进行中"
TASK_ENDED = "已结束"
TASK_ARCHIVED = "已归档"
TASK_STATUSES = {TASK_ACTIVE, TASK_ENDED, TASK_ARCHIVED}


def _required(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def create_grading_task(
    task_name: str,
    course_id: int,
    class_id: int,
    experiment_id: int,
    description: str | None = None,
) -> int:
    _normalize_existing_task_statuses()
    task_name = _required(task_name, "批改任务名称")
    return execute(
        """
        INSERT INTO grading_tasks (
            task_name, title, course_id, class_id, experiment_id, description, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task_name, task_name, course_id, class_id, experiment_id, _optional(description), TASK_ACTIVE),
    )


def list_grading_tasks(
    course_id: int | None = None,
    class_id: int | None = None,
    experiment_id: int | None = None,
    include_ended: bool = False,
    status: str | None = None,
) -> list[dict]:
    _normalize_existing_task_statuses()
    conditions = []
    params: list[int | str] = []
    status_text = _normalize_status(status) if status else None
    if status_text:
        conditions.append("COALESCE(gt.status, ?) = ?")
        params.extend([TASK_ACTIVE, status_text])
    elif not include_ended:
        conditions.append("COALESCE(gt.status, ?) = ?")
        params.extend([TASK_ACTIVE, TASK_ACTIVE])
    if course_id is not None:
        conditions.append("gt.course_id = ?")
        params.append(course_id)
    if class_id is not None:
        conditions.append("gt.class_id = ?")
        params.append(class_id)
    if experiment_id is not None:
        conditions.append("gt.experiment_id = ?")
        params.append(experiment_id)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = fetch_all(
        f"""
        SELECT
            gt.*,
            c.course_name,
            c.semester AS course_semester,
            tc.class_name,
            e.experiment_name
        FROM grading_tasks gt
        JOIN courses c ON c.id = gt.course_id
        JOIN teaching_classes tc ON tc.id = gt.class_id
        JOIN experiments e ON e.id = gt.experiment_id
        {where_clause}
        ORDER BY gt.created_at DESC, gt.id DESC
        """,
        tuple(params),
    )
    return [_normalize_task(row) for row in rows]


def get_grading_task(task_id: int) -> dict | None:
    row = fetch_one(
        """
        SELECT
            gt.*,
            c.course_name,
            c.semester AS course_semester,
            tc.class_name,
            e.experiment_name
        FROM grading_tasks gt
        JOIN courses c ON c.id = gt.course_id
        JOIN teaching_classes tc ON tc.id = gt.class_id
        JOIN experiments e ON e.id = gt.experiment_id
        WHERE gt.id = ?
        """,
        (task_id,),
    )
    return _normalize_task(row) if row else None


def update_grading_task(task_id: int, task_name: str, description: str | None = None, status: str = TASK_ACTIVE) -> None:
    if get_grading_task(task_id) is None:
        raise ValueError("未找到批改任务。")
    task_name = _required(task_name, "批改任务名称")
    execute(
        """
        UPDATE grading_tasks
        SET task_name = ?,
            title = ?,
            description = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (task_name, task_name, _optional(description), _normalize_status(status), task_id),
    )


def delete_grading_task(task_id: int) -> None:
    if get_grading_task(task_id) is None:
        raise ValueError("未找到批改任务。")
    execute("DELETE FROM grading_tasks WHERE id = ?", (task_id,))


def count_task_submissions(task_id: int) -> int:
    row = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM submissions
        WHERE COALESCE(task_id, grading_task_id) = ?
        """,
        (task_id,),
    )
    return int(row["count"] or 0)


def _normalize_task(row: dict) -> dict:
    data = dict(row)
    data["task_name"] = data.get("task_name") or data.get("title") or ""
    data["status"] = _normalize_status(data.get("status"))
    data["created_at"] = sqlite_utc_to_local_text(data.get("created_at")) or data.get("created_at")
    data["updated_at"] = sqlite_utc_to_local_text(data.get("updated_at")) or data.get("updated_at")
    return data


def _normalize_status(value: str | None) -> str:
    text = (value or "").strip()
    if not text or text == "草稿":
        return TASK_ACTIVE
    if text not in TASK_STATUSES:
        return TASK_ACTIVE
    return text


def _normalize_existing_task_statuses() -> None:
    execute(
        """
        UPDATE grading_tasks
        SET status = ?
        WHERE status IS NULL
           OR TRIM(status) = ''
           OR status = '草稿'
        """,
        (TASK_ACTIVE,),
    )
