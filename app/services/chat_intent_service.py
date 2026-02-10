from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.chat import ChatIntentRequest
from app.services.chat_graph import execute_task010_intent as _execute_task010_intent


def execute_task010_intent(
    db: Session,
    admin_id: int,
    payload: ChatIntentRequest,
):
    """兼容层：转发到 app.services.chat_graph.execute_task010_intent。"""
    return _execute_task010_intent(db=db, admin_id=admin_id, payload=payload)
