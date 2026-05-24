from __future__ import annotations

import json
import re
from typing import Any


def extract_json_from_text(text: str) -> dict | None:
    content = (text or "").strip()
    if not content:
        return None

    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL | re.IGNORECASE)
    if code_block:
        try:
            parsed = json.loads(code_block.group(1).strip())
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    candidate = _find_first_json_object(content)
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def validate_and_normalize_ai_score(ai_result: dict, rubric_items: list[dict]) -> dict:
    if not isinstance(ai_result, dict):
        raise ValueError("AI 评分结果必须是 JSON 对象。")

    returned_scores = ai_result.get("rubric_scores") or []
    if not isinstance(returned_scores, list):
        returned_scores = []

    by_id: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for item in returned_scores:
        if not isinstance(item, dict):
            continue
        try:
            by_id[int(item.get("rubric_item_id"))] = item
        except (TypeError, ValueError):
            pass
        name = str(item.get("item_name") or "").strip()
        if name:
            by_name[name] = item

    normalized_scores: list[dict] = []
    total = 0.0
    for rubric in rubric_items:
        rubric_id = int(rubric["id"])
        item_name = str(rubric.get("item_name") or "")
        max_score = _to_float(rubric.get("max_score"), 0.0)
        requires_review = bool(int(rubric.get("requires_review") or 0))
        returned = by_id.get(rubric_id) or by_name.get(item_name)

        if returned is None:
            score = {
                "rubric_item_id": rubric_id,
                "item_name": item_name,
                "max_score": max_score,
                "ai_score": 0.0,
                "deduction_reason": "AI 未返回该评分项，需教师复核。",
                "evidence": [{"type": "text", "source": "评分标准", "content": "该评分项缺失。"}],
                "suggestion": "请教师人工检查该评分项。",
                "confidence": "低",
                "need_teacher_review": True,
            }
        else:
            raw_score = returned.get("ai_score")
            score_value = _to_float(raw_score, 0.0)
            score_value = max(0.0, min(score_value, max_score))
            confidence = str(returned.get("confidence") or "低").strip()
            if confidence not in {"高", "中", "低"}:
                confidence = "低"
            score = {
                "rubric_item_id": rubric_id,
                "item_name": item_name,
                "max_score": max_score,
                "ai_score": round(score_value, 2),
                "deduction_reason": str(returned.get("deduction_reason") or "未说明扣分原因，需教师复核。"),
                "evidence": returned.get("evidence") if isinstance(returned.get("evidence"), list) else [],
                "suggestion": str(returned.get("suggestion") or ""),
                "confidence": confidence,
                "need_teacher_review": bool(returned.get("need_teacher_review")) or requires_review,
            }

        total += float(score["ai_score"])
        normalized_scores.append(score)

    common_error_tags = ai_result.get("common_error_tags") or []
    if not isinstance(common_error_tags, list):
        common_error_tags = [str(common_error_tags)]

    return {
        "total_ai_score": round(total, 2),
        "overall_comment": str(ai_result.get("overall_comment") or ""),
        "rubric_scores": normalized_scores,
        "common_error_tags": [str(item) for item in common_error_tags if str(item).strip()],
        "student_feedback": str(ai_result.get("student_feedback") or ""),
        "teacher_review_points": ai_result.get("teacher_review_points") if isinstance(ai_result.get("teacher_review_points"), list) else [],
    }


def _find_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
