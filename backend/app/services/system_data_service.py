from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.core.config import DATA_DIR, EXPORTS_DIR, UPLOADS_DIR, ensure_runtime_dirs, get_db_path
from app.db.database import init_db


BACKUP_DIR = EXPORTS_DIR / "backups"

CORE_TABLES = [
    "teacher_scores",
    "ai_scores",
    "submissions",
    "grading_tasks",
    "rubric_items",
    "experiments",
    "students",
    "class_students",
    "course_class_links",
    "teaching_classes",
    "courses",
]

AI_CONFIG_TABLES = ["ai_provider_configs"]


def _now_text() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_dirs() -> None:
    ensure_runtime_dirs()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _display_size(size: int | float) -> str:
    size = float(size or 0)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _count_table(conn: sqlite3.Connection, table_name: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0


def _write_manifest(path: Path, backup_type: str, include_api_keys: bool, include_exports: bool) -> None:
    manifest = {
        "system_name": "实验智评 V2",
        "backup_type": backup_type,
        "include_api_keys": include_api_keys,
        "include_exports": include_exports,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "database": "data/app.db",
        "uploads": "uploads/",
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_database_to(target_db: Path, remove_api_keys: bool = False) -> None:
    init_db()
    source_db = get_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(source_db), timeout=10) as source:
        with sqlite3.connect(str(target_db), timeout=10) as target:
            source.backup(target)
            target.commit()
    if remove_api_keys:
        with sqlite3.connect(str(target_db), timeout=10) as conn:
            conn.execute("UPDATE ai_provider_configs SET api_key = ''")
            conn.commit()


def _add_path_to_zip(zip_file: zipfile.ZipFile, source: Path, arc_root: str) -> None:
    if not source.exists():
        return
    if source.is_file():
        zip_file.write(source, arc_root)
        return
    for item in source.rglob("*"):
        if item.is_file():
            arc_name = str(Path(arc_root) / item.relative_to(source)).replace("\\", "/")
            zip_file.write(item, arc_name)


def create_system_backup(*, include_api_keys: bool = True, include_exports: bool = False, label: str | None = None) -> Path:
    _ensure_dirs()
    timestamp = _now_text()
    backup_type = "full" if include_api_keys else "demo"
    safe_label = f"_{label}" if label else ""
    zip_path = BACKUP_DIR / f"实验智评V2_系统数据备份_{backup_type}{safe_label}_{timestamp}.zip"

    with tempfile.TemporaryDirectory(prefix="aigrader_v2_backup_", ignore_cleanup_errors=True) as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        data_dir = tmp_dir / "data"
        uploads_dir = tmp_dir / "uploads"
        exports_dir = tmp_dir / "exports"

        _copy_database_to(data_dir / "app.db", remove_api_keys=not include_api_keys)
        if UPLOADS_DIR.exists():
            shutil.copytree(UPLOADS_DIR, uploads_dir, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            uploads_dir.mkdir(parents=True, exist_ok=True)
        if include_exports and EXPORTS_DIR.exists():
            shutil.copytree(EXPORTS_DIR, exports_dir, ignore=shutil.ignore_patterns("backups", "__pycache__"))
        manifest_path = tmp_dir / "backup_manifest.json"
        _write_manifest(manifest_path, backup_type, include_api_keys, include_exports)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            _add_path_to_zip(zip_file, data_dir / "app.db", "data/app.db")
            _add_path_to_zip(zip_file, uploads_dir, "uploads")
            if include_exports:
                _add_path_to_zip(zip_file, exports_dir, "exports")
            _add_path_to_zip(zip_file, manifest_path, "backup_manifest.json")

    return zip_path


def validate_backup_zip(zip_path: Path | str) -> dict:
    zip_path = Path(zip_path)
    result = {"ok": False, "message": "", "entries": 0, "manifest": None}
    if not zip_path.exists():
        result["message"] = "备份文件不存在。"
        return result
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            names = zip_file.namelist()
            result["entries"] = len(names)
            if "data/app.db" not in names:
                result["message"] = "备份包中缺少 data/app.db，不能恢复。"
                return result
            if "backup_manifest.json" in names:
                with zip_file.open("backup_manifest.json") as file:
                    result["manifest"] = json.loads(file.read().decode("utf-8"))
            result["ok"] = True
            result["message"] = "备份包校验通过。"
            return result
    except Exception as exc:
        result["message"] = f"备份包读取失败：{exc}"
        return result


def _safe_extract(zip_file: zipfile.ZipFile, destination: Path, allowed_roots: Iterable[str]) -> None:
    destination = destination.resolve()
    allowed_roots = tuple(root.rstrip("/") + "/" for root in allowed_roots)
    for member in zip_file.infolist():
        name = member.filename.replace("\\", "/")
        if name.endswith("/") or name == "backup_manifest.json":
            continue
        if not any(name.startswith(root) for root in allowed_roots):
            continue
        target = (destination / name).resolve()
        if not str(target).startswith(str(destination)):
            raise ValueError(f"备份包包含不安全路径：{name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(member) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


def restore_system_backup(zip_path: Path | str) -> dict:
    zip_path = Path(zip_path)
    validation = validate_backup_zip(zip_path)
    if not validation["ok"]:
        return {"ok": False, "message": validation["message"], "safety_backup": ""}

    _ensure_dirs()
    safety_backup = create_system_backup(include_api_keys=True, include_exports=False, label="before_restore")
    try:
        with tempfile.TemporaryDirectory(prefix="aigrader_v2_restore_", ignore_cleanup_errors=True) as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                _safe_extract(zip_file, tmp_dir, allowed_roots=["data", "uploads", "exports"])

            restored_db = tmp_dir / "data" / "app.db"
            if not restored_db.exists():
                return {"ok": False, "message": "恢复失败：备份包中没有数据库文件。", "safety_backup": str(safety_backup)}

            with sqlite3.connect(str(restored_db), timeout=10) as source:
                with sqlite3.connect(str(get_db_path()), timeout=10) as target:
                    source.backup(target)
                    target.commit()

            restored_uploads = tmp_dir / "uploads"
            if UPLOADS_DIR.exists():
                shutil.rmtree(UPLOADS_DIR)
            if restored_uploads.exists():
                shutil.copytree(restored_uploads, UPLOADS_DIR)
            else:
                UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        init_db()
        return {
            "ok": True,
            "message": "数据恢复完成。建议刷新页面，或重启系统后继续使用。",
            "safety_backup": str(safety_backup),
        }
    except Exception as exc:
        return {"ok": False, "message": f"恢复失败：{exc}", "safety_backup": str(safety_backup)}


def _delete_table_rows(conn: sqlite3.Connection, tables: Iterable[str]) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.Error:
            pass
    for table in tables:
        try:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        except sqlite3.Error:
            pass
    conn.execute("PRAGMA foreign_keys = ON")


def _clear_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def clear_grading_data() -> dict:
    _ensure_dirs()
    safety_backup = create_system_backup(include_api_keys=True, include_exports=False, label="before_clear_grading")
    init_db()
    with sqlite3.connect(str(get_db_path()), timeout=10) as conn:
        _delete_table_rows(conn, ["teacher_scores", "ai_scores", "submissions", "grading_tasks"])
        conn.commit()
    _clear_directory(UPLOADS_DIR)
    return {
        "ok": True,
        "message": "已清空批改任务、报告提交、AI 初评和教师复核数据；课程、教学班、学生名单、实验任务和评分标准已保留。",
        "safety_backup": str(safety_backup),
    }


def clear_business_data(*, include_ai_configs: bool = False) -> dict:
    _ensure_dirs()
    label = "before_reset_all" if include_ai_configs else "before_clear_business"
    safety_backup = create_system_backup(include_api_keys=True, include_exports=False, label=label)
    init_db()
    tables = list(CORE_TABLES)
    if include_ai_configs:
        tables = AI_CONFIG_TABLES + tables
    with sqlite3.connect(str(get_db_path()), timeout=10) as conn:
        _delete_table_rows(conn, tables)
        conn.commit()
    _clear_directory(UPLOADS_DIR)
    return {
        "ok": True,
        "message": "已完成系统数据清理。清理前已自动生成安全备份。",
        "safety_backup": str(safety_backup),
    }


def get_system_overview() -> dict:
    _ensure_dirs()
    init_db()
    db_path = get_db_path()
    with sqlite3.connect(str(db_path), timeout=10) as conn:
        counts = {
            "courses": _count_table(conn, "courses"),
            "classes": _count_table(conn, "teaching_classes"),
            "class_students": _count_table(conn, "class_students"),
            "course_students": _count_table(conn, "students"),
            "experiments": _count_table(conn, "experiments"),
            "rubric_items": _count_table(conn, "rubric_items"),
            "grading_tasks": _count_table(conn, "grading_tasks"),
            "submissions": _count_table(conn, "submissions"),
            "ai_scores": _count_table(conn, "ai_scores"),
            "teacher_scores": _count_table(conn, "teacher_scores"),
            "ai_configs": _count_table(conn, "ai_provider_configs"),
        }
    db_size = db_path.stat().st_size if db_path.exists() else 0
    uploads_size = _dir_size(UPLOADS_DIR)
    exports_size = _dir_size(EXPORTS_DIR)
    backup_size = _dir_size(BACKUP_DIR)
    return {
        "counts": counts,
        "db_path": str(db_path),
        "db_size": db_size,
        "db_size_text": _display_size(db_size),
        "uploads_size": uploads_size,
        "uploads_size_text": _display_size(uploads_size),
        "exports_size": exports_size,
        "exports_size_text": _display_size(exports_size),
        "backup_size": backup_size,
        "backup_size_text": _display_size(backup_size),
    }


def save_uploaded_backup(data: bytes) -> Path:
    _ensure_dirs()
    target = BACKUP_DIR / f"uploaded_restore_{_now_text()}.zip"
    target.write_bytes(data)
    return target
