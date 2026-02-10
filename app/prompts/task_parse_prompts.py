from __future__ import annotations

import json
from typing import Any

TASK_PARSE_SYSTEM_PROMPT = """
你是教务查询任务解析助手。
请把用户问题解析为结构化任务对象，用于后续 SQL 生成。

硬性要求：
1) 只输出一个 JSON 对象，不要输出 markdown 或解释文字。
2) 字段必须包含：
   - intent: "chat" | "business_query"
   - entities: [{type, value}]
   - dimensions: [string]
   - metrics: [string]
   - filters: [{field, op, value}]
   - time_range: {start, end}
   - operation: "detail" | "aggregate" | "ranking" | "trend"
   - confidence: 0~1
3) filters.field 必须是 table.field 形式。
4) filters.field 必须来自给定知识库字段白名单。
5) 如果问题是闲聊，intent=chat，其他字段尽量置空数组或空值。
""".strip()


def build_task_parse_user_prompt(
    query: str,
    field_whitelist: list[str],
    alias_pairs: list[dict[str, str]],
) -> str:
    payload: dict[str, Any] = {
        "query": query,
        "kb_field_whitelist": field_whitelist,
        "alias_hints": alias_pairs,
        "output_schema": {
            "intent": "chat|business_query",
            "entities": [{"type": "string", "value": "string"}],
            "dimensions": ["string"],
            "metrics": ["string"],
            "filters": [{"field": "table.field", "op": "=", "value": "string|number|boolean"}],
            "time_range": {"start": "YYYY-MM-DD|null", "end": "YYYY-MM-DD|null"},
            "operation": "detail|aggregate|ranking|trend",
            "confidence": "0~1",
        },
    }
    return json.dumps(payload, ensure_ascii=False)

