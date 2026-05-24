from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_ROOT, PROJECT_ROOT, UPLOADS_DIR


def is_supported_report_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in {".docx", ".doc", ".pdf"}


def task_reports_dir(task_id: int) -> Path:
    path = UPLOADS_DIR / str(task_id) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def task_images_dir(task_id: int, submission_id: int) -> Path:
    path = UPLOADS_DIR / str(task_id) / "images" / str(submission_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_stored_file_path(stored_path: str | Path | None) -> Path:
    """Resolve paths stored in SQLite after project moves or backup restore.

    Earlier versions stored absolute paths such as D:\\old\\project\\backend\\uploads\\...
    After copying the project to another directory, those paths become stale while the
    files still exist under the current backend/uploads directory. This helper keeps
    existing records usable by remapping anything after the uploads segment.
    """
    if not stored_path:
        return Path("")

    raw_path = Path(str(stored_path))
    if raw_path.exists():
        return raw_path

    candidates: list[Path] = []
    if not raw_path.is_absolute():
        candidates.extend([BACKEND_ROOT / raw_path, PROJECT_ROOT / raw_path, UPLOADS_DIR / raw_path])

    parts = list(raw_path.parts)
    lowered = [part.lower() for part in parts]
    if "uploads" in lowered:
        upload_index = lowered.index("uploads")
        tail_parts = parts[upload_index + 1 :]
        if tail_parts:
            candidates.append(UPLOADS_DIR.joinpath(*tail_parts))
    if "backend" in lowered:
        backend_index = lowered.index("backend")
        tail_parts = parts[backend_index + 1 :]
        if tail_parts:
            candidates.append(BACKEND_ROOT.joinpath(*tail_parts))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return raw_path


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    return name.strip() or "report.docx"


def save_upload_file(uploaded_file: Any, task_id: int, student_no: str | None = None) -> Path:
    prefix_parts = [uuid.uuid4().hex[:8]]
    if student_no:
        prefix_parts.insert(0, student_no)
    target = task_reports_dir(task_id) / f"{'_'.join(prefix_parts)}_{safe_filename(uploaded_file.filename or 'report.docx')}"
    with target.open("wb") as output:
        while True:
            chunk = uploaded_file.file.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    return target
