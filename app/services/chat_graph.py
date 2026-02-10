from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from langgraph.constants import START
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat_history import ChatHistory
from app.models.workflow_log import WorkflowLog
from app.prompts.intent_prompts import INTENT_SYSTEM_PROMPT_FULL, build_intent_user_prompt
from app.prompts.task_parse_prompts import TASK_PARSE_SYSTEM_PROMPT, build_task_parse_user_prompt
from app.schemas.chat import ChatIntentRequest

NodeIoLogger = Callable[[str, dict[str, Any], dict[str, Any] | None, str, str | None], None]


class IntentGraphState(TypedDict):
    message: str
    history_user_messages: list[str]
    threshold: float
    model_name: str | None
    result: dict[str, Any]


class TaskParseGraphState(TypedDict):
    intent_result: dict[str, Any]
    parse_result: dict[str, Any] | None


def _build_task010_intent_graph(
    node_executor: Callable[[str, list[str], float, str | None], dict[str, Any]],
    node_io_logger: NodeIoLogger | None,
):
    def _helper_route_start(_: IntentGraphState) -> str:
        return "intent_recognition"

    def _helper_intent_node(node_state: IntentGraphState) -> IntentGraphState:
        node_input = {
            "message": node_state["message"],
            "history_user_messages": node_state["history_user_messages"],
            "threshold": node_state["threshold"],
            "model_name": node_state["model_name"],
        }
        try:
            result = node_executor(
                node_state["message"],
                node_state["history_user_messages"],
                node_state["threshold"],
                node_state["model_name"],
            )
            if node_io_logger:
                node_io_logger("intent_recognition", node_input, result, "success", None)
            return {**node_state, "result": result}
        except Exception as exc:
            if node_io_logger:
                node_io_logger("intent_recognition", node_input, None, "failed", str(exc))
            raise

    graph = StateGraph(IntentGraphState)
    graph.add_node("intent_recognition", _helper_intent_node)
    graph.add_conditional_edges(
        START,
        _helper_route_start,
        {
            "intent_recognition": "intent_recognition",
        },
    )
    graph.add_edge("intent_recognition", END)
    return graph.compile()


def _build_task011_parse_graph(
    node_executor: Callable[[dict[str, Any]], dict[str, Any]],
    node_io_logger: NodeIoLogger | None,
):
    def _helper_route_start(node_state: TaskParseGraphState) -> str:
        intent = str(node_state["intent_result"].get("intent", "chat")).strip().lower()
        if intent == "business_query":
            return "task_parse"
        return "end"

    def _helper_task_parse_node(node_state: TaskParseGraphState) -> TaskParseGraphState:
        node_input = {
            "intent_result": node_state["intent_result"],
        }
        try:
            result = node_executor(node_state["intent_result"])
            if node_io_logger:
                node_io_logger("task_parse", node_input, result, "success", None)
            return {**node_state, "parse_result": result}
        except Exception as exc:
            if node_io_logger:
                node_io_logger("task_parse", node_input, None, "failed", str(exc))
            raise

    graph = StateGraph(TaskParseGraphState)
    graph.add_node("task_parse", _helper_task_parse_node)
    graph.add_conditional_edges(
        START,
        _helper_route_start,
        {
            "task_parse": "task_parse",
            "end": END,
        },
    )
    graph.add_edge("task_parse", END)
    return graph.compile()


def _format_task011_output(output: TaskParseGraphState) -> dict[str, Any]:
    parse_result = output.get("parse_result")
    if parse_result is None:
        return {
            "skipped": True,
            "task": None,
            "reason": "intent_is_chat",
        }
    return {
        "skipped": False,
        "task": parse_result,
        "reason": None,
    }


def _run_graph_manager(compiled_graph: Any, state: dict[str, Any]) -> dict[str, Any]:
    """统一图运行入口：集中执行 invoke。"""
    return compiled_graph.invoke(state)


def run_task010_intent_graph(
    message: str,
    history_user_messages: list[str],
    threshold: float,
    model_name: str | None,
    node_executor: Callable[[str, list[str], float, str | None], dict[str, Any]],
    node_io_logger: NodeIoLogger | None = None,
) -> tuple[Any, IntentGraphState]:
    """构建 TASK010 意图识别图与初始状态。"""

    state: IntentGraphState = {
        "message": message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
        "model_name": model_name,
        "result": {},
    }

    app = _build_task010_intent_graph(node_executor=node_executor, node_io_logger=node_io_logger)
    return app, state


def run_task011_parse_graph(
    intent_result: dict[str, Any],
    node_executor: Callable[[dict[str, Any]], dict[str, Any]],
    node_io_logger: NodeIoLogger | None = None,
) -> tuple[Any, TaskParseGraphState]:
    """
    执行 TASK011 任务解析图。
    规则：当 intent=chat 时直接结束，不进入 task_parse 节点。
    """

    state: TaskParseGraphState = {
        "intent_result": intent_result,
        "parse_result": None,
    }

    app = _build_task011_parse_graph(node_executor=node_executor, node_io_logger=node_io_logger)
    return app, state


def execute_task010_intent(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
) -> dict[str, Any]:
    """执行 TASK010：意图识别 + 入库。"""

    BUSINESS_KEYWORDS = [
        "学生",
        "学号",
        "教师",
        "老师",
        "课程",
        "选课",
        "成绩",
        "分数",
        "考勤",
        "缺勤",
        "出勤",
        "班级",
        "专业",
        "学院",
        "学期",
        "挂科",
        "平均分",
        "教务",
        "男生",
        "女生",
    ]
    FOLLOWUP_HINTS = [
        "这个",
        "那个",
        "上一个",
        "上一条",
        "继续",
        "再",
        "另外",
        "那",
        "同样",
        "改成",
        "换成",
        "然后",
        "还要",
    ]

    def _helper_get_recent_user_messages(session_id: str, limit: int = 4) -> list[str]:
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

    def _helper_extract_user_history(payload_history: list[dict[str, Any]] | None) -> list[str]:
        if not payload_history:
            return []
        result: list[str] = []
        for item in payload_history:
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role == "user" and content:
                result.append(content)
        return result[-4:]

    def _helper_is_followup_fallback(message: str, history_user_messages: list[str]) -> bool:
        if not history_user_messages:
            return False
        for hint in FOLLOWUP_HINTS:
            if hint in message:
                return True
        return len(message.strip()) <= 10

    def _helper_intent_fallback(message: str, history_user_messages: list[str]) -> tuple[str, float]:
        context = " ".join([*history_user_messages[-4:], message]).strip()
        hit = sum(1 for kw in BUSINESS_KEYWORDS if kw in context)
        if hit > 0:
            confidence = min(0.75 + 0.05 * hit, 0.95)
            return "business_query", float(confidence)
        return "chat", 0.85

    def _helper_merge_query_fallback(message: str, history_user_messages: list[str], is_followup: bool) -> str:
        if not is_followup:
            return message.strip()
        context = "；".join([item.strip() for item in history_user_messages if item.strip()])
        if context:
            return f"基于历史问题“{context}”，当前追问是“{message.strip()}”"
        return message.strip()

    def _helper_extract_json_object(text: str) -> dict[str, Any] | None:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _helper_llm_intent_infer(
        message: str,
        history_user_messages: list[str],
        model_name: str | None,
    ) -> dict[str, Any] | None:
        if not settings.llm_api_key:
            return None
        try:
            import httpx
            from openai import OpenAI

            model = model_name or settings.llm_model_intent
            kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
            if settings.llm_base_url:
                kwargs["base_url"] = settings.llm_base_url
            with httpx.Client(trust_env=False, timeout=20.0) as http_client:
                client = OpenAI(**kwargs, http_client=http_client)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": INTENT_SYSTEM_PROMPT_FULL},
                        {
                            "role": "user",
                            "content": build_intent_user_prompt(message, history_user_messages),
                        },
                    ],
                    temperature=0.1,
                )
            output_text = ""
            if resp.choices and resp.choices[0].message:
                output_text = resp.choices[0].message.content or ""
            return _helper_extract_json_object(output_text)
        except Exception:
            return None

    def _helper_intent_node_logic(
        message: str,
        history_user_messages: list[str],
        threshold: float,
        model_name: str | None,
    ) -> dict[str, Any]:
        llm_data = _helper_llm_intent_infer(message, history_user_messages, model_name)

        if llm_data:
            intent = str(llm_data.get("intent", "chat")).strip().lower()
            if intent not in {"chat", "business_query"}:
                intent = "chat"
            is_followup = bool(llm_data.get("is_followup", False))
            confidence = float(llm_data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            merged_query = str(llm_data.get("merged_query", "")).strip()
            if not merged_query:
                merged_query = _helper_merge_query_fallback(message, history_user_messages, is_followup)
        else:
            intent, confidence = _helper_intent_fallback(message, history_user_messages)
            is_followup = _helper_is_followup_fallback(message, history_user_messages)
            merged_query = _helper_merge_query_fallback(message, history_user_messages, is_followup)

        if confidence < threshold:
            intent = "chat"

        rewritten_query = merged_query
        return {
            "intent": intent,
            "is_followup": is_followup,
            "confidence": confidence,
            "merged_query": merged_query,
            "rewritten_query": rewritten_query,
            "threshold": threshold,
        }

    def _helper_insert_chat_history(
        session_id: str,
        user_message: str,
        rewritten_query: str,
        model_name: str | None,
    ) -> None:
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

    def _helper_insert_workflow_log(
        session_id: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
        db.add(
            WorkflowLog(
                session_id=session_id,
                step_name="intent_recognition",
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

    def _helper_save_node_io_local(
        session_id: str,
        step_name: str,
        node_input: dict[str, Any],
        node_output: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
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

    session_id = payload.session_id or uuid.uuid4().hex[:16]
    model_name = payload.model_name or (settings.llm_model_intent if settings.llm_api_key else None)
    threshold = settings.intent_confidence_threshold

    request_history = _helper_extract_user_history(
        [item.model_dump() for item in payload.history] if payload.history else None
    )
    db_history = _helper_get_recent_user_messages(session_id=session_id, limit=4)
    history_user_messages = request_history[-4:] if request_history else db_history[-4:]

    input_json = {
        "message": payload.message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
    }

    try:
        def _helper_node_logger(
            step_name: str,
            node_input: dict[str, Any],
            node_output: dict[str, Any] | None,
            status: str,
            error_message: str | None,
        ) -> None:
            _helper_save_node_io_local(
                session_id=session_id,
                step_name=step_name,
                node_input=node_input,
                node_output=node_output,
                status=status,
                error_message=error_message,
            )

        graph_app, graph_state = run_task010_intent_graph(
            message=payload.message,
            history_user_messages=history_user_messages,
            threshold=threshold,
            model_name=model_name,
            node_executor=_helper_intent_node_logic,
            node_io_logger=_helper_node_logger,
        )
        graph_output = _run_graph_manager(graph_app, graph_state)
        result = graph_output["result"]
        result["session_id"] = session_id

        _helper_insert_chat_history(
            session_id=session_id,
            user_message=payload.message,
            rewritten_query=result["rewritten_query"],
            model_name=model_name,
        )
        _helper_insert_workflow_log(
            session_id=session_id,
            input_json=input_json,
            output_json=result,
            status="success",
            error_message=None,
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        try:
            _helper_insert_workflow_log(
                session_id=session_id,
                input_json=input_json,
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            db.commit()
        except Exception:
            db.rollback()
        raise


def execute_task011_parse(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
) -> dict[str, Any]:
    """执行 TASK011：任务解析。"""

    ALLOWED_INTENTS = {"chat", "business_query"}
    ALLOWED_OPERATIONS = {"detail", "aggregate", "ranking", "trend"}
    ALLOWED_FILTER_OPS = {
        "=",
        "!=",
        ">",
        "<",
        ">=",
        "<=",
        "like",
        "in",
        "not in",
        "between",
    }
    TREND_TOKENS = ("趋势", "变化", "每月", "每周", "每日", "按月")
    RANK_TOKENS = ("top", "rank", "排名", "前十", "前5", "前五")
    AGG_TOKENS = ("多少", "总数", "人数", "数量", "平均", "占比", "比例")
    MALE_TOKENS = ("男", "男生")
    FEMALE_TOKENS = ("女", "女生")
    COUNT_TOKENS = ("多少", "总数", "数量", "人数", "几人", "多少人")
    DIMENSION_HINTS = (
        ("专业", "major.major_name"),
        ("班级", "class.class_name"),
        ("学院", "college.college_name"),
        ("课程", "course.course_name"),
    )

    def _helper_extract_json_object(text: str) -> dict[str, Any] | None:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _helper_safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except Exception:
            number = default
        return max(0.0, min(1.0, number))

    def _helper_to_unique_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            item_text = str(item).strip()
            if not item_text:
                continue
            key = item_text.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(item_text)
        return result

    def _helper_normalize_entities(value: Any) -> list[dict[str, str]]:
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
                op = "="
            filters.append(
                {
                    "field": field,
                    "op": op,
                    "value": item.get("value"),
                }
            )
        return filters

    def _helper_normalize_task_output(
        raw: dict[str, Any],
        whitelist: set[str],
        default_intent: str = "business_query",
    ) -> dict[str, Any]:
        intent = str(raw.get("intent", default_intent)).strip().lower()
        if intent not in ALLOWED_INTENTS:
            intent = default_intent if default_intent in ALLOWED_INTENTS else "chat"

        operation = str(raw.get("operation", "detail")).strip().lower()
        if operation not in ALLOWED_OPERATIONS:
            operation = "detail"

        time_range_raw = raw.get("time_range", {})
        if not isinstance(time_range_raw, dict):
            time_range_raw = {}
        start = time_range_raw.get("start")
        end = time_range_raw.get("end")
        start_text = str(start).strip() if start is not None else None
        end_text = str(end).strip() if end is not None else None

        return {
            "intent": intent,
            "entities": _helper_normalize_entities(raw.get("entities")),
            "dimensions": _helper_to_unique_str_list(raw.get("dimensions")),
            "metrics": _helper_to_unique_str_list(raw.get("metrics")),
            "filters": _helper_normalize_filters(raw.get("filters"), whitelist),
            "time_range": {
                "start": start_text or None,
                "end": end_text or None,
            },
            "operation": operation,
            "confidence": _helper_safe_float(raw.get("confidence"), default=0.0),
        }

    def _helper_preferred_field(candidates: list[str], whitelist: set[str]) -> str | None:
        for field in candidates:
            if field in whitelist:
                return field
        return None

    def _helper_infer_operation(query: str) -> str:
        lower_query = query.lower()
        if any(token in query for token in TREND_TOKENS):
            return "trend"
        if any(token in lower_query for token in RANK_TOKENS):
            return "ranking"
        if any(token in query for token in AGG_TOKENS):
            return "aggregate"
        return "detail"

    def _helper_fallback_task_parse(query: str, whitelist: set[str]) -> dict[str, Any]:
        entities: list[dict[str, str]] = []
        dimensions: list[str] = []
        metrics: list[str] = []
        filters: list[dict[str, Any]] = []

        year_match = re.search(r"((?:20)?\d{2})级", query)
        if year_match:
            year_token = year_match.group(1)
            year_num = int(year_token)
            if year_num < 100:
                year_num += 2000
            year_field = _helper_preferred_field(["student.enroll_year", "class.grade_year"], whitelist)
            if year_field:
                filters.append({"field": year_field, "op": "=", "value": year_num})
            entities.append({"type": "grade", "value": f"{year_num}级"})

        gender_field = _helper_preferred_field(["student.gender"], whitelist)
        if gender_field and any(token in query for token in MALE_TOKENS):
            filters.append({"field": gender_field, "op": "=", "value": "男"})
            entities.append({"type": "gender", "value": "男"})
        elif gender_field and any(token in query for token in FEMALE_TOKENS):
            filters.append({"field": gender_field, "op": "=", "value": "女"})
            entities.append({"type": "gender", "value": "女"})

        if any(token in query for token in COUNT_TOKENS):
            metrics.append("count")

        for key, field in DIMENSION_HINTS:
            if key in query and field in whitelist:
                dimensions.append(field)
                entities.append({"type": "dimension", "value": key})

        if not entities and query.strip():
            entities.append({"type": "query_text", "value": query.strip()[:100]})

        return {
            "intent": "business_query",
            "entities": _helper_normalize_entities(entities),
            "dimensions": _helper_to_unique_str_list(dimensions),
            "metrics": _helper_to_unique_str_list(metrics),
            "filters": _helper_normalize_filters(filters, whitelist),
            "time_range": {"start": None, "end": None},
            "operation": _helper_infer_operation(query),
            "confidence": 0.55,
        }

    def _helper_load_schema_kb() -> dict[str, Any]:
        kb_path = Path(__file__).resolve().parents[1] / "knowledge" / "schema_kb_core.json"
        return json.loads(kb_path.read_text(encoding="utf-8"))

    def _helper_build_kb_hints() -> tuple[list[str], list[dict[str, str]]]:
        kb = _helper_load_schema_kb()
        fields: list[str] = []
        alias_pairs: list[dict[str, str]] = []

        for table in kb.get("tables", []):
            table_name = str(table.get("name", "")).strip()
            if not table_name:
                continue
            for column in table.get("columns", []):
                column_name = str(column.get("name", "")).strip()
                if not column_name:
                    continue
                field = f"{table_name}.{column_name}"
                fields.append(field)

                raw_aliases = column.get("aliases", []) or []
                aliases = [str(item).strip() for item in raw_aliases if str(item).strip()]
                aliases.extend([column_name, f"{table_name}.{column_name}"])

                seen: set[str] = set()
                for alias in aliases:
                    key = alias.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    alias_pairs.append({"alias": alias, "field": field})

        return fields, alias_pairs

    def _helper_llm_task_parse(
        query: str,
        field_whitelist: list[str],
        alias_pairs: list[dict[str, str]],
        model_name: str | None,
    ) -> dict[str, Any] | None:
        if not settings.llm_api_key:
            return None
        try:
            import httpx
            from openai import OpenAI

            model = model_name or settings.llm_model_intent
            kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
            if settings.llm_base_url:
                kwargs["base_url"] = settings.llm_base_url

            with httpx.Client(trust_env=False, timeout=25.0) as http_client:
                client = OpenAI(**kwargs, http_client=http_client)
                user_prompt = build_task_parse_user_prompt(
                    query=query,
                    field_whitelist=field_whitelist,
                    alias_pairs=alias_pairs,
                )
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": TASK_PARSE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )

            text = ""
            if response.choices and response.choices[0].message:
                text = response.choices[0].message.content or ""
            return _helper_extract_json_object(text)
        except Exception:
            return None

    def _helper_task_parse_node_logic(intent_result: dict[str, Any], model_name: str | None) -> dict[str, Any]:
        query = str(
            intent_result.get("rewritten_query")
            or intent_result.get("merged_query")
            or intent_result.get("message")
            or ""
        ).strip()

        field_whitelist, alias_pairs = _helper_build_kb_hints()
        whitelist_set = set(field_whitelist)

        llm_output = _helper_llm_task_parse(
            query=query,
            field_whitelist=field_whitelist,
            alias_pairs=alias_pairs,
            model_name=model_name,
        )
        if llm_output:
            normalized = _helper_normalize_task_output(
                raw=llm_output,
                whitelist=whitelist_set,
                default_intent="business_query",
            )
            normalized["intent"] = "business_query"
            if normalized["confidence"] <= 0.0:
                normalized["confidence"] = _helper_safe_float(intent_result.get("confidence", 0.0), default=0.0)
            return normalized

        fallback_result = _helper_fallback_task_parse(query=query, whitelist=whitelist_set)
        fallback_result["confidence"] = min(
            fallback_result["confidence"],
            _helper_safe_float(intent_result.get("confidence", 0.55), default=0.55),
        )
        return fallback_result

    def _helper_insert_task_parse_log(
        session_id: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
        db.add(
            WorkflowLog(
                session_id=session_id,
                step_name="task_parse",
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

    def _helper_save_node_io_local(
        session_id: str,
        step_name: str,
        node_input: dict[str, Any],
        node_output: dict[str, Any] | None,
        status: str,
        error_message: str | None,
    ) -> None:
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

    intent_result = execute_task010_intent(db=db, admin_id=admin_id, payload=payload)
    session_id = intent_result["session_id"]
    model_name = payload.model_name or (settings.llm_model_intent if settings.llm_api_key else None)
    input_json = {"intent_result": intent_result}

    try:
        def _helper_node_logger(
            step_name: str,
            node_input: dict[str, Any],
            node_output: dict[str, Any] | None,
            status: str,
            error_message: str | None,
        ) -> None:
            _helper_save_node_io_local(
                session_id=session_id,
                step_name=step_name,
                node_input=node_input,
                node_output=node_output,
                status=status,
                error_message=error_message,
            )

        graph_app, graph_state = run_task011_parse_graph(
            intent_result=intent_result,
            node_executor=lambda node_input: _helper_task_parse_node_logic(node_input, model_name=model_name),
            node_io_logger=_helper_node_logger,
        )
        graph_output = _run_graph_manager(graph_app, graph_state)
        parse_stage = _format_task011_output(graph_output)
        result = {
            "session_id": session_id,
            "intent": intent_result["intent"],
            "is_followup": intent_result["is_followup"],
            "merged_query": intent_result["merged_query"],
            "rewritten_query": intent_result["rewritten_query"],
            "skipped": parse_stage["skipped"],
            "reason": parse_stage["reason"],
            "task": parse_stage["task"],
        }

        _helper_insert_task_parse_log(
            session_id=session_id,
            input_json=input_json,
            output_json=result,
            status="success",
            error_message=None,
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        try:
            _helper_insert_task_parse_log(
                session_id=session_id,
                input_json=input_json,
                output_json=None,
                status="failed",
                error_message=str(exc),
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
