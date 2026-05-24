from __future__ import annotations

import json

from app.db.database import execute, fetch_all, fetch_one, get_connection
from app.services.ai_client import chat_completion_once, kimi_fast_extra_body
from app.utils.json_utils import extract_json_from_text


def list_configs() -> list[dict]:
    return fetch_all(
        """
        SELECT *
        FROM ai_provider_configs
        ORDER BY is_default DESC, enabled DESC, id DESC
        """
    )


def get_config(config_id: int) -> dict | None:
    return fetch_one("SELECT * FROM ai_provider_configs WHERE id = ?", (config_id,))


def get_default_config() -> dict | None:
    return fetch_one(
        """
        SELECT *
        FROM ai_provider_configs
        WHERE is_default = 1 AND enabled = 1
        ORDER BY id DESC
        LIMIT 1
        """
    )


def create_config(payload: dict) -> int:
    _validate_payload(payload)
    analysis_model = payload.get("analysis_model") or payload.get("text_model")
    is_default = int(bool(payload.get("is_default")))
    with get_connection() as conn:
        if is_default:
            conn.execute("UPDATE ai_provider_configs SET is_default = 0")
        cursor = conn.execute(
            """
            INSERT INTO ai_provider_configs (
                provider_name, provider_type, base_url, api_key, text_model, vision_model,
                analysis_model, supports_vision, supports_json, is_default, enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["provider_name"].strip(),
                payload.get("provider_type") or "openai_compatible",
                payload["base_url"].strip(),
                payload["api_key"].strip(),
                payload["text_model"].strip(),
                (payload.get("vision_model") or "").strip(),
                (analysis_model or "").strip(),
                int(bool(payload.get("supports_vision"))),
                int(bool(payload.get("supports_json", True))),
                is_default,
                int(bool(payload.get("enabled", True))),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_config(config_id: int, payload: dict) -> None:
    current = get_config(config_id)
    if not current:
        raise ValueError("未找到 AI 配置。")
    merged = {**current, **payload}
    if not payload.get("api_key"):
        merged["api_key"] = current.get("api_key")
    _validate_payload(merged)
    analysis_model = merged.get("analysis_model") or merged.get("text_model")
    is_default = int(bool(merged.get("is_default")))
    with get_connection() as conn:
        if is_default:
            conn.execute("UPDATE ai_provider_configs SET is_default = 0 WHERE id <> ?", (config_id,))
        conn.execute(
            """
            UPDATE ai_provider_configs
            SET provider_name = ?, provider_type = ?, base_url = ?, api_key = ?, text_model = ?,
                vision_model = ?, analysis_model = ?, supports_vision = ?, supports_json = ?,
                is_default = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                merged["provider_name"].strip(),
                merged.get("provider_type") or "openai_compatible",
                merged["base_url"].strip(),
                merged["api_key"].strip(),
                merged["text_model"].strip(),
                (merged.get("vision_model") or "").strip(),
                (analysis_model or "").strip(),
                int(bool(merged.get("supports_vision"))),
                int(bool(merged.get("supports_json", True))),
                is_default,
                int(bool(merged.get("enabled", True))),
                config_id,
            ),
        )
        conn.commit()


def delete_config(config_id: int) -> None:
    execute("DELETE FROM ai_provider_configs WHERE id = ?", (config_id,))


def mask_api_key(api_key: str | None) -> str:
    text = api_key or ""
    if len(text) <= 10:
        return "*" * len(text)
    return f"{text[:6]}{'*' * max(len(text) - 10, 4)}{text[-4:]}"


def test_config(config_id: int) -> dict:
    config = get_config(config_id)
    if not config:
        return {"ok": False, "message": "未找到 AI 配置。"}
    messages = [
        {"role": "system", "content": "你是连接测试助手，请严格返回 JSON。"},
        {"role": "user", "content": '请返回 {"status":"ok","message":"连接成功"}'},
    ]
    result = chat_completion_once(
        config,
        messages,
        model=config.get("text_model"),
        max_tokens=128,
        timeout=30,
        extra_body=kimi_fast_extra_body(config, config.get("text_model")),
    )
    if not result.get("ok"):
        return {"ok": False, "message": result.get("user_message") or "连接失败。", "error": result.get("error")}
    parsed = extract_json_from_text(result.get("content") or "")
    if parsed and parsed.get("status") == "ok":
        return {"ok": True, "message": parsed.get("message") or "连接成功。", "content": result.get("content")}
    return {"ok": True, "message": "接口可访问，但返回格式未严格遵守 JSON。", "content": result.get("content")}


def public_config(config: dict) -> dict:
    data = dict(config)
    data["api_key"] = mask_api_key(data.get("api_key"))
    return data


def _validate_payload(payload: dict) -> None:
    for key, label in {
        "provider_name": "服务商名称",
        "base_url": "API Base URL",
        "api_key": "API Key",
        "text_model": "文本模型",
    }.items():
        if not str(payload.get(key) or "").strip():
            raise ValueError(f"{label}不能为空。")
