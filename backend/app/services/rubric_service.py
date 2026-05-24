from __future__ import annotations

from app.db.database import execute, fetch_all, fetch_one, get_connection


COMMON_REPORT_RUBRIC_TEMPLATE = [
    {
        "item_name": "实验报告结构完整性",
        "max_score": 10,
        "description": "检查实验报告是否包含实验目的、实验环境、实验步骤、实验结果、结果分析和实验总结等基本组成部分。",
        "deduction_rules": "缺少关键部分按缺失程度扣分，结构混乱或内容明显不完整应适当扣分。",
        "requires_review": False,
        "sort_order": 1,
    },
    {
        "item_name": "实验任务完成度",
        "max_score": 20,
        "description": "检查学生是否按照实验要求完成主要任务，是否覆盖本次实验规定的核心操作。",
        "deduction_rules": "未完成核心任务、任务步骤缺失或与实验要求不符时扣分。",
        "requires_review": True,
        "sort_order": 2,
    },
    {
        "item_name": "关键截图与证据充分性",
        "max_score": 20,
        "description": "检查报告中是否包含本次实验要求的关键截图，截图是否能够支撑实验过程和实验结果。",
        "deduction_rules": "缺少关键截图、截图模糊、截图与文字不对应或截图不能证明实验结果时扣分。",
        "requires_review": True,
        "sort_order": 3,
    },
    {
        "item_name": "技术正确性",
        "max_score": 20,
        "description": "检查实验配置、代码、参数、命令或操作过程是否正确，是否符合课程知识点和实验目标。",
        "deduction_rules": "存在配置错误、代码错误、参数错误、实验结果不成立等情况时扣分。",
        "requires_review": True,
        "sort_order": 4,
    },
    {
        "item_name": "结果分析与原理解释",
        "max_score": 20,
        "description": "检查学生是否对实验结果进行解释，是否能说明结果背后的原理、原因和过程，而不是只给出截图或结论。",
        "deduction_rules": "只写“成功”“完成”等空泛表述，缺少原理分析、原因解释或结果讨论时扣分。",
        "requires_review": True,
        "sort_order": 5,
    },
    {
        "item_name": "表达规范与实验反思",
        "max_score": 10,
        "description": "检查报告语言、格式、图文对应关系和实验反思质量。",
        "deduction_rules": "语言混乱、格式不规范、反思空泛、复制模板痕迹明显时扣分。",
        "requires_review": False,
        "sort_order": 6,
    },
]


def _required(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空。")
    return text


def _optional(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _score(value: float | int | str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("满分必须是数字。") from exc
    if score <= 0:
        raise ValueError("满分必须大于 0。")
    return score


def list_rubric_items(experiment_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT *
        FROM rubric_items
        WHERE experiment_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (experiment_id,),
    )


def get_rubric_item(item_id: int) -> dict | None:
    return fetch_one("SELECT * FROM rubric_items WHERE id = ?", (item_id,))


def create_rubric_item(
    experiment_id: int,
    item_name: str,
    max_score: float,
    description: str | None = None,
    deduction_rules: str | None = None,
    requires_review: bool = False,
    sort_order: int = 0,
) -> int:
    item_name = _required(item_name, "评分项名称")
    score = _score(max_score)
    desc = _optional(description)
    return execute(
        """
        INSERT INTO rubric_items (
            experiment_id, item_name, item_description, description, deduction_rules,
            max_score, requires_review, sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_id,
            item_name,
            desc,
            desc,
            _optional(deduction_rules),
            score,
            int(requires_review),
            int(sort_order or 0),
        ),
    )


def update_rubric_item(
    item_id: int,
    item_name: str,
    max_score: float,
    description: str | None = None,
    deduction_rules: str | None = None,
    requires_review: bool = False,
    sort_order: int = 0,
) -> None:
    if get_rubric_item(item_id) is None:
        raise ValueError("未找到评分项。")
    item_name = _required(item_name, "评分项名称")
    score = _score(max_score)
    desc = _optional(description)
    execute(
        """
        UPDATE rubric_items
        SET item_name = ?,
            item_description = ?,
            description = ?,
            deduction_rules = ?,
            max_score = ?,
            requires_review = ?,
            sort_order = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            item_name,
            desc,
            desc,
            _optional(deduction_rules),
            score,
            int(requires_review),
            int(sort_order or 0),
            item_id,
        ),
    )


def delete_rubric_item(item_id: int) -> None:
    item = get_rubric_item(item_id)
    if item is None:
        raise ValueError("未找到评分项。")
    ai_score_count = fetch_one("SELECT COUNT(*) AS count FROM ai_scores WHERE rubric_item_id = ?", (item_id,))
    task_count = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM grading_tasks
        WHERE experiment_id = ?
        """,
        (item.get("experiment_id"),),
    )
    blocking = []
    if int((task_count or {}).get("count") or 0) > 0:
        blocking.append(f"关联批改任务 {int((task_count or {}).get('count') or 0)} 个")
    if int((ai_score_count or {}).get("count") or 0) > 0:
        blocking.append(f"AI 分项评分 {int((ai_score_count or {}).get('count') or 0)} 条")
    if blocking:
        raise ValueError("该评分项已有后续评分数据或批改任务引用，不能直接删除：" + "、".join(blocking) + "。")
    execute("DELETE FROM rubric_items WHERE id = ?", (item_id,))


def get_total_score(experiment_id: int) -> float:
    row = fetch_one("SELECT COALESCE(SUM(max_score), 0) AS total FROM rubric_items WHERE experiment_id = ?", (experiment_id,))
    return float(row["total"] or 0)


def create_common_report_rubric_template(experiment_id: int) -> int:
    if list_rubric_items(experiment_id):
        raise ValueError("当前实验任务已有评分项。如需使用模板，请先删除现有评分项。")
    with get_connection() as conn:
        for item in COMMON_REPORT_RUBRIC_TEMPLATE:
            desc = item["description"]
            conn.execute(
                """
                INSERT INTO rubric_items (
                    experiment_id, item_name, item_description, description, deduction_rules,
                    max_score, requires_review, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    item["item_name"],
                    desc,
                    desc,
                    item["deduction_rules"],
                    item["max_score"],
                    int(item["requires_review"]),
                    item["sort_order"],
                ),
            )
        conn.commit()
    return len(COMMON_REPORT_RUBRIC_TEMPLATE)
