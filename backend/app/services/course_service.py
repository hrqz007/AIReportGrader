from __future__ import annotations

import re

from app.db.database import execute, fetch_all, fetch_one


def _required(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _semester(value: str | None) -> str:
    text = (value or "").strip().replace(" ", "").replace("　", "").replace("—", "-").replace("–", "-")
    if not text:
        raise ValueError("学期不能为空，请选择如 2025-2026第一学期 的规范格式。")
    match = re.fullmatch(r"(\d{4})-(\d{4})(?:第)?([一二12])学期", text)
    if not match:
        raise ValueError("学期格式不规范，请使用如 2025-2026第一学期 或 2025-2026第二学期 的格式。")
    start_year = int(match.group(1))
    end_year = int(match.group(2))
    if end_year != start_year + 1:
        raise ValueError("学期年份不连续，请使用如 2025-2026第一学期 的格式。")
    term = "第一学期" if match.group(3) in {"一", "1"} else "第二学期"
    return f"{start_year}-{end_year}{term}"


def list_courses() -> list[dict]:
    return fetch_all(
        """
        SELECT *
        FROM courses
        WHERE deleted_at IS NULL OR TRIM(deleted_at) = ''
        ORDER BY created_at DESC, id DESC
        """
    )


def get_course(course_id: int) -> dict | None:
    return fetch_one("SELECT * FROM courses WHERE id = ?", (course_id,))


def create_course(course_name: str, course_type: str, semester: str | None, description: str | None) -> int:
    course_name = _required(course_name, "课程名称")
    course_type = _optional(course_type) or "理论+实验课程"
    semester_text = _semester(semester)
    return execute(
        """
        INSERT INTO courses (name, course_name, course_type, semester, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (course_name, course_name, course_type, semester_text, _optional(description)),
    )


def update_course(course_id: int, course_name: str, course_type: str, semester: str | None, description: str | None) -> None:
    if get_course(course_id) is None:
        raise ValueError("未找到课程。")
    course_name = _required(course_name, "课程名称")
    course_type = _optional(course_type) or "理论+实验课程"
    semester_text = _semester(semester)
    execute(
        """
        UPDATE courses
        SET name = ?,
            course_name = ?,
            course_type = ?,
            semester = ?,
            description = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (course_name, course_name, course_type, semester_text, _optional(description), course_id),
    )


def delete_course(course_id: int) -> None:
    if get_course(course_id) is None:
        raise ValueError("未找到课程。")
    deps = count_course_dependencies(course_id)
    blocking = []
    if deps["course_links"] > 0:
        blocking.append(f"教学班关联 {deps['course_links']} 个")
    if deps["course_students"] > 0:
        blocking.append(f"课程名单学生 {deps['course_students']} 人")
    if deps["experiments"] > 0:
        blocking.append(f"实验任务 {deps['experiments']} 个")
    if deps["grading_tasks"] > 0:
        blocking.append(f"批改任务 {deps['grading_tasks']} 个")
    if deps["submissions"] > 0:
        blocking.append(f"提交记录 {deps['submissions']} 条")
    if blocking:
        raise ValueError("该课程已有后续数据，不能直接删除：" + "、".join(blocking) + "。如课程已结束，请在归档页面归档相关批改任务。")
    execute(
        """
        UPDATE courses
        SET deleted_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (course_id,),
    )


def count_course_dependencies(course_id: int) -> dict:
    course_links = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM course_class_links
        WHERE course_id = ?
          AND (deleted_at IS NULL OR TRIM(deleted_at) = '')
        """,
        (course_id,),
    )
    course_students = fetch_one("SELECT COUNT(*) AS count FROM students WHERE course_id = ?", (course_id,))
    experiments = fetch_one("SELECT COUNT(*) AS count FROM experiments WHERE course_id = ?", (course_id,))
    grading_tasks = fetch_one("SELECT COUNT(*) AS count FROM grading_tasks WHERE course_id = ?", (course_id,))
    submissions = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM submissions s
        JOIN grading_tasks gt ON gt.id = COALESCE(s.task_id, s.grading_task_id)
        WHERE gt.course_id = ?
        """,
        (course_id,),
    )
    return {
        "course_links": int((course_links or {}).get("count") or 0),
        "course_students": int((course_students or {}).get("count") or 0),
        "experiments": int((experiments or {}).get("count") or 0),
        "grading_tasks": int((grading_tasks or {}).get("count") or 0),
        "submissions": int((submissions or {}).get("count") or 0),
    }
