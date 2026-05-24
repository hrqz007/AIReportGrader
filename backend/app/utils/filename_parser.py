from __future__ import annotations

import re
from pathlib import Path


UNRELATED_WORDS = [
    "实验报告",
    "实验",
    "报告",
    "静态路由",
    "配置",
    "第",
    "次",
]


def _clean_name_part(value: str | None) -> str:
    if not value:
        return ""
    parts = [part for part in re.split(r"[\s_\-—–()（）【】\[\]]+", value) if part]
    for part in parts:
        if any(word in part for word in UNRELATED_WORDS):
            continue
        candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", part)
        if candidates:
            return candidates[0]

    text = value
    for word in UNRELATED_WORDS:
        text = text.replace(word, "")
    text = re.sub(r"[\s_\-—–()（）【】\[\]0-9A-Za-z]+", "", text)
    candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
    return candidates[0] if candidates else ""


def parse_student_from_filename(filename: str) -> dict[str, str]:
    stem = Path(filename).stem.strip()
    number_match = re.search(r"(?P<student_no>\d{6,20})", stem)
    if not number_match:
        return {"student_no": "", "student_name": "", "raw_name_part": ""}

    student_no = number_match.group("student_no")
    before = stem[: number_match.start()]
    after = stem[number_match.end() :]
    after_name = _clean_name_part(after)
    before_name = _clean_name_part(before)
    return {
        "student_no": student_no,
        "student_name": after_name or before_name,
        "raw_name_part": (after if after_name else before).strip(" _-—–"),
    }
