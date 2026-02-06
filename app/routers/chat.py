from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_admin, get_db
from app.schemas.chat import ChatIntentData, ChatIntentRequest, ChatIntentResponse
from app.services.chat_intent_service import execute_task010_intent

router = APIRouter()


@router.post("/intent", response_model=ChatIntentResponse)
def chat_intent(
    payload: ChatIntentRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    data = execute_task010_intent(db=db, admin_id=current_admin.id, payload=payload)
    return ChatIntentResponse(data=ChatIntentData(**data))


@router.post("", response_model=ChatIntentResponse)
def chat_entry(
    payload: ChatIntentRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    # 当前阶段 /api/chat 与 /api/chat/intent 等价，统一走 TASK010 输出
    data = execute_task010_intent(db=db, admin_id=current_admin.id, payload=payload)
    return ChatIntentResponse(data=ChatIntentData(**data))

