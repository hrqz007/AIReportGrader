from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

try:
    from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
except Exception:  # pragma: no cover
    APIConnectionError = None
    APIStatusError = None
    APITimeoutError = None
    OpenAI = None


def chat_completion_once(
    config: dict,
    messages: list,
    model: str | None = None,
    max_tokens: int | None = 1024,
    timeout: int = 60,
    extra_body: dict | None = None,
) -> dict:
    return _chat_completion(config, messages, model, max_tokens, timeout, extra_body, stream=False)


def chat_completion_stream(
    config: dict,
    messages: list,
    model: str | None = None,
    max_tokens: int | None = 2048,
    timeout: int = 120,
    extra_body: dict | None = None,
) -> dict:
    return _chat_completion(config, messages, model, max_tokens, timeout, extra_body, stream=True)


def kimi_fast_extra_body(config: dict, model_name: str | None = None) -> dict | None:
    model = (model_name or config.get("text_model") or "").lower()
    base_url = (config.get("base_url") or "").lower()
    if "kimi-k2.6" in model or "kimi-k2.5" in model or ("moonshot" in base_url and model.startswith("kimi-k2")):
        return {"thinking": {"type": "disabled"}}
    return None


def guess_image_mime_type(image_path: str | Path) -> str:
    suffix = Path(image_path).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "image/png"


def encode_image_to_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    mime_type = guess_image_mime_type(path)
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _chat_completion(
    config: dict,
    messages: list,
    model: str | None,
    max_tokens: int | None,
    timeout: int,
    extra_body: dict | None,
    stream: bool,
) -> dict:
    if OpenAI is None:
        return _failure("当前环境未安装通用兼容 API 客户端，请先安装后端依赖。", "dependency_error", "AI 客户端组件缺失。")

    base_url = str(config.get("base_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    selected_model = str(model or config.get("text_model") or "").strip()
    if not base_url or not api_key or not selected_model:
        return _failure("AI 配置缺少 Base URL、API Key 或模型名称。", "config_error", "AI 配置不完整。")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=timeout)
        kwargs: dict[str, Any] = {"model": selected_model, "messages": messages, "stream": stream}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if extra_body:
            kwargs["extra_body"] = extra_body

        if stream:
            content_parts: list[str] = []
            chunk_count = 0
            for chunk in client.chat.completions.create(**kwargs):
                chunk_count += 1
                try:
                    content = chunk.choices[0].delta.content
                except Exception:
                    content = None
                if content:
                    content_parts.append(str(content))
            return _success("".join(content_parts), {"stream": True, "chunk_count": chunk_count})

        response = client.chat.completions.create(**kwargs)
        raw = response.model_dump() if hasattr(response, "model_dump") else response
        content = str(response.choices[0].message.content or "")
        return _success(content, raw)
    except Exception as exc:
        return _exception_to_failure(exc)


def _success(content: str, raw: Any) -> dict:
    return {"ok": True, "content": content, "raw": raw, "error": "", "error_type": "", "user_message": "", "attempts": 1}


def _failure(error: str, error_type: str, user_message: str) -> dict:
    return {"ok": False, "content": "", "raw": None, "error": error, "error_type": error_type, "user_message": user_message, "attempts": 1}


def _exception_to_failure(exc: Exception) -> dict:
    if APITimeoutError is not None and isinstance(exc, APITimeoutError):
        return _failure(str(exc), "timeout", "AI 服务响应超时。建议稍后重试，或缩短报告文本后再试。")
    if APIConnectionError is not None and isinstance(exc, APIConnectionError):
        return _failure(str(exc), "connection_error", "无法连接 AI 服务，请检查网络、代理或服务商状态。")
    if APIStatusError is not None and isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", "")
        return _failure(str(exc), "http_error", f"AI 服务返回 HTTP 错误{status}，请检查模型名称、额度和接口地址。")
    if isinstance(exc, TimeoutError):
        return _failure(str(exc), "timeout", "AI 服务响应超时。")
    return _failure(str(exc), "unknown_error", "AI 请求发生未知错误。")
