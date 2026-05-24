from __future__ import annotations

from app.db.database import execute, fetch_all, fetch_one, get_connection


def _required(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def list_experiments(course_id: int | None = None) -> list[dict]:
    if course_id is None:
        return fetch_all(
            """
            SELECT e.*, c.course_name, c.semester,
                   COALESCE(rc.rubric_count, 0) AS rubric_count,
                   COALESCE(rc.rubric_total_score, 0) AS rubric_total_score
            FROM experiments e
            LEFT JOIN courses c ON c.id = e.course_id
            LEFT JOIN (
                SELECT experiment_id, COUNT(*) AS rubric_count, COALESCE(SUM(max_score), 0) AS rubric_total_score
                FROM rubric_items
                GROUP BY experiment_id
            ) rc ON rc.experiment_id = e.id
            ORDER BY e.created_at DESC, e.id DESC
            """
        )
    return fetch_all(
        """
        SELECT e.*, c.course_name, c.semester,
               COALESCE(rc.rubric_count, 0) AS rubric_count,
               COALESCE(rc.rubric_total_score, 0) AS rubric_total_score
        FROM experiments e
        LEFT JOIN courses c ON c.id = e.course_id
        LEFT JOIN (
            SELECT experiment_id, COUNT(*) AS rubric_count, COALESCE(SUM(max_score), 0) AS rubric_total_score
            FROM rubric_items
            GROUP BY experiment_id
        ) rc ON rc.experiment_id = e.id
        WHERE e.course_id = ?
        ORDER BY e.created_at DESC, e.id DESC
        """,
        (course_id,),
    )


def get_experiment(experiment_id: int) -> dict | None:
    return fetch_one("SELECT * FROM experiments WHERE id = ?", (experiment_id,))


def create_experiment(
    course_id: int,
    experiment_name: str,
    experiment_objectives: str | None = None,
    experiment_requirements: str | None = None,
    required_screenshots: str | None = None,
    key_evaluation_points: str | None = None,
    common_errors: str | None = None,
    special_notes: str | None = None,
) -> int:
    experiment_name = _required(experiment_name, "实验任务名称")
    objectives = _optional(experiment_objectives)
    requirements = _optional(experiment_requirements)
    return execute(
        """
        INSERT INTO experiments (
            course_id, title, experiment_name, description, requirements,
            experiment_objectives, experiment_requirements, required_screenshots,
            key_evaluation_points, common_errors, special_notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            course_id,
            experiment_name,
            experiment_name,
            objectives,
            requirements,
            objectives,
            requirements,
            _optional(required_screenshots),
            _optional(key_evaluation_points),
            _optional(common_errors),
            _optional(special_notes),
        ),
    )


def update_experiment(
    experiment_id: int,
    experiment_name: str,
    experiment_objectives: str | None = None,
    experiment_requirements: str | None = None,
    required_screenshots: str | None = None,
    key_evaluation_points: str | None = None,
    common_errors: str | None = None,
    special_notes: str | None = None,
) -> None:
    if get_experiment(experiment_id) is None:
        raise ValueError("未找到实验任务。")
    experiment_name = _required(experiment_name, "实验任务名称")
    objectives = _optional(experiment_objectives)
    requirements = _optional(experiment_requirements)
    execute(
        """
        UPDATE experiments
        SET title = ?,
            experiment_name = ?,
            description = ?,
            requirements = ?,
            experiment_objectives = ?,
            experiment_requirements = ?,
            required_screenshots = ?,
            key_evaluation_points = ?,
            common_errors = ?,
            special_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            experiment_name,
            experiment_name,
            objectives,
            requirements,
            objectives,
            requirements,
            _optional(required_screenshots),
            _optional(key_evaluation_points),
            _optional(common_errors),
            _optional(special_notes),
            experiment_id,
        ),
    )


def delete_experiment(experiment_id: int) -> None:
    if get_experiment(experiment_id) is None:
        raise ValueError("未找到实验任务。")
    deps = count_experiment_dependencies(experiment_id)
    blocking = []
    if deps["grading_tasks"] > 0:
        blocking.append(f"批改任务 {deps['grading_tasks']} 个")
    if deps["submissions"] > 0:
        blocking.append(f"提交记录 {deps['submissions']} 条")
    if deps["rubric_items"] > 0:
        blocking.append(f"评分标准 {deps['rubric_items']} 项")
    if blocking:
        raise ValueError("该实验任务已有后续数据，不能直接删除：" + "、".join(blocking) + "。")
    execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))


def count_experiment_dependencies(experiment_id: int) -> dict:
    rubric_count = fetch_one("SELECT COUNT(*) AS count FROM rubric_items WHERE experiment_id = ?", (experiment_id,))["count"]
    task_count = 0
    submission_count = 0
    try:
        task_count = fetch_one("SELECT COUNT(*) AS count FROM grading_tasks WHERE experiment_id = ?", (experiment_id,))["count"]
        submission_count = fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM submissions s
            JOIN grading_tasks gt ON gt.id = COALESCE(s.task_id, s.grading_task_id)
            WHERE gt.experiment_id = ?
            """,
            (experiment_id,),
        )["count"]
    except Exception:
        task_count = 0
        submission_count = 0
    return {
        "rubric_items": int(rubric_count or 0),
        "grading_tasks": int(task_count or 0),
        "submissions": int(submission_count or 0),
    }


def clone_experiment_with_rubrics(source_experiment_id: int, target_course_id: int, experiment_name: str | None = None) -> dict:
    source = get_experiment(source_experiment_id)
    if source is None:
        raise ValueError("未找到要复用的历史实验任务。")
    source_course = fetch_one("SELECT * FROM courses WHERE id = ?", (source.get("course_id"),))
    target_course = fetch_one("SELECT * FROM courses WHERE id = ?", (target_course_id,))
    if target_course is None:
        raise ValueError("未找到目标课程。")

    source_name = _required(source.get("experiment_name") or source.get("title"), "实验任务名称")
    new_name = _optional(experiment_name) or source_name
    existing = fetch_one(
        "SELECT id FROM experiments WHERE course_id = ? AND TRIM(experiment_name) = TRIM(?)",
        (target_course_id, new_name),
    )
    if existing:
        raise ValueError("当前课程下已存在同名实验任务，请修改复制后的实验名称。")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO experiments (
                course_id, title, experiment_name, description, requirements,
                experiment_objectives, experiment_requirements, required_screenshots,
                key_evaluation_points, common_errors, special_notes,
                source_experiment_id, source_course_id, copied_from_semester
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_course_id,
                new_name,
                new_name,
                source.get("description"),
                source.get("requirements"),
                source.get("experiment_objectives"),
                source.get("experiment_requirements"),
                source.get("required_screenshots"),
                source.get("key_evaluation_points"),
                source.get("common_errors"),
                source.get("special_notes"),
                source_experiment_id,
                source.get("course_id"),
                source_course.get("semester") if source_course else None,
            ),
        )
        new_experiment_id = int(cursor.lastrowid)

        rubric_rows = conn.execute(
            """
            SELECT *
            FROM rubric_items
            WHERE experiment_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (source_experiment_id,),
        ).fetchall()
        copied_rubrics = 0
        for row in rubric_rows:
            conn.execute(
                """
                INSERT INTO rubric_items (
                    experiment_id, item_name, item_description, description, deduction_rules,
                    max_score, requires_review, sort_order, source_rubric_item_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_experiment_id,
                    row["item_name"],
                    row["item_description"],
                    row["description"],
                    row["deduction_rules"],
                    row["max_score"],
                    row["requires_review"],
                    row["sort_order"],
                    row["id"],
                ),
            )
            copied_rubrics += 1
        conn.commit()

    return {
        "id": new_experiment_id,
        "experiment_name": new_name,
        "copied_rubric_items": copied_rubrics,
        "source_experiment_id": source_experiment_id,
        "target_course_id": target_course_id,
    }
