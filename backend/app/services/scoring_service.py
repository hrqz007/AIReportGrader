from __future__ import annotations

import json
from typing import Any

from app.db.database import execute, fetch_all, fetch_one, get_connection
from app.services.ai_client import chat_completion_stream, encode_image_to_data_url, kimi_fast_extra_body
from app.services.ai_provider_service import get_default_config, test_config
from app.services.file_service import resolve_stored_file_path
from app.utils.json_utils import extract_json_from_text, validate_and_normalize_ai_score

MATCHED = "已匹配"
NAME_MISMATCH = "姓名不一致"
PARSE_DONE = "解析完成"
AI_NOT_STARTED = "未初评"
AI_RUNNING = "初评中"
AI_DONE = "初评完成"
AI_FAILED = "初评失败"
MAX_TEXT_CHARS = 6000
MAX_OUTPUT_TOKENS = 2048
DEFAULT_VISION_IMAGES = 3
PROMPT_TEMPLATE_VERSION = "scoring_prompt_v2.2"


def build_scoring_prompt(
    course: dict,
    experiment: dict,
    rubric_items: list[dict],
    anonymized_text: str,
    detected_flags: dict,
    image_infos: list[dict],
    use_vision: bool = False,
    sent_image_count: int = 0,
) -> list[dict]:
    rubric_payload = [
        {
            "rubric_item_id": int(item["id"]),
            "item_name": item.get("item_name") or "",
            "max_score": float(item.get("max_score") or 0),
            "description": _truncate(item.get("description") or item.get("item_description"), 200),
            "deduction_rules": _truncate(item.get("deduction_rules"), 300),
            "requires_review": bool(int(item.get("requires_review") or 0)),
            "sort_order": int(item.get("sort_order") or 0),
        }
        for item in rubric_items
    ]
    output_schema = {
        "rubric_scores": [
            {
                "rubric_item_id": 1,
                "item_name": "",
                "max_score": 10,
                "ai_score": 8,
                "deduction_reason": "不超过80字",
                "confidence": "高/中/低",
                "need_teacher_review": True,
            }
        ],
        "common_error_tags": ["不超过5个标签"],
    }
    detected_summary = detected_flags.get("summary") if isinstance(detected_flags, dict) else ""
    if use_vision and sent_image_count > 0:
        image_note = (
            f"该报告共提取 {len(image_infos)} 张截图，本次已向 AI 发送 {sent_image_count} 张截图。"
            "评分时可以结合已发送截图内容，但不能臆测未发送截图的细节；证据不足的项目需要标记 need_teacher_review=true。"
        )
    else:
        image_note = (
            f"该报告共提取 {len(image_infos)} 张截图。当前为纯文本初评模式，AI 未读取截图内容；"
            "涉及截图真实性、截图细节和截图证据充分性的评分项，请标记 need_teacher_review=true。"
        )
    system = (
        "你是一名高校课程实验报告评分助手。你的任务是严格依据教师提供的实验任务和评分标准，"
        "对已经脱敏的学生实验报告生成 AI 建议分。AI 建议分不是最终成绩，最终成绩必须由教师复核确认。"
        "不得因为姓名、学号、班级等字段被脱敏而扣分。只返回严格 JSON，不要返回 Markdown 或代码块。"
    )
    user = f"""
【课程信息】
Prompt模板版本：{PROMPT_TEMPLATE_VERSION}
课程名称：{course.get("course_name") or course.get("name") or ""}
课程类型：{course.get("course_type") or ""}

【实验任务】
实验名称：{experiment.get("experiment_name") or experiment.get("title") or ""}
实验目标：{_truncate(experiment.get("experiment_objectives"), 800)}
实验要求：{_truncate(experiment.get("experiment_requirements"), 800)}
必须截图：{_truncate(experiment.get("required_screenshots"), 500)}
重点检查：{_truncate(experiment.get("key_evaluation_points"), 800)}
常见错误：{_truncate(experiment.get("common_errors"), 500)}

【评分标准】
{json.dumps(rubric_payload, ensure_ascii=False)}

【脱敏说明】
{detected_summary or "报告中如有姓名、学号、班级等真实信息，系统已尽量替换为脱敏占位符。评分时不得因此扣分。"}

【截图说明】
{image_note}

【学生报告脱敏文本】
{anonymized_text}

【输出 JSON 结构】
{json.dumps(output_schema, ensure_ascii=False)}

【约束】
1. rubric_scores 必须覆盖所有评分项。
2. ai_score 不能小于 0，不能大于 max_score。
3. confidence 只能是“高”“中”“低”。
4. requires_review=true 的评分项必须 need_teacher_review=true。
5. 证据不足时不要臆测，应降低置信度并标记教师复核。
""".strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def score_submission(
    submission_id: int,
    rescore: bool = True,
    use_vision: bool = False,
    image_mode: str = "first_3",
    image_indices: list[int] | None = None,
) -> dict:
    submission = fetch_one("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    if not submission:
        return {"ok": False, "message": "未找到提交记录。"}
    if not rescore and submission.get("ai_status") == AI_DONE:
        return {"ok": True, "message": "该报告已完成初评，已跳过。", "skipped": True}

    try:
        _validate_submission(submission)
        task = _get_task(int(submission.get("task_id") or submission.get("grading_task_id")))
        course = fetch_one("SELECT * FROM courses WHERE id = ?", (task["course_id"],))
        experiment = fetch_one("SELECT * FROM experiments WHERE id = ?", (task["experiment_id"],))
        rubric_items = _get_rubric_items(int(task["experiment_id"]))
        if not rubric_items:
            raise ValueError("该实验任务尚未配置评分标准，不能进行 AI 初评。")
        config = get_default_config()
        if not config:
            raise ValueError("未设置默认 AI 配置，请先配置默认模型。")
        if not int(config.get("enabled") or 0):
            raise ValueError("默认 AI 配置未启用。")

        anonymized_text = str(submission.get("anonymized_text") or "")
        sent_text = anonymized_text[:MAX_TEXT_CHARS]
        if len(anonymized_text) > MAX_TEXT_CHARS:
            sent_text += f"\n\n【系统提示】报告较长，当前仅截取前 {MAX_TEXT_CHARS} 字用于 AI 初评，教师需结合完整报告复核。"
        image_infos = _build_image_infos(submission)
        selected_image_infos = _select_image_infos(image_infos, image_mode, image_indices)
        vision_enabled = _can_use_vision(config, use_vision, selected_image_infos)
        detected_flags = _loads_json(submission.get("detected_flags"), {})
        messages = build_scoring_prompt(
            course or {},
            experiment or {},
            rubric_items,
            sent_text,
            detected_flags,
            image_infos,
            use_vision=vision_enabled,
            sent_image_count=len(selected_image_infos) if vision_enabled else 0,
        )
        model_name = config.get("text_model")
        if vision_enabled:
            messages = _build_multimodal_messages(messages, selected_image_infos)
            model_name = config.get("vision_model") or config.get("text_model")

        execute(
            """
            UPDATE submissions
            SET ai_status = ?, ai_error = NULL, ai_scored_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (AI_RUNNING, submission_id),
        )
        result = chat_completion_stream(
            config=config,
            messages=messages,
            model=model_name,
            max_tokens=MAX_OUTPUT_TOKENS,
            timeout=120,
            extra_body=kimi_fast_extra_body(config, model_name),
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("user_message") or result.get("error") or "AI 请求失败。")
        parsed = extract_json_from_text(result.get("content") or "")
        if parsed is None:
            _mark_failed(submission_id, "AI 返回内容不是有效 JSON。", raw_response=result.get("content") or "")
            return {"ok": False, "message": "AI 返回内容不是有效 JSON。"}
        normalized = validate_and_normalize_ai_score(parsed, rubric_items)
        _save_ai_result(submission, normalized, result.get("content") or "", result.get("raw") or {})
        return {
            "ok": True,
            "message": "AI 初评完成。",
            "data": {
                "submission_id": submission_id,
                "total_ai_score": normalized["total_ai_score"],
                "rubric_count": len(normalized["rubric_scores"]),
                "sent_text_length": len(sent_text),
                "image_count": len(image_infos),
                "use_vision": vision_enabled,
                "image_mode": image_mode,
                "sent_image_count": len(selected_image_infos) if vision_enabled else 0,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            },
        }
    except Exception as exc:
        _mark_failed(submission_id, str(exc))
        return {"ok": False, "message": str(exc)}


def score_task(
    task_id: int,
    rescore_completed: bool = False,
    use_vision: bool = False,
    image_mode: str = "first_3",
) -> dict:
    if image_mode == "custom":
        image_mode = "first_3"
    rows = fetch_all(
        """
        SELECT *
        FROM submissions
        WHERE COALESCE(task_id, grading_task_id) = ?
          AND match_status IN (?, ?)
          AND parse_status = ?
        ORDER BY student_no ASC, id ASC
        """,
        (task_id, MATCHED, NAME_MISMATCH, PARSE_DONE),
    )
    success = failed = skipped = 0
    for row in rows:
        if row.get("ai_status") == AI_DONE and not rescore_completed:
            skipped += 1
            continue
        result = score_submission(int(row["id"]), rescore=True, use_vision=use_vision, image_mode=image_mode)
        if result.get("ok"):
            success += 1
        else:
            failed += 1
    return {"total": len(rows), "success": success, "failed": failed, "skipped": skipped}


def reset_submission_ai_status(submission_id: int) -> dict:
    with get_connection() as conn:
        conn.execute("DELETE FROM ai_scores WHERE submission_id = ?", (submission_id,))
        conn.execute(
            """
            UPDATE submissions
            SET ai_status = ?, ai_total_score = NULL, ai_overall_comment = NULL,
                ai_student_feedback = NULL, ai_common_error_tags = NULL,
                ai_teacher_review_points = NULL, ai_raw_response = NULL,
                ai_error = NULL, ai_prompt_version = NULL, ai_scored_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (AI_NOT_STARTED, submission_id),
        )
        conn.commit()
    return {"ok": True, "message": "该报告 AI 状态已重置。"}


def get_ai_summary(task_id: int) -> dict:
    rows = fetch_all("SELECT ai_status, parse_status, match_status FROM submissions WHERE COALESCE(task_id, grading_task_id) = ?", (task_id,))
    return {
        "total": len(rows),
        "parsed": sum(1 for row in rows if row.get("parse_status") == PARSE_DONE),
        "pending": sum(1 for row in rows if row.get("match_status") in {MATCHED, NAME_MISMATCH} and row.get("parse_status") == PARSE_DONE and row.get("ai_status") != AI_DONE),
        "done": sum(1 for row in rows if row.get("ai_status") == AI_DONE),
        "failed": sum(1 for row in rows if row.get("ai_status") == AI_FAILED),
    }


def list_ai_scores(submission_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM ai_scores WHERE submission_id = ? ORDER BY id ASC", (submission_id,))


def test_default_config() -> dict:
    config = get_default_config()
    if not config:
        return {"ok": False, "message": "未设置默认 AI 配置。"}
    return test_config(int(config["id"]))


def _select_image_infos(image_infos: list[dict], image_mode: str, image_indices: list[int] | None = None) -> list[dict]:
    mode = (image_mode or "first_3").strip()
    if mode == "all":
        return list(image_infos)
    if mode == "custom":
        selected = {int(index) for index in image_indices or [] if int(index) > 0}
        return [item for item in image_infos if int(item.get("index") or 0) in selected]
    return list(image_infos[:DEFAULT_VISION_IMAGES])


def _can_use_vision(config: dict, use_vision: bool, selected_image_infos: list[dict]) -> bool:
    if not use_vision or not selected_image_infos:
        return False
    return bool(int(config.get("supports_vision") or 0) and (config.get("vision_model") or config.get("text_model")))


def _build_multimodal_messages(messages: list[dict], selected_image_infos: list[dict]) -> list[dict]:
    if not messages:
        return messages
    converted = [dict(message) for message in messages]
    user_message = dict(converted[-1])
    text = str(user_message.get("content") or "")
    content: list[dict] = []
    for image in selected_image_infos:
        image_path = image.get("path")
        if not image_path:
            continue
        try:
            resolved_path = resolve_stored_file_path(image_path)
            if not resolved_path.exists():
                continue
            content.append({"type": "image_url", "image_url": {"url": encode_image_to_data_url(resolved_path)}})
        except Exception:
            continue
    content.append({"type": "text", "text": text})
    user_message["content"] = content
    converted[-1] = user_message
    return converted


def _validate_submission(submission: dict) -> None:
    if submission.get("match_status") not in {MATCHED, NAME_MISMATCH}:
        raise ValueError("该报告未处于可初评的匹配状态。")
    if submission.get("parse_status") != PARSE_DONE:
        raise ValueError("该报告尚未完成解析与脱敏。")
    if not str(submission.get("anonymized_text") or "").strip():
        raise ValueError("脱敏文本为空，不能进行 AI 初评。")


def _get_task(task_id: int) -> dict:
    task = fetch_one("SELECT * FROM grading_tasks WHERE id = ?", (task_id,))
    if not task:
        raise ValueError("未找到批改任务。")
    return task


def _get_rubric_items(experiment_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM rubric_items WHERE experiment_id = ? ORDER BY sort_order ASC, id ASC", (experiment_id,))


def _save_ai_result(submission: dict, normalized: dict, raw_content: str, raw: Any) -> None:
    submission_id = int(submission["id"])
    task_id = int(submission.get("task_id") or submission.get("grading_task_id"))
    with get_connection() as conn:
        conn.execute("DELETE FROM ai_scores WHERE submission_id = ?", (submission_id,))
        for item in normalized["rubric_scores"]:
            conn.execute(
                """
                INSERT INTO ai_scores (
                    submission_id, task_id, rubric_item_id, item_name, max_score, ai_score,
                    deduction_reason, evidence_json, suggestion, confidence, need_teacher_review
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    task_id,
                    int(item["rubric_item_id"]),
                    item["item_name"],
                    float(item["max_score"]),
                    float(item["ai_score"]),
                    item.get("deduction_reason") or "",
                    json.dumps(item.get("evidence") or [], ensure_ascii=False),
                    item.get("suggestion") or "",
                    item.get("confidence") or "低",
                    int(bool(item.get("need_teacher_review"))),
                ),
            )
        conn.execute(
            """
            UPDATE submissions
            SET ai_status = ?, ai_total_score = ?, ai_overall_comment = ?,
                ai_student_feedback = ?, ai_common_error_tags = ?, ai_teacher_review_points = ?,
                ai_raw_response = ?, ai_error = NULL, ai_prompt_version = ?,
                ai_scored_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                AI_DONE,
                float(normalized["total_ai_score"]),
                normalized.get("overall_comment") or "",
                normalized.get("student_feedback") or "",
                json.dumps(normalized.get("common_error_tags") or [], ensure_ascii=False),
                json.dumps(normalized.get("teacher_review_points") or [], ensure_ascii=False),
                json.dumps({"content": raw_content, "raw": raw}, ensure_ascii=False),
                PROMPT_TEMPLATE_VERSION,
                submission_id,
            ),
        )
        conn.commit()


def _mark_failed(submission_id: int, message: str, raw_response: str | None = None) -> None:
    execute(
        """
        UPDATE submissions
        SET ai_status = ?, ai_error = ?, ai_raw_response = COALESCE(?, ai_raw_response),
            ai_scored_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (AI_FAILED, message[:2000], raw_response, submission_id),
    )


def _build_image_infos(submission: dict) -> list[dict]:
    paths = _loads_json(submission.get("image_paths"), [])
    return [{"index": index, "path": path} for index, path in enumerate(paths, start=1)]


def _loads_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _truncate(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]
