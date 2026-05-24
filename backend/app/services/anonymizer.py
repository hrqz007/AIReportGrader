from __future__ import annotations

import re


PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_CARD_RE = re.compile(r"(?<!\d)(?:\d{15}|\d{17}[\dXx])(?!\d)")
WINDOWS_USER_PATH_RE = re.compile(r"C:\\Users\\[^\\\s]+", re.IGNORECASE)
ACCOUNT_KEYWORD_RE = re.compile(
    r"(QQ|微信|WeChat|wechat|账号|帐号|个人账号|联系方式|电话|手机号)\s*[:：]?",
    re.IGNORECASE,
)


def detect_sensitive_info(
    text: str,
    student_no: str | None = None,
    student_name: str | None = None,
    class_name: str | None = None,
) -> dict:
    content = text or ""
    flags = {
        "name_detected": bool(student_name and student_name in content),
        "student_no_detected": bool(student_no and student_no in content),
        "class_detected": bool(class_name and class_name in content),
        "phone_detected": bool(PHONE_RE.search(content)),
        "email_detected": bool(EMAIL_RE.search(content)),
        "id_card_detected": bool(ID_CARD_RE.search(content)),
        "windows_user_path_detected": bool(WINDOWS_USER_PATH_RE.search(content)),
        "account_keyword_detected": bool(ACCOUNT_KEYWORD_RE.search(content)),
    }
    label_map = {
        "name_detected": "姓名",
        "student_no_detected": "学号",
        "class_detected": "班级",
        "phone_detected": "手机号",
        "email_detected": "邮箱",
        "id_card_detected": "身份证号样式",
        "windows_user_path_detected": "Windows 用户路径",
        "account_keyword_detected": "个人账号关键词",
    }
    labels = [label for key, label in label_map.items() if flags[key]]
    flags["summary"] = f"检测到{'、'.join(labels)}信息。" if labels else "未检测到明显敏感信息。"
    return flags


def anonymize_text(
    text: str,
    student_no: str | None = None,
    student_name: str | None = None,
    class_name: str | None = None,
) -> str:
    anonymized = text or ""
    replacements = {
        student_name: "[姓名已脱敏]",
        student_no: "[学号已脱敏]",
        class_name: "[班级已脱敏]",
    }
    for raw, placeholder in replacements.items():
        if raw:
            anonymized = anonymized.replace(raw, placeholder)

    anonymized = PHONE_RE.sub("[手机号已脱敏]", anonymized)
    anonymized = EMAIL_RE.sub("[邮箱已脱敏]", anonymized)
    anonymized = ID_CARD_RE.sub("[身份证号已脱敏]", anonymized)
    anonymized = WINDOWS_USER_PATH_RE.sub(lambda _: r"C:\Users\[用户路径已脱敏]", anonymized)
    anonymized = re.sub(
        r"(QQ|微信|WeChat|wechat|账号|帐号|个人账号)\s*[:：]\s*\S+",
        r"\1：[个人账号已脱敏]",
        anonymized,
        flags=re.IGNORECASE,
    )
    return anonymized
