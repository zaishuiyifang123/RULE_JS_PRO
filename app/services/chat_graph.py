from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from langgraph.constants import START
from langgraph.graph import END, StateGraph
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat_history import ChatHistory
from app.models.workflow_log import WorkflowLog
from app.prompts.intent_prompts import INTENT_SYSTEM_PROMPT_FULL, build_intent_user_prompt
from app.prompts.sql_generation_prompts import SQL_GENERATION_SYSTEM_PROMPT, build_sql_generation_user_prompt
from app.prompts.task_parse_prompts import TASK_PARSE_SYSTEM_PROMPT, build_task_parse_user_prompt
from app.schemas.chat import ChatIntentRequest


class UnifiedChatGraphState(TypedDict):
    message: str
    history_user_messages: list[str]
    threshold: float
    model_name: str
    intent_result: dict[str, Any] | None
    parse_result: dict[str, Any] | None
    sql_result: dict[str, Any] | None
    sql_validate_result: dict[str, Any] | None
    hidden_context_result: dict[str, Any] | None
    hidden_context_retry_count: int


def execute_chat_workflow(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
) -> dict[str, Any]:
    """执行统一聊天工作流（TASK010/TASK011/TASK015/TASK016）。"""

    ALLOWED_INTENTS = {"chat", "business_query"}
    ALLOWED_OPERATIONS = {"detail", "aggregate", "ranking", "trend"}
    ALLOWED_FILTER_OPS = {"=", "!=", ">", "<", ">=", "<=", "like", "in", "not in", "between"}
    HIDDEN_CONTEXT_MAX_RETRY = 2

    def _helper_get_recent_user_messages(session_id: str, limit: int = 4) -> list[str]:
        """读取同一会话最近的 user 消息。"""

        rows = (
            db.query(ChatHistory)
            .filter(
                ChatHistory.session_id == session_id,
                ChatHistory.message_role == "user",
                ChatHistory.is_deleted == False,
            )
            .order_by(ChatHistory.created_at.desc(), ChatHistory.id.desc())
            .limit(limit)
            .all()
        )
        return [row.message_content for row in reversed(rows)]

    def _helper_extract_json_object(text_value: str) -> dict[str, Any] | None:
        """从模型输出文本中提取 JSON。"""

        match = re.search(r"\{.*\}", text_value, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _helper_safe_float(value: Any, default: float = 0.0) -> float:
        """安全转换浮点并裁剪到 [0,1]。"""

        try:
            number = float(value)
        except Exception:
            number = default
        return max(0.0, min(1.0, number))

    def _helper_to_unique_str_list(value: Any) -> list[str]:
        """标准化字符串数组并去重。"""

        if not isinstance(value, list):
            return []
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            text_value = str(item).strip()
            if not text_value:
                continue
            key = text_value.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(text_value)
        return result

    def _helper_normalize_entities(value: Any) -> list[dict[str, str]]:
        """标准化 entities。"""

        if not isinstance(value, list):
            return []
        entities: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            entity_type = str(item.get("type", "")).strip()
            entity_value = str(item.get("value", "")).strip()
            if not entity_type or not entity_value:
                continue
            entities.append({"type": entity_type, "value": entity_value})
        return entities

    def _helper_normalize_filters(value: Any, whitelist: set[str]) -> list[dict[str, Any]]:
        """标准化 filters 并校验字段白名单。"""

        if not isinstance(value, list):
            return []
        filters: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field", "")).strip()
            if field not in whitelist:
                continue
            op = str(item.get("op", "=")).strip().lower() or "="
            if op not in ALLOWED_FILTER_OPS:
                continue
            filters.append({"field": field, "op": op, "value": item.get("value")})
        return filters

    def _helper_extract_sql_fields(sql: str) -> list[str]:
        """提取 SQL 中的 table.field 并去重。"""

        matches = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b", sql)
        result: list[str] = []
        seen: set[str] = set()
        for table_name, column_name in matches:
            field = f"{table_name}.{column_name}"
            key = field.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(field)
        return result

    def _helper_extract_cte_names(sql: str) -> set[str]:
        """提取 WITH 子句中定义的 CTE 名称。"""

        names = re.findall(r"(?is)(?:\bwith\b|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", sql)
        return {name.lower() for name in names}

    def _helper_normalize_entity_mappings(value: Any, whitelist: set[str]) -> list[dict[str, str]]:
        """标准化 entity_mappings 并校验字段白名单。"""

        if not isinstance(value, list):
            return []
        mappings: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            entity_type = str(item.get("type", "")).strip()
            entity_value = str(item.get("value", "")).strip()
            field = str(item.get("field", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if not entity_type or not entity_value or not field:
                continue
            if field not in whitelist:
                continue
            mappings.append(
                {
                    "type": entity_type,
                    "value": entity_value,
                    "field": field,
                    "reason": reason,
                }
            )
        return mappings

    def _helper_is_readonly_sql(sql: str) -> bool:
        """仅允许查询 SQL。"""

        stripped = sql.strip().lower()
        if not stripped:
            return False
        if not (stripped.startswith("select") or stripped.startswith("with")):
            return False
        forbidden_tokens = [
            "insert",
            "update",
            "delete",
            "replace",
            "alter",
            "drop",
            "truncate",
            "create",
            "grant",
            "revoke",
        ]
        for token in forbidden_tokens:
            if re.search(rf"\b{token}\b", stripped):
                return False
        return True

    def _helper_build_kb_hints() -> tuple[list[str], list[dict[str, list[str]]], list[dict[str, Any]]]:
        """构建字段白名单、字段别名提示与结构化描述提示。"""

        kb_path = Path(__file__).resolve().parents[1] / "knowledge" / "schema_kb_core.json"
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        fields: list[str] = []
        alias_pairs: list[dict[str, list[str]]] = []
        schema_hints: list[dict[str, Any]] = []

        for table in kb.get("tables", []):
            table_name = str(table.get("name", "")).strip()
            if not table_name:
                continue
            table_description = str(table.get("description", "")).strip()
            table_columns: list[dict[str, Any]] = []
            for column in table.get("columns", []):
                column_name = str(column.get("name", "")).strip()
                if not column_name:
                    continue
                field = f"{table_name}.{column_name}"
                fields.append(field)

                raw_aliases = column.get("aliases", []) or []
                aliases = [str(item).strip() for item in raw_aliases if str(item).strip()]
                aliases.extend([column_name, field])

                dedup_aliases: list[str] = []
                seen: set[str] = set()
                for alias in aliases:
                    key = alias.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    dedup_aliases.append(alias)
                alias_pairs.append({field: dedup_aliases})
                table_columns.append(
                    {
                        "field": field,
                        "field_description": str(column.get("description", "")).strip(),
                        "aliases": dedup_aliases,
                    }
                )

            schema_hints.append(
                {
                    "table": table_name,
                    "table_description": table_description,
                    "columns": table_columns,
                }
            )

        return fields, alias_pairs, schema_hints

    def _helper_call_llm(system_prompt: str, user_prompt: str, model_name: str, timeout: float) -> dict[str, Any]:
        """调用大模型并解析 JSON。"""

        import httpx
        from openai import OpenAI

        if not settings.llm_api_key:
            raise RuntimeError("未配置 LLM_API_KEY，无法执行工作流")
        if not model_name:
            raise RuntimeError("未配置模型名，无法执行工作流")

        try:
            kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
            if settings.llm_base_url:
                kwargs["base_url"] = settings.llm_base_url
            with httpx.Client(trust_env=False, timeout=timeout) as http_client:
                client = OpenAI(**kwargs, http_client=http_client)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )
        except Exception as exc:
            raise RuntimeError(f"大模型调用失败: {exc}") from exc

        output_text = ""
        if response.choices and response.choices[0].message:
            output_text = response.choices[0].message.content or ""
        output_data = _helper_extract_json_object(output_text)
        if not output_data:
            raise ValueError("模型输出不是有效 JSON")
        return output_data

    def _helper_intent_node_logic(
        message: str,
        history_user_messages: list[str],
        threshold: float,
        model_name: str,
    ) -> dict[str, Any]:
        """意图识别节点业务逻辑。"""

        llm_data = _helper_call_llm(
            system_prompt=INTENT_SYSTEM_PROMPT_FULL,
            user_prompt=build_intent_user_prompt(message, history_user_messages),
            model_name=model_name,
            timeout=20.0,
        )

        intent = str(llm_data.get("intent", "")).strip().lower()
        if intent not in ALLOWED_INTENTS:
            raise ValueError(f"意图识别输出了非法 intent: {intent}")

        confidence = _helper_safe_float(llm_data.get("confidence", None), default=-1.0)
        if confidence < 0.0:
            raise ValueError("意图识别缺少有效 confidence 字段")

        merged_query = str(llm_data.get("merged_query", "")).strip()
        rewritten_query = str(llm_data.get("rewritten_query", merged_query)).strip()
        if not merged_query or not rewritten_query:
            raise ValueError("意图识别缺少 merged_query 或 rewritten_query")

        if confidence < threshold:
            intent = "chat"
        result = {
            "intent": intent,
            "is_followup": bool(llm_data.get("is_followup", False)),
            "confidence": confidence,
            "merged_query": merged_query,
            "rewritten_query": rewritten_query,
            "threshold": threshold,
        }
        print("意图识别节点输出:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def _helper_task_parse_node_logic(intent_result: dict[str, Any], model_name: str) -> dict[str, Any]:
        """任务解析节点业务逻辑。"""

        query = str(
            intent_result.get("rewritten_query")
            or intent_result.get("merged_query")
            or intent_result.get("message")
            or ""
        ).strip()
        if not query:
            raise ValueError("任务解析缺少 query")

        field_whitelist, alias_pairs, _ = _helper_build_kb_hints()
        whitelist_set = set(field_whitelist)

        llm_output = _helper_call_llm(
            system_prompt=TASK_PARSE_SYSTEM_PROMPT,
            user_prompt=build_task_parse_user_prompt(
                query=query,
                field_whitelist=field_whitelist,
                alias_pairs=alias_pairs,
            ),
            model_name=model_name,
            timeout=25.0,
        )

        intent = str(llm_output.get("intent", "")).strip().lower()
        if intent not in ALLOWED_INTENTS:
            raise ValueError(f"任务解析输出了非法 intent: {intent}")

        operation = str(llm_output.get("operation", "")).strip().lower()
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"任务解析输出了非法 operation: {operation}")

        time_range_raw = llm_output.get("time_range")
        if not isinstance(time_range_raw, dict):
            raise ValueError("任务解析缺少有效 time_range")

        confidence = _helper_safe_float(llm_output.get("confidence", None), default=-1.0)
        if confidence < 0.0:
            raise ValueError("任务解析缺少有效 confidence 字段")

        result = {
            "intent": "business_query",
            "entities": _helper_normalize_entities(llm_output.get("entities")),
            "dimensions": _helper_to_unique_str_list(llm_output.get("dimensions")),
            "metrics": _helper_to_unique_str_list(llm_output.get("metrics")),
            "filters": _helper_normalize_filters(llm_output.get("filters"), whitelist_set),
            "time_range": {
                "start": str(time_range_raw.get("start")).strip() if time_range_raw.get("start") not in (None, "") else None,
                "end": str(time_range_raw.get("end")).strip() if time_range_raw.get("end") not in (None, "") else None,
            },
            "operation": operation,
            "confidence": confidence,
        }
        print("任务解析节点输出:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def _helper_sql_generation_node_logic(
        rewritten_query: str,
        parse_result: dict[str, Any],
        hidden_context_result: dict[str, Any] | None,
        model_name: str,
    ) -> dict[str, Any]:
        """SQL 生成节点业务逻辑。"""

        if not isinstance(parse_result, dict):
            raise ValueError("SQL 生成缺少有效任务解析结果")
        if str(parse_result.get("intent", "")).strip().lower() != "business_query":
            raise ValueError("SQL 生成仅支持 business_query")

        field_whitelist, alias_pairs, schema_hints = _helper_build_kb_hints()
        whitelist_set = set(field_whitelist)

        llm_output = _helper_call_llm(
            system_prompt=SQL_GENERATION_SYSTEM_PROMPT,
            user_prompt=build_sql_generation_user_prompt(
                rewritten_query=rewritten_query,
                task=parse_result,
                field_whitelist=field_whitelist,
                alias_pairs=alias_pairs,
                schema_hints=schema_hints,
                hidden_context=hidden_context_result,
            ),
            model_name=model_name,
            timeout=30.0,
        )

        sql = str(llm_output.get("sql", "")).strip()
        if not sql:
            raise ValueError("SQL 生成缺少 sql 字段")
        if not re.search(r"^\s*with\b", sql, flags=re.I):
            raise ValueError("SQL 生成未使用 WITH（CTE）")

        sql_fields = _helper_extract_sql_fields(sql)
        if not sql_fields:
            raise ValueError("SQL 中未识别到 table.field 字段")
        cte_names = _helper_extract_cte_names(sql)
        invalid_fields: list[str] = []
        for field in sql_fields:
            table_name = field.split(".", 1)[0].lower()
            if table_name in cte_names:
                continue
            if field not in whitelist_set:
                invalid_fields.append(field)
        if invalid_fields:
            raise ValueError(f"SQL 包含非白名单字段: {invalid_fields}")

        entity_mappings = _helper_normalize_entity_mappings(llm_output.get("entity_mappings"), whitelist_set)
        entities = _helper_normalize_entities(parse_result.get("entities"))
        for entity in entities:
            entity_type = entity["type"]
            entity_value = entity["value"]
            target_mapping = next(
                (
                    mapping
                    for mapping in entity_mappings
                    if mapping["type"] == entity_type and mapping["value"] == entity_value
                ),
                None,
            )
            if not target_mapping:
                raise ValueError(f"关键实体映射失败: type={entity_type}, value={entity_value}")
            if target_mapping["field"] not in sql_fields:
                raise ValueError(
                    f"关键实体映射字段未出现在 SQL 中: type={entity_type}, value={entity_value}, field={target_mapping['field']}"
                )

        result = {
            "sql": sql,
            "entity_mappings": entity_mappings,
            "sql_fields": sql_fields,
        }
        print("SQL 生成节点输出:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def _helper_sql_validate_node_logic(sql_result: dict[str, Any] | None) -> dict[str, Any]:
        """SQL 验证节点：真实执行 SQL 并返回完整结果或报错。"""

        sql = str((sql_result or {}).get("sql", "")).strip()
        if not sql:
            v_result = {
                "is_valid": False,
                "error": "SQL 验证缺少 sql",
                "rows": 0,
                "result": [],
                "executed_sql": "",
            }
            print("SQL验证节点输出：")
            print(json.dumps(v_result, indent=2, ensure_ascii=False))
            return v_result


        if not _helper_is_readonly_sql(sql):
            v_result = {
                "is_valid": False,
                "error": "SQL 验证失败：仅允许查询语句（SELECT/WITH）",
                "rows": 0,
                "result": [],
                "executed_sql": sql,
            }
            print("SQL验证节点输出：")
            print(json.dumps(v_result, indent=2, ensure_ascii=False))
            return v_result


        try:
            rows = db.execute(text(sql)).mappings().all()
            result_rows = [dict(row) for row in rows]
            v_result =  {
                "is_valid": True,
                "error": None,
                "rows": len(result_rows),
                "result": result_rows,
                "executed_sql": sql,
            }
            print("SQL验证节点输出：")
            print(json.dumps(v_result, indent=2, ensure_ascii=False))
            return v_result

        except Exception as exc:
            v_result = {
                "is_valid": False,
                "error": str(exc),
                "rows": 0,
                "result": [],
                "executed_sql": sql,
            }
            print("SQL验证节点输出：")
            print(json.dumps(v_result, indent=2, ensure_ascii=False))
            return v_result

    def _helper_hidden_context_node_logic(
        rewritten_query: str,
        parse_result: dict[str, Any] | None,
        sql_result: dict[str, Any] | None,
        sql_validate_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """隐藏上下文探索节点：基于 SQL 报错做只读探测并产出补充上下文。"""

        error_text = str((sql_validate_result or {}).get("error") or "").strip()
        failed_sql = str((sql_result or {}).get("sql") or "").strip()
        error_lower = error_text.lower()

        error_type = "execution_error"
        if "unknown column" in error_lower:
            error_type = "unknown_column"
        elif "unknown table" in error_lower:
            error_type = "unknown_table"
        elif "syntax" in error_lower:
            error_type = "syntax_error"
        elif "doesn't exist" in error_lower:
            error_type = "object_not_found"

        field_whitelist, alias_pairs, schema_hints = _helper_build_kb_hints()
        whitelist_set = set(field_whitelist)

        parse_filters = (parse_result or {}).get("filters") if isinstance(parse_result, dict) else []
        parse_dimensions = (parse_result or {}).get("dimensions") if isinstance(parse_result, dict) else []
        entity_mappings = (sql_result or {}).get("entity_mappings") if isinstance(sql_result, dict) else []

        candidate_fields: list[str] = []
        for item in parse_filters or []:
            if isinstance(item, dict):
                field = str(item.get("field", "")).strip()
                if field in whitelist_set:
                    candidate_fields.append(field)
        for field in parse_dimensions or []:
            field_text = str(field).strip()
            if field_text in whitelist_set:
                candidate_fields.append(field_text)
        for mapping in entity_mappings or []:
            if isinstance(mapping, dict):
                field = str(mapping.get("field", "")).strip()
                if field in whitelist_set:
                    candidate_fields.append(field)

        dedup_fields: list[str] = []
        seen_fields: set[str] = set()
        for field in candidate_fields:
            key = field.lower()
            if key in seen_fields:
                continue
            seen_fields.add(key)
            dedup_fields.append(field)
        dedup_fields = dedup_fields[:8]

        probe_samples: list[dict[str, Any]] = []
        for field in dedup_fields:
            table_name, column_name = field.split(".", 1)
            probe_sql = (
                f"SELECT DISTINCT {table_name}.{column_name} AS value "
                f"FROM {table_name} "
                f"WHERE {table_name}.{column_name} IS NOT NULL AND {table_name}.is_deleted = 0 "
                f"LIMIT 20"
            )
            try:
                rows = db.execute(text(probe_sql)).mappings().all()
                values = [str(row.get("value")) for row in rows if row.get("value") is not None]
                probe_samples.append(
                    {
                        "field": field,
                        "probe_sql": probe_sql,
                        "values": values,
                    }
                )
            except Exception as exc:
                probe_samples.append(
                    {
                        "field": field,
                        "probe_sql": probe_sql,
                        "values": [],
                        "error": str(exc),
                    }
                )

        missing_token = ""
        match_single = re.search(r"Unknown column '([^']+)'", error_text, flags=re.I)
        match_tick = re.search(r"Unknown column `([^`]+)`", error_text, flags=re.I)
        if match_single:
            missing_token = match_single.group(1).strip()
        elif match_tick:
            missing_token = match_tick.group(1).strip()

        alias_lookup: dict[str, list[str]] = {}
        for alias_item in alias_pairs:
            if isinstance(alias_item, dict):
                for field, aliases in alias_item.items():
                    alias_lookup[field] = [str(alias).strip().lower() for alias in aliases if str(alias).strip()]

        field_candidates: list[dict[str, Any]] = []
        if missing_token:
            missing_suffix = missing_token.split(".")[-1].strip().lower()
            candidates: list[str] = []
            for field in field_whitelist:
                field_lower = field.lower()
                if field_lower.endswith(f".{missing_suffix}"):
                    candidates.append(field)
                    continue
                aliases = alias_lookup.get(field, [])
                if missing_suffix in aliases:
                    candidates.append(field)
            field_candidates.append(
                {
                    "missing": missing_token,
                    "candidates": candidates[:12],
                }
            )

        hints: list[str] = [f"error_type={error_type}"]
        if missing_token:
            hints.append(f"missing_token={missing_token}")
        if dedup_fields:
            hints.append("use_probe_samples_to_rewrite_filters_or_entities")
        hints.append("retry_sql_generation_with_hidden_context")

        hc_result = {
            "error_type": error_type,
            "error": error_text,
            "failed_sql": failed_sql,
            "rewritten_query": rewritten_query,
            "field_candidates": field_candidates,
            "probe_samples": probe_samples,
            "hints": hints,
            "kb_summary": {
                "table_count": len(schema_hints),
                "field_count": len(field_whitelist),
            },
        }
        print("闅愯棌涓婁笅鏂囨帰绱㈣妭鐐硅緭鍑?")
        print(json.dumps(hc_result, indent=2, ensure_ascii=False))
        return hc_result

    def _helper_insert_workflow_log(
        session_id: str,
        step_name: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
        """插入工作流日志。"""

        db.add(
            WorkflowLog(
                session_id=session_id,
                step_name=step_name,
                input_json=input_json,
                output_json=output_json,
                status=status,
                error_message=error_message,
                risk_level="low",
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            )
        )

    def _helper_insert_chat_history(
        session_id: str,
        user_message: str,
        rewritten_query: str,
        model_name: str,
    ) -> None:
        """插入一轮 user + assistant 会话。"""

        db.add(
            ChatHistory(
                admin_id=admin_id,
                session_id=session_id,
                message_role="user",
                message_content=user_message,
                model_name=model_name,
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            )
        )
        db.add(
            ChatHistory(
                admin_id=admin_id,
                session_id=session_id,
                message_role="assistant",
                message_content=rewritten_query,
                model_name=model_name,
                created_by=admin_id,
                updated_by=admin_id,
                is_deleted=False,
            )
        )

    def _helper_save_node_io_local(
        session_id: str,
        step_name: str,
        node_input: dict[str, Any],
        node_output: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
        """保存节点输入输出到本地。"""

        root = Path(settings.node_io_log_dir)
        step_dir = root / session_id / step_name
        step_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H-%M-%S-%f")
        file_path = step_dir / f"{ts}-{status}.json"
        payload_data = {
            "session_id": session_id,
            "admin_id": admin_id,
            "step_name": step_name,
            "status": status,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "input": node_input,
            "output": node_output,
        }
        file_path.write_text(json.dumps(payload_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _helper_node_logger(
        step_name: str,
        node_input: dict[str, Any],
        node_output: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
        """节点日志包装。"""

        _helper_save_node_io_local(
            session_id=session_id,
            step_name=step_name,
            node_input=node_input,
            node_output=node_output,
            status=status,
            error_message=error_message,
        )

    def _helper_intent_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        """图中的意图识别节点。"""

        node_input = {
            "message": state["message"],
            "history_user_messages": state["history_user_messages"],
            "threshold": state["threshold"],
            "model_name": state["model_name"],
        }
        try:
            intent_result = _helper_intent_node_logic(
                message=state["message"],
                history_user_messages=state["history_user_messages"],
                threshold=state["threshold"],
                model_name=state["model_name"],
            )
            _helper_node_logger("intent_recognition", node_input, intent_result, "success", None)
            return {**state, "intent_result": intent_result}
        except Exception as exc:
            _helper_node_logger("intent_recognition", node_input, None, "failed", str(exc))
            raise

    def _helper_task_parse_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        """图中的任务解析节点。"""

        intent_result = state.get("intent_result") or {}
        node_input = {"intent_result": intent_result}
        try:
            parse_result = _helper_task_parse_node_logic(intent_result=intent_result, model_name=state["model_name"])
            _helper_node_logger("task_parse", node_input, parse_result, "success", None)
            return {**state, "parse_result": parse_result}
        except Exception as exc:
            _helper_node_logger("task_parse", node_input, None, "failed", str(exc))
            raise

    def _helper_sql_generation_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        """图中的 SQL 生成节点。"""

        parse_result = state.get("parse_result") or {}
        hidden_context_result = state.get("hidden_context_result")
        rewritten_query = str((state.get("intent_result") or {}).get("rewritten_query", state["message"])).strip()
        node_input = {
            "rewritten_query": rewritten_query,
            "parse_result": parse_result,
            "hidden_context_result": hidden_context_result,
        }
        try:
            sql_result = _helper_sql_generation_node_logic(
                rewritten_query=rewritten_query,
                parse_result=parse_result,
                hidden_context_result=hidden_context_result,
                model_name=state["model_name"],
            )
            _helper_node_logger("sql_generation", node_input, sql_result, "success", None)
            return {**state, "sql_result": sql_result}
        except Exception as exc:
            _helper_node_logger("sql_generation", node_input, None, "failed", str(exc))
            raise

    def _helper_sql_validate_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        """图中的 SQL 验证节点。"""

        node_input = {"sql_result": state.get("sql_result")}
        validate_result = _helper_sql_validate_node_logic(sql_result=state.get("sql_result"))
        status = "success" if validate_result.get("is_valid") else "failed"
        _helper_node_logger("sql_validate", node_input, validate_result, status, validate_result.get("error"))
        return {**state, "sql_validate_result": validate_result}

    def _helper_hidden_context_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        current_retry_count = int(state.get("hidden_context_retry_count") or 0)
        rewritten_query = str((state.get("intent_result") or {}).get("rewritten_query", state["message"])).strip()
        parse_result = state.get("parse_result")
        sql_result = state.get("sql_result")
        sql_validate_result = state.get("sql_validate_result")
        node_input = {
            "rewritten_query": rewritten_query,
            "parse_result": parse_result,
            "sql_result": sql_result,
            "sql_validate_result": sql_validate_result,
            "hidden_context_retry_count": current_retry_count,
        }
        try:
            hidden_context_result = _helper_hidden_context_node_logic(
                rewritten_query=rewritten_query,
                parse_result=parse_result,
                sql_result=sql_result,
                sql_validate_result=sql_validate_result,
            )
            next_retry_count = current_retry_count + 1
            hidden_context_result["retry_count"] = next_retry_count
            _helper_node_logger("hidden_context", node_input, hidden_context_result, "success", None)
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="hidden_context",
                input_json=node_input,
                output_json=hidden_context_result,
                status="success",
                error_message=None,
            )
            return {
                **state,
                "hidden_context_result": hidden_context_result,
                "hidden_context_retry_count": next_retry_count,
            }
        except Exception as exc:
            _helper_node_logger("hidden_context", node_input, None, "failed", str(exc))
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="hidden_context",
                input_json=node_input,
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            raise

    def _helper_result_return_node(state: UnifiedChatGraphState) -> UnifiedChatGraphState:
        return state

    def _helper_build_graph():
        """构建统一工作流图。"""

        def _helper_route_after_intent(state: UnifiedChatGraphState) -> str:
            intent_result = state.get("intent_result") or {}
            intent = str(intent_result.get("intent", "chat")).strip().lower()
            if intent == "business_query":
                return "task_parse"
            return "result_return"

        def _helper_route_after_sql_validate(state: UnifiedChatGraphState) -> str:
            validate_result = state.get("sql_validate_result") or {}
            if bool(validate_result.get("is_valid")):
                return "result_return"
            retry_count = int(state.get("hidden_context_retry_count") or 0)
            if retry_count >= HIDDEN_CONTEXT_MAX_RETRY:
                return "result_return"
            return "hidden_context"

        def _helper_route_after_hidden_context(state: UnifiedChatGraphState) -> str:
            retry_count = int(state.get("hidden_context_retry_count") or 0)
            if retry_count > HIDDEN_CONTEXT_MAX_RETRY:
                return "result_return"
            return "sql_generation"

        graph = StateGraph(UnifiedChatGraphState)
        graph.add_node("intent_recognition", _helper_intent_node)
        graph.add_node("task_parse", _helper_task_parse_node)
        graph.add_node("sql_generation", _helper_sql_generation_node)
        graph.add_node("sql_validate", _helper_sql_validate_node)
        graph.add_node("hidden_context", _helper_hidden_context_node)
        graph.add_node("result_return", _helper_result_return_node)
        graph.add_edge(START, "intent_recognition")
        graph.add_conditional_edges(
            "intent_recognition",
            _helper_route_after_intent,
            {"task_parse": "task_parse", "result_return": "result_return"},
        )
        graph.add_edge("task_parse", "sql_generation")
        graph.add_edge("sql_generation", "sql_validate")
        graph.add_conditional_edges(
            "sql_validate",
            _helper_route_after_sql_validate,
            {"hidden_context": "hidden_context", "result_return": "result_return"},
        )
        graph.add_conditional_edges(
            "hidden_context",
            _helper_route_after_hidden_context,
            {"sql_generation": "sql_generation", "result_return": "result_return"},
        )
        graph.add_edge("result_return", END)
        return graph.compile()

    session_id = payload.session_id or uuid.uuid4().hex[:16]
    if not settings.llm_api_key:
        raise RuntimeError("未配置 LLM_API_KEY，无法执行工作流")
    model_name = payload.model_name or settings.llm_model_intent
    if not model_name:
        raise RuntimeError("未配置 llm_model_intent，无法执行工作流")

    threshold = settings.intent_confidence_threshold
    history_user_messages = _helper_get_recent_user_messages(session_id=session_id, limit=4)[-4:]

    graph_state: UnifiedChatGraphState = {
        "message": payload.message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
        "model_name": model_name,
        "intent_result": None,
        "parse_result": None,
        "sql_result": None,
        "sql_validate_result": None,
        "hidden_context_result": None,
        "hidden_context_retry_count": 0,
    }
    input_json = {
        "message": payload.message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
    }

    try:
        graph_app = _helper_build_graph()
        graph_output = graph_app.invoke(graph_state)
        intent_result = graph_output.get("intent_result") or {}
        parse_result = graph_output.get("parse_result")
        sql_result = graph_output.get("sql_result")
        sql_validate_result = graph_output.get("sql_validate_result")
        hidden_context_result = graph_output.get("hidden_context_result")
        hidden_context_retry_count = int(graph_output.get("hidden_context_retry_count") or 0)

        skipped = parse_result is None
        result = {
            "session_id": session_id,
            "intent": intent_result.get("intent", "chat"),
            "is_followup": bool(intent_result.get("is_followup", False)),
            "merged_query": str(intent_result.get("merged_query", payload.message)).strip(),
            "rewritten_query": str(intent_result.get("rewritten_query", payload.message)).strip(),
            "skipped": skipped,
            "reason": "intent_is_chat" if skipped else None,
            "task": parse_result,
            "sql_result": sql_result,
            "sql_validate_result": sql_validate_result,
            "hidden_context_result": hidden_context_result,
            "hidden_context_retry_count": hidden_context_retry_count,
        }

        _helper_insert_chat_history(
            session_id=session_id,
            user_message=payload.message,
            rewritten_query=result["rewritten_query"],
            model_name=model_name,
        )
        _helper_insert_workflow_log(
            session_id=session_id,
            step_name="intent_recognition",
            input_json=input_json,
            output_json=intent_result,
            status="success",
            error_message=None,
        )
        if not skipped:
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="task_parse",
                input_json={"intent_result": intent_result},
                output_json=parse_result,
                status="success",
                error_message=None,
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="sql_generation",
                input_json={"rewritten_query": result["rewritten_query"], "task": parse_result},
                output_json=sql_result,
                status="success",
                error_message=None,
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="sql_validate",
                input_json={"sql_result": sql_result},
                output_json=sql_validate_result,
                status="success" if (sql_validate_result or {}).get("is_valid") else "failed",
                error_message=(sql_validate_result or {}).get("error"),
            )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        try:
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="intent_recognition",
                input_json=input_json,
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="task_parse",
                input_json={"message": payload.message},
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="sql_generation",
                input_json={"message": payload.message},
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="sql_validate",
                input_json={"message": payload.message},
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            _helper_insert_workflow_log(
                session_id=session_id,
                step_name="hidden_context",
                input_json={"message": payload.message},
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
