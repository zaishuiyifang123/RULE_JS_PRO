from __future__ import annotations

import json
from typing import Any

SQL_GENERATION_SYSTEM_PROMPT = """
你是教务系统 SQL 生成助手。
请基于任务解析结果生成 MySQL 8 可执行 SQL，并严格遵守以下约束：
1) 只输出一个 JSON 对象，不要输出 markdown、解释或多余文本。
2) JSON 必须包含：
   - sql: string
   - entity_mappings: [{type, value, field, reason}]
   - sql_fields: [table.field]
3) sql 必须使用 WITH（CTE）开头。
4) sql 中字段引用必须使用 table.field；但当字段来自 CTE（如 base）时，允许使用 cte_name.field（如 base.course_name）。CTE 中 select 的列名应为无点号的列名（如 course_name、teacher_name），外层用 base.<列名> 引用。
5) 原表字段必须来自 kb_field_whitelist；CTE 输出列（如 base.course_name）必须是从 whitelist 字段直接 SELECT 出来的列（不允许凭空造列）。
6) 生成时必须参考 kb_schema_hints 中的表描述(table_description)和字段描述(field_description)做语义对齐。
7) entity_mappings 必须覆盖输入 entities 的每个实体，并映射到具体 table.field。
8) 若无法可靠映射，不要臆造字段，保持空并交给调用方报错。
9) 外层查询如果 FROM base，则不得引用 CTE 内部原表名（course.xxx），只能引用 base.xxx。
10) 当 hidden_context.probe_samples 提供某字段的候选值时，必须优先用候选值对 SQL 过滤值做归一化，不得机械沿用用户简称原文。
11) 文本值归一化顺序：先精确匹配，再做规范化匹配（大小写/空白/常见简称），再做语义近似匹配；若唯一候选可确定，SQL 中必须使用该候选的真实值并优先使用 '='。
12) 如果候选值不唯一且无法可靠唯一化，可使用 LIKE，但必须叠加其他可确定条件（如年级、专业）缩小范围，并在 reason 中写明未唯一化原因。
13) entity_mappings.reason 必须明确说明“原始实体值 -> SQL 实际过滤值”的依据；当依据来自 probe_samples 时必须显式注明。
14) 若 hidden_context.hints 包含 retry_sql_generation_with_hidden_context，且已出现可用候选值，本轮 SQL 相比 failed_sql 必须体现过滤值修正。
15) SQL 中所有 table.field 引用与字符串过滤值都必须去除两端空格（例如 student.gender='男'，不得出现 student.gender=' 男' 或 class . class_name）。
完整输出示例（必须严格输出 JSON，不要附加解释）：
{
  "sql": "WITH base AS (SELECT student.enroll_year, student.gender, class.class_name FROM student JOIN class ON student.class_id = class.id WHERE student.enroll_year = 2022 AND student.gender = '男' AND student.is_deleted = 0 AND class.is_deleted = 0) SELECT base.class_name, COUNT(*) AS student_count FROM base GROUP BY base.class_name ORDER BY student_count DESC",
  "entity_mappings": [
    {"type": "grade", "value": "22级", "field": "student.enroll_year", "reason": "根据字段描述“入学年份（常见问法：22级）”映射"},
    {"type": "gender", "value": "男生", "field": "student.gender", "reason": "根据字段描述“性别（男/女等）”映射"}
  ],
  "sql_fields": [
    "student.enroll_year",
    "student.gender",
    "class.class_name",
    "student.class_id",
    "class.id",
    "student.is_deleted",
    "class.is_deleted"
  ]
}
""".strip()


def build_sql_generation_user_prompt(
    rewritten_query: str,
    task: dict[str, Any],
    field_whitelist: list[str],
    alias_pairs: list[dict[str, list[str]]],
    schema_hints: list[dict[str, Any]],
    hidden_context: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "rewritten_query": rewritten_query,
        "task": task,
        "kb_field_whitelist": field_whitelist,
        "alias_hints": alias_pairs,
        "kb_schema_hints": schema_hints,
        "hidden_context": hidden_context,
        "output_schema": {
            "sql": "WITH ... SELECT ...",
            "entity_mappings": [
                {
                    "type": "string",
                    "value": "string",
                    "field": "table.field",
                    "reason": "映射依据（可引用字段描述）",
                }
            ],
            "sql_fields": ["table.field"],
        },
    }
    return json.dumps(payload, ensure_ascii=False)
