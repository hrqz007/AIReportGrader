from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import ensure_runtime_dirs, get_db_path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    course_name TEXT,
    course_type TEXT,
    semester TEXT,
    description TEXT,
    deleted_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teaching_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    name TEXT NOT NULL,
    class_name TEXT,
    semester TEXT,
    grade TEXT,
    major TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS course_class_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    deleted_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (course_id, class_id)
);

CREATE TABLE IF NOT EXISTS class_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    student_no TEXT NOT NULL,
    name TEXT NOT NULL,
    student_name TEXT,
    class_name TEXT,
    anonymous_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (class_id, student_no)
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    class_id INTEGER NOT NULL,
    student_no TEXT NOT NULL,
    name TEXT NOT NULL,
    student_name TEXT,
    class_name TEXT,
    anonymous_id TEXT,
    gender TEXT,
    major TEXT,
    raw_info TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (course_id, class_id, student_no)
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    experiment_name TEXT,
    experiment_no TEXT,
    description TEXT,
    requirements TEXT,
    experiment_objectives TEXT,
    experiment_requirements TEXT,
    required_screenshots TEXT,
    key_evaluation_points TEXT,
    common_errors TEXT,
    special_notes TEXT,
    source_experiment_id INTEGER,
    source_course_id INTEGER,
    copied_from_semester TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rubric_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    item_description TEXT,
    description TEXT,
    deduction_rules TEXT,
    max_score REAL NOT NULL,
    requires_review INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_rubric_item_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grading_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    title TEXT,
    course_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    experiment_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT '进行中',
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL,
    provider_type TEXT NOT NULL DEFAULT 'openai_compatible',
    base_url TEXT NOT NULL,
    api_key TEXT NOT NULL,
    text_model TEXT NOT NULL,
    vision_model TEXT,
    analysis_model TEXT,
    supports_vision INTEGER NOT NULL DEFAULT 0,
    supports_json INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    grading_task_id INTEGER,
    student_id INTEGER,
    student_no TEXT,
    student_name TEXT,
    anonymous_id TEXT,
    original_filename TEXT NOT NULL,
    stored_file_path TEXT NOT NULL,
    matched_student_no TEXT,
    matched_student_name TEXT,
    parsed_student_no TEXT,
    parsed_student_name TEXT,
    match_status TEXT NOT NULL DEFAULT '未匹配',
    ai_status TEXT NOT NULL DEFAULT '未初评',
    review_status TEXT NOT NULL DEFAULT '未复核',
    parse_status TEXT NOT NULL DEFAULT '未解析',
    parse_error TEXT,
    plain_text TEXT,
    anonymized_text TEXT,
    image_paths TEXT,
    detected_flags TEXT,
    parsed_at TEXT,
    ai_total_score REAL,
    ai_overall_comment TEXT,
    ai_student_feedback TEXT,
    ai_common_error_tags TEXT,
    ai_teacher_review_points TEXT,
    ai_raw_response TEXT,
    ai_error TEXT,
    ai_prompt_version TEXT,
    ai_scored_at TEXT,
    teacher_total_score REAL,
    teacher_overall_comment TEXT,
    reviewed_at TEXT,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    task_id INTEGER,
    rubric_item_id INTEGER,
    item_name TEXT,
    max_score REAL,
    ai_score REAL,
    deduction_reason TEXT,
    evidence_json TEXT,
    suggestion TEXT,
    confidence TEXT,
    need_teacher_review INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teacher_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL UNIQUE,
    task_id INTEGER,
    total_score REAL NOT NULL,
    item_scores_json TEXT,
    feedback TEXT,
    reviewer_name TEXT,
    confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    ensure_runtime_dirs()
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> Path:
    ensure_runtime_dirs()
    path = get_db_path()
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
        run_compatibility_migrations(conn)
        conn.commit()
    return path


def run_compatibility_migrations(conn: sqlite3.Connection) -> None:
    _add_column_if_missing(conn, "courses", "course_name", "TEXT")
    _add_column_if_missing(conn, "courses", "course_type", "TEXT")
    _add_column_if_missing(conn, "courses", "semester", "TEXT")
    _add_column_if_missing(conn, "courses", "deleted_at", "TEXT")
    conn.execute(
        """
        UPDATE courses
        SET course_name = COALESCE(NULLIF(TRIM(course_name), ''), name),
            course_type = COALESCE(NULLIF(TRIM(course_type), ''), '实验类课程')
        """
    )

    _add_column_if_missing(conn, "teaching_classes", "class_name", "TEXT")
    _add_column_if_missing(conn, "teaching_classes", "semester", "TEXT")
    conn.execute("UPDATE teaching_classes SET class_name = COALESCE(NULLIF(TRIM(class_name), ''), name)")

    _add_column_if_missing(conn, "course_class_links", "deleted_at", "TEXT")
    conn.execute(
        """
        INSERT OR IGNORE INTO course_class_links (course_id, class_id)
        SELECT course_id, id
        FROM teaching_classes
        WHERE course_id IS NOT NULL
        """
    )

    _add_column_if_missing(conn, "students", "course_id", "INTEGER")
    _add_column_if_missing(conn, "students", "student_name", "TEXT")
    _add_column_if_missing(conn, "students", "class_name", "TEXT")
    _add_column_if_missing(conn, "students", "anonymous_id", "TEXT")
    conn.execute("UPDATE students SET student_name = COALESCE(NULLIF(TRIM(student_name), ''), name)")

    _add_column_if_missing(conn, "experiments", "experiment_name", "TEXT")
    _add_column_if_missing(conn, "experiments", "experiment_no", "TEXT")
    _add_column_if_missing(conn, "experiments", "experiment_objectives", "TEXT")
    _add_column_if_missing(conn, "experiments", "experiment_requirements", "TEXT")
    _add_column_if_missing(conn, "experiments", "required_screenshots", "TEXT")
    _add_column_if_missing(conn, "experiments", "key_evaluation_points", "TEXT")
    _add_column_if_missing(conn, "experiments", "common_errors", "TEXT")
    _add_column_if_missing(conn, "experiments", "special_notes", "TEXT")
    _add_column_if_missing(conn, "experiments", "source_experiment_id", "INTEGER")
    _add_column_if_missing(conn, "experiments", "source_course_id", "INTEGER")
    _add_column_if_missing(conn, "experiments", "copied_from_semester", "TEXT")
    conn.execute(
        """
        UPDATE experiments
        SET experiment_name = COALESCE(NULLIF(TRIM(experiment_name), ''), title),
            experiment_objectives = COALESCE(NULLIF(TRIM(experiment_objectives), ''), description),
            experiment_requirements = COALESCE(NULLIF(TRIM(experiment_requirements), ''), requirements)
        """
    )

    _add_column_if_missing(conn, "rubric_items", "description", "TEXT")
    _add_column_if_missing(conn, "rubric_items", "deduction_rules", "TEXT")
    _add_column_if_missing(conn, "rubric_items", "requires_review", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "rubric_items", "source_rubric_item_id", "INTEGER")
    conn.execute(
        """
        UPDATE rubric_items
        SET description = COALESCE(NULLIF(TRIM(description), ''), item_description),
            requires_review = COALESCE(requires_review, 0)
        """
    )

    _add_column_if_missing(conn, "grading_tasks", "task_name", "TEXT")
    _add_column_if_missing(conn, "grading_tasks", "title", "TEXT")
    _add_column_if_missing(conn, "grading_tasks", "status", "TEXT NOT NULL DEFAULT '进行中'")
    _add_column_if_missing(conn, "grading_tasks", "description", "TEXT")
    conn.execute(
        """
        UPDATE grading_tasks
        SET task_name = COALESCE(NULLIF(TRIM(task_name), ''), title),
            title = COALESCE(NULLIF(TRIM(title), ''), task_name),
            status = COALESCE(NULLIF(TRIM(status), ''), '进行中')
        """
    )
    conn.execute(
        """
        UPDATE grading_tasks
        SET status = '进行中'
        WHERE status IS NULL
           OR TRIM(status) = ''
           OR status = '草稿'
        """
    )

    _add_column_if_missing(conn, "submissions", "task_id", "INTEGER")
    _add_column_if_missing(conn, "submissions", "grading_task_id", "INTEGER")
    _add_column_if_missing(conn, "submissions", "student_id", "INTEGER")
    _add_column_if_missing(conn, "submissions", "student_no", "TEXT")
    _add_column_if_missing(conn, "submissions", "student_name", "TEXT")
    _add_column_if_missing(conn, "submissions", "anonymous_id", "TEXT")
    _add_column_if_missing(conn, "submissions", "matched_student_no", "TEXT")
    _add_column_if_missing(conn, "submissions", "matched_student_name", "TEXT")
    _add_column_if_missing(conn, "submissions", "parsed_student_no", "TEXT")
    _add_column_if_missing(conn, "submissions", "parsed_student_name", "TEXT")
    _add_column_if_missing(conn, "submissions", "match_status", "TEXT NOT NULL DEFAULT '未匹配'")
    _add_column_if_missing(conn, "submissions", "ai_status", "TEXT NOT NULL DEFAULT '未初评'")
    _add_column_if_missing(conn, "submissions", "review_status", "TEXT NOT NULL DEFAULT '未复核'")
    _add_column_if_missing(conn, "submissions", "parse_status", "TEXT NOT NULL DEFAULT '未解析'")
    _add_column_if_missing(conn, "submissions", "parse_error", "TEXT")
    _add_column_if_missing(conn, "submissions", "plain_text", "TEXT")
    _add_column_if_missing(conn, "submissions", "anonymized_text", "TEXT")
    _add_column_if_missing(conn, "submissions", "image_paths", "TEXT")
    _add_column_if_missing(conn, "submissions", "detected_flags", "TEXT")
    _add_column_if_missing(conn, "submissions", "parsed_at", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_total_score", "REAL")
    _add_column_if_missing(conn, "submissions", "ai_overall_comment", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_student_feedback", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_common_error_tags", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_teacher_review_points", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_raw_response", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_error", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_prompt_version", "TEXT")
    _add_column_if_missing(conn, "submissions", "ai_scored_at", "TEXT")
    _add_column_if_missing(conn, "submissions", "teacher_total_score", "REAL")
    _add_column_if_missing(conn, "submissions", "teacher_overall_comment", "TEXT")
    _add_column_if_missing(conn, "submissions", "reviewed_at", "TEXT")
    conn.execute(
        """
        UPDATE submissions
        SET task_id = COALESCE(task_id, grading_task_id),
            grading_task_id = COALESCE(grading_task_id, task_id),
            matched_student_no = COALESCE(NULLIF(TRIM(matched_student_no), ''), student_no),
            matched_student_name = COALESCE(NULLIF(TRIM(matched_student_name), ''), student_name),
            match_status = COALESCE(NULLIF(TRIM(match_status), ''), '未匹配'),
            ai_status = COALESCE(NULLIF(TRIM(ai_status), ''), '未初评'),
            review_status = COALESCE(NULLIF(TRIM(review_status), ''), '未复核'),
            parse_status = COALESCE(NULLIF(TRIM(parse_status), ''), '未解析')
        """
    )

    for table_sql in (
        """
        CREATE TABLE IF NOT EXISTS ai_provider_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_name TEXT NOT NULL,
            provider_type TEXT NOT NULL DEFAULT 'openai_compatible',
            base_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            text_model TEXT NOT NULL,
            vision_model TEXT,
            analysis_model TEXT,
            supports_vision INTEGER NOT NULL DEFAULT 0,
            supports_json INTEGER NOT NULL DEFAULT 1,
            is_default INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            task_id INTEGER,
            rubric_item_id INTEGER,
            item_name TEXT,
            max_score REAL,
            ai_score REAL,
            deduction_reason TEXT,
            evidence_json TEXT,
            suggestion TEXT,
            confidence TEXT,
            need_teacher_review INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ):
        conn.execute(table_sql)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL UNIQUE,
            task_id INTEGER,
            total_score REAL NOT NULL,
            item_scores_json TEXT,
            feedback TEXT,
            reviewer_name TEXT,
            confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for column_name, column_definition in {
        "provider_name": "TEXT",
        "provider_type": "TEXT NOT NULL DEFAULT 'openai_compatible'",
        "base_url": "TEXT",
        "api_key": "TEXT",
        "text_model": "TEXT",
        "vision_model": "TEXT",
        "analysis_model": "TEXT",
        "supports_vision": "INTEGER NOT NULL DEFAULT 0",
        "supports_json": "INTEGER NOT NULL DEFAULT 1",
        "is_default": "INTEGER NOT NULL DEFAULT 0",
        "enabled": "INTEGER NOT NULL DEFAULT 1",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        _add_column_if_missing(conn, "ai_provider_configs", column_name, column_definition)

    for column_name, column_definition in {
        "submission_id": "INTEGER",
        "task_id": "INTEGER",
        "rubric_item_id": "INTEGER",
        "item_name": "TEXT",
        "max_score": "REAL",
        "ai_score": "REAL",
        "deduction_reason": "TEXT",
        "evidence_json": "TEXT",
        "suggestion": "TEXT",
        "confidence": "TEXT",
        "need_teacher_review": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        _add_column_if_missing(conn, "ai_scores", column_name, column_definition)

    for column_name, column_definition in {
        "submission_id": "INTEGER",
        "task_id": "INTEGER",
        "total_score": "REAL",
        "item_scores_json": "TEXT",
        "feedback": "TEXT",
        "reviewer_name": "TEXT",
        "confirmed_at": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        _add_column_if_missing(conn, "teacher_scores", column_name, column_definition)


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return dict(row) if row is not None else None


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def execute(query: str, params: Iterable[Any] = ()) -> int:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(params))
        conn.commit()
        return int(cursor.lastrowid or cursor.rowcount or 0)


def sqlite_utc_to_local_text(value: str | None) -> str | None:
    """Convert SQLite CURRENT_TIMESTAMP text from UTC to local display time."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return text
    normalized = text.replace("T", " ")
    if "." in normalized:
        normalized = normalized.split(".", 1)[0]
    normalized = normalized[:19]
    try:
        utc_dt = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return text
    return utc_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
