from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat_history import ChatHistory
from app.models.workflow_log import WorkflowLog
from app.schemas.chat import ChatIntentRequest
from app.services.chat_graph import run_task010_intent_graph

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


def _get_recent_user_messages(db: Session, session_id: str, limit: int = 4) -> list[str]:
    """从数据库获取最近 N 条 user 消息，按时间正序返回。"""
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


def _extract_user_history(payload_history: list[dict[str, Any]] | None) -> list[str]:
    """从请求中的 history 提取 user 消息。"""
    if not payload_history:
        return []
    result: list[str] = []
    for item in payload_history:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role == "user" and content:
            result.append(content)
    return result[-4:]


def _is_followup_fallback(message: str, history_user_messages: list[str]) -> bool:
    """追问兜底规则：有历史且当前问句依赖上下文指代。"""
    if not history_user_messages:
        return False
    for hint in FOLLOWUP_HINTS:
        if hint in message:
            return True
    if len(message.strip()) <= 10:
        return True
    return False


def _intent_fallback(message: str, history_user_messages: list[str]) -> tuple[str, float]:
    """意图兜底规则：结合最近 user 历史与当前问题判定业务查询。"""
    context = " ".join([*history_user_messages[-4:], message]).strip()
    hit = sum(1 for kw in BUSINESS_KEYWORDS if kw in context)
    if hit > 0:
        confidence = min(0.75 + 0.05 * hit, 0.95)
        return "business_query", float(confidence)
    return "chat", 0.85


def _merge_query_fallback(message: str, history_user_messages: list[str], is_followup: bool) -> str:
    """合并兜底规则：追问时拼接历史，否则返回当前问题。"""
    if not is_followup:
        return message.strip()
    context = "；".join([item.strip() for item in history_user_messages if item.strip()])
    if context:
        return f"基于历史问题“{context}”，当前追问为“{message.strip()}”"
    return message.strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _llm_intent_infer(
    message: str,
    history_user_messages: list[str],
    model_name: str | None,
) -> dict[str, Any] | None:
    """可选 LLM 推理：返回 intent/is_followup/confidence/merged_query。"""
    if not settings.llm_api_key:
        return None
    try:
        from openai import OpenAI

        model = model_name or settings.llm_model_intent
        kwargs = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        client = OpenAI(**kwargs)

        system_prompt = (
            "你是教务系统意图识别助手。"
            "请严格输出 JSON，对用户问题进行意图识别与追问判断。"
            "意图仅允许 chat 或 business_query。"
            "只可参考最近4条user消息。"
            "若是追问，请合并历史得到 merged_query。"
            "confidence 必须在 0 到 1 之间。"
        )
        user_prompt = json.dumps(
            {
                "message": message,
                "history_user_messages": history_user_messages[-4:],
                "schema": {
                    "intent": "chat|business_query",
                    "is_followup": "bool",
                    "confidence": "float(0~1)",
                    "merged_query": "string",
                },
            },
            ensure_ascii=False,
        )
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        data = _extract_json_object(resp.output_text or "")
        if not data:
            return None
        return data
    except Exception:
        return None


def _intent_node_logic(
    message: str,
    history_user_messages: list[str],
    threshold: float,
    model_name: str | None,
) -> dict[str, Any]:
    llm_data = _llm_intent_infer(message, history_user_messages, model_name)

    if llm_data:
        intent = str(llm_data.get("intent", "chat")).strip().lower()
        if intent not in {"chat", "business_query"}:
            intent = "chat"
        is_followup = bool(llm_data.get("is_followup", False))
        confidence = float(llm_data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        merged_query = str(llm_data.get("merged_query", "")).strip()
        if not merged_query:
            merged_query = _merge_query_fallback(message, history_user_messages, is_followup)
    else:
        intent, confidence = _intent_fallback(message, history_user_messages)
        is_followup = _is_followup_fallback(message, history_user_messages)
        merged_query = _merge_query_fallback(message, history_user_messages, is_followup)

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


def _insert_chat_history(
    db: Session,
    admin_id: int,
    session_id: str,
    user_message: str,
    rewritten_query: str,
    model_name: str | None,
) -> None:
    """按约定写两条历史：user 原文 + assistant rewritten_query。"""
    user_row = ChatHistory(
        admin_id=admin_id,
        session_id=session_id,
        message_role="user",
        message_content=user_message,
        model_name=model_name,
        created_by=admin_id,
        updated_by=admin_id,
        is_deleted=False,
    )
    assistant_row = ChatHistory(
        admin_id=admin_id,
        session_id=session_id,
        message_role="assistant",
        message_content=rewritten_query,
        model_name=model_name,
        created_by=admin_id,
        updated_by=admin_id,
        is_deleted=False,
    )
    db.add(user_row)
    db.add(assistant_row)


def _insert_workflow_log(
    db: Session,
    admin_id: int,
    session_id: str,
    input_json: dict[str, Any],
    output_json: dict[str, Any] | None,
    status: str,
    error_message: str | None,
) -> None:
    row = WorkflowLog(
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
    db.add(row)


def _save_node_io_local(
    session_id: str,
    admin_id: int,
    step_name: str,
    node_input: dict[str, Any],
    node_output: dict[str, Any] | None,
    status: str,
    error_message: str | None,
) -> None:
    """将节点输入/输出持久化到本地 JSON 文件。"""
    root = Path(settings.node_io_log_dir)
    step_dir = root / session_id / step_name
    step_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = step_dir / f"{ts}_{status}.json"

    payload = {
        "session_id": session_id,
        "admin_id": admin_id,
        "step_name": step_name,
        "status": status,
        "error_message": error_message,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input": node_input,
        "output": node_output,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def execute_task010_intent(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
) -> dict[str, Any]:
    """执行 TASK010：意图识别 + 入库。"""
    session_id = payload.session_id or uuid.uuid4().hex[:16]
    # 未配置 LLM key 时走本地兜底，不记录默认模型名，避免误导。
    model_name = payload.model_name or (
        settings.llm_model_intent if settings.llm_api_key else None
    )
    threshold = settings.intent_confidence_threshold

    request_history = _extract_user_history(
        [item.dict() for item in payload.history] if payload.history else None
    )
    db_history = _get_recent_user_messages(db, session_id, limit=4)
    # 前端已传 history 时优先使用传入历史，避免与数据库历史重复叠加。
    history_user_messages = request_history[-4:] if request_history else db_history[-4:]

    input_json = {
        "message": payload.message,
        "history_user_messages": history_user_messages,
        "threshold": threshold,
    }

    try:
        def _node_logger(
            step_name: str,
            node_input: dict[str, Any],
            node_output: dict[str, Any] | None,
            status: str,
            error_message: str | None,
        ) -> None:
            _save_node_io_local(
                session_id=session_id,
                admin_id=admin_id,
                step_name=step_name,
                node_input=node_input,
                node_output=node_output,
                status=status,
                error_message=error_message,
            )

        result = run_task010_intent_graph(
            message=payload.message,
            history_user_messages=history_user_messages,
            threshold=threshold,
            model_name=model_name,
            node_executor=_intent_node_logic,
            node_io_logger=_node_logger,
        )
        result["session_id"] = session_id

        _insert_chat_history(
            db=db,
            admin_id=admin_id,
            session_id=session_id,
            user_message=payload.message,
            rewritten_query=result["rewritten_query"],
            model_name=model_name,
        )
        _insert_workflow_log(
            db=db,
            admin_id=admin_id,
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
            _insert_workflow_log(
                db=db,
                admin_id=admin_id,
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
