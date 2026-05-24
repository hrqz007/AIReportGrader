from __future__ import annotations

from app.db.database import execute, fetch_all, fetch_one, get_connection, init_db
from app.services.student_service import sync_course_roster_from_class


def _required(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def list_classes(course_id: int | None = None) -> list[dict]:
    if course_id is None:
        return fetch_all(
            """
            SELECT tc.*,
                   GROUP_CONCAT(DISTINCT c.course_name || ' / ' || COALESCE(NULLIF(c.semester, ''), '未填写学期')) AS linked_course_names
            FROM teaching_classes tc
            LEFT JOIN course_class_links link
                ON link.class_id = tc.id
               AND (link.deleted_at IS NULL OR TRIM(link.deleted_at) = '')
            LEFT JOIN courses c
                ON c.id = link.course_id
               AND (c.deleted_at IS NULL OR TRIM(c.deleted_at) = '')
            GROUP BY tc.id
            ORDER BY tc.created_at DESC, tc.id DESC
            """
        )
    return fetch_all(
        """
        SELECT tc.*,
               GROUP_CONCAT(DISTINCT c.course_name || ' / ' || COALESCE(NULLIF(c.semester, ''), '未填写学期')) AS linked_course_names
        FROM teaching_classes tc
        JOIN course_class_links link
            ON link.class_id = tc.id
           AND link.course_id = ?
           AND (link.deleted_at IS NULL OR TRIM(link.deleted_at) = '')
        LEFT JOIN courses c
            ON c.id = link.course_id
        GROUP BY tc.id
        ORDER BY tc.created_at DESC, tc.id DESC
        """,
        (course_id,),
    )


def get_class(class_id: int) -> dict | None:
    return fetch_one("SELECT * FROM teaching_classes WHERE id = ?", (class_id,))


def create_class(class_name: str, description: str | None = None, course_id: int | None = None) -> int:
    class_name = _required(class_name, "班级名称")
    class_id = execute(
        """
        INSERT INTO teaching_classes (course_id, name, class_name, description)
        VALUES (?, ?, ?, ?)
        """,
        (course_id, class_name, class_name, _optional(description)),
    )
    if course_id is not None:
        link_class_to_course(class_id, course_id)
    return class_id


def update_class(class_id: int, class_name: str, description: str | None = None) -> None:
    if get_class(class_id) is None:
        raise ValueError("未找到教学班。")
    class_name = _required(class_name, "班级名称")
    execute(
        """
        UPDATE teaching_classes
        SET name = ?,
            class_name = ?,
            description = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (class_name, class_name, _optional(description), class_id),
    )
    execute(
        """
        UPDATE class_students
        SET class_name = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE class_id = ?
        """,
        (class_name, class_id),
    )


def delete_class(class_id: int) -> None:
    if get_class(class_id) is None:
        raise ValueError("未找到教学班。")
    deps = count_class_dependencies(class_id)
    blocking = []
    if deps["class_students"] > 0:
        blocking.append(f"班级基础名单 {deps['class_students']} 人")
    if deps["course_students"] > 0:
        blocking.append(f"课程名单副本 {deps['course_students']} 人")
    if deps["grading_tasks"] > 0:
        blocking.append(f"批改任务 {deps['grading_tasks']} 个")
    if deps["submissions"] > 0:
        blocking.append(f"提交记录 {deps['submissions']} 条")
    if deps["course_links"] > 0:
        blocking.append(f"课程关联 {deps['course_links']} 个")
    if blocking:
        raise ValueError("该教学班已有后续数据，不能直接删除：" + "、".join(blocking) + "。如需停用，请先取消课程关联或归档相关数据。")
    execute("DELETE FROM teaching_classes WHERE id = ?", (class_id,))


def count_class_dependencies(class_id: int) -> dict:
    class_students = fetch_one("SELECT COUNT(*) AS count FROM class_students WHERE class_id = ?", (class_id,))
    course_students = fetch_one("SELECT COUNT(*) AS count FROM students WHERE class_id = ?", (class_id,))
    course_links = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM course_class_links
        WHERE class_id = ?
          AND (deleted_at IS NULL OR TRIM(deleted_at) = '')
        """,
        (class_id,),
    )
    grading_tasks = fetch_one("SELECT COUNT(*) AS count FROM grading_tasks WHERE class_id = ?", (class_id,))
    submissions = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM submissions s
        JOIN grading_tasks gt ON gt.id = COALESCE(s.task_id, s.grading_task_id)
        WHERE gt.class_id = ?
        """,
        (class_id,),
    )
    return {
        "class_students": int((class_students or {}).get("count") or 0),
        "course_students": int((course_students or {}).get("count") or 0),
        "course_links": int((course_links or {}).get("count") or 0),
        "grading_tasks": int((grading_tasks or {}).get("count") or 0),
        "submissions": int((submissions or {}).get("count") or 0),
    }


def link_class_to_course(class_id: int, course_id: int) -> None:
    init_db()
    if get_class(class_id) is None:
        raise ValueError("未找到教学班。")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO course_class_links (course_id, class_id)
            VALUES (?, ?)
            """,
            (course_id, class_id),
        )
        conn.execute(
            """
            UPDATE course_class_links
            SET deleted_at = NULL
            WHERE course_id = ? AND class_id = ?
            """,
            (course_id, class_id),
        )
        conn.execute(
            """
            UPDATE teaching_classes
            SET course_id = COALESCE(course_id, ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (course_id, class_id),
        )
        conn.commit()
    sync_course_roster_from_class(class_id, course_id)


def unlink_class_from_course(class_id: int, course_id: int) -> None:
    execute(
        """
        UPDATE course_class_links
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE class_id = ? AND course_id = ?
        """,
        (class_id, course_id),
    )
