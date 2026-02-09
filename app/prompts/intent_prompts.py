from __future__ import annotations

import json

INTENT_SYSTEM_PROMPT = """
你是教务系统的意图识别助手。
你的任务是判断用户当前问题的意图，并识别是否为追问。

你只能使用：
1) 当前用户问题
2) 历史中最近 4 条 user 消息

字段定义：
- intent：只能是 "chat" 或 "business_query"
- is_followup：当前问题是否依赖历史上下文
- confidence：置信度，范围 [0, 1]
- merged_query：将上下文补全后的独立问题
""".strip()


INTENT_OUTPUT_FORMAT = """
输出要求（严格）：
1) 只返回一个 JSON 对象。
2) 不要输出 markdown、代码块、解释说明或任何额外文本。
3) 不要新增未定义字段。
4) 字段及约束：
   - intent: "chat" 或 "business_query"
   - is_followup: 布尔值
   - confidence: 0 到 1 的数字
   - merged_query: 非空字符串
5) 如果 is_followup=false，merged_query 应是对当前问题的清晰改写。
6) 如果 is_followup=true，merged_query 必须补全历史上下文，形成可独立理解的问题。
""".strip()


INTENT_OUTPUT_EXAMPLES = """
示例输出 A：
{"intent":"chat","is_followup":false,"confidence":0.92,"merged_query":"今天天气怎么样？"}

示例输出 B：
{"intent":"business_query","is_followup":true,"confidence":0.88,"merged_query":"统计 2025-2026-1 学期三班近四周的缺勤率趋势"}
""".strip()


INTENT_SYSTEM_PROMPT_FULL = "\n\n".join(
    [
        INTENT_SYSTEM_PROMPT,
        "期望 JSON 结构："
        '{"intent":"chat|business_query","is_followup":true,"confidence":0.0,"merged_query":"..."}',
        INTENT_OUTPUT_FORMAT,
        INTENT_OUTPUT_EXAMPLES,
    ]
)


def build_intent_user_prompt(message: str, history_user_messages: list[str]) -> str:
    payload = {
        "message": message,
        "history_user_messages": history_user_messages[-4:],
        "schema": {
            "intent": {"type": "string", "enum": ["chat", "business_query"]},
            "is_followup": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "merged_query": {"type": "string", "minLength": 1},
        },
        "output_contract": {
            "json_only": True,
            "no_markdown_or_extra_text": True,
            "required_keys": ["intent", "is_followup", "confidence", "merged_query"],
        },
    }
    return json.dumps(payload, ensure_ascii=False)
