from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.chat import ChatIntentRequest
from app.services.chat_graph import execute_task011_parse as _execute_task011_parse


def execute_task011_parse(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
):
    """兼容层：转发到 app.services.chat_graph.execute_task011_parse。"""
    return _execute_task011_parse(db=db, admin_id=admin_id, payload=payload)
