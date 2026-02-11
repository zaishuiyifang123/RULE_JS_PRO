from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.deps import get_current_admin, get_db
from app.models.admin import Admin
from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatIntentRequest, ChatParseData, ChatParseResponse
from app.schemas.response import ListResponse, Meta, OkResponse
from app.services.chat_graph import execute_chat_workflow
from app.services.chat_stream_service import generate_chat_stream

router = APIRouter()


@router.post("", response_model=ChatParseResponse)
def chat_entry(
    payload: ChatIntentRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    data = execute_chat_workflow(db=db, admin_id=current_admin.id, payload=payload)
    return ChatParseResponse(data=ChatParseData(**data))


@router.post("/stream")
def chat_stream_entry(
    payload: ChatIntentRequest,
    current_admin=Depends(get_current_admin),
):
    if settings.chat_stream_mode == "sync":
        db = SessionLocal()
        try:
            data = execute_chat_workflow(db=db, admin_id=current_admin.id, payload=payload)
            return ChatParseResponse(data=ChatParseData(**data))
        finally:
            db.close()

    stream_iterator = generate_chat_stream(admin_id=current_admin.id, payload=payload)
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(stream_iterator, media_type="text/event-stream; charset=utf-8", headers=headers)


@router.get("/sessions", response_model=ListResponse)
def list_chat_sessions(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    base_filters = (
        ChatHistory.admin_id == current_admin.id,
        ChatHistory.is_deleted.is_(False),
        ChatHistory.message_role.in_(("user", "assistant")),
    )
    total = db.query(func.count(func.distinct(ChatHistory.session_id))).filter(*base_filters).scalar() or 0
    session_rows = (
        db.query(
            ChatHistory.session_id.label("session_id"),
            func.max(ChatHistory.created_at).label("last_active_at"),
        )
        .filter(*base_filters)
        .group_by(ChatHistory.session_id)
        .order_by(func.max(ChatHistory.created_at).desc(), ChatHistory.session_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    session_ids = [row.session_id for row in session_rows]
    preview_map: dict[str, str] = {}
    if session_ids:
        first_user_subquery = (
            db.query(
                ChatHistory.session_id.label("session_id"),
                func.min(ChatHistory.id).label("first_user_id"),
            )
            .filter(
                ChatHistory.admin_id == current_admin.id,
                ChatHistory.is_deleted.is_(False),
                ChatHistory.message_role == "user",
                ChatHistory.session_id.in_(session_ids),
            )
            .group_by(ChatHistory.session_id)
            .subquery()
        )
        preview_rows = (
            db.query(ChatHistory.session_id, ChatHistory.message_content)
            .join(first_user_subquery, ChatHistory.id == first_user_subquery.c.first_user_id)
            .all()
        )
        for row in preview_rows:
            raw_text = str(row.message_content or "").strip()
            preview_map[row.session_id] = f"{raw_text[:7]}..." if len(raw_text) > 7 else raw_text

    data = [
        {
            "session_id": row.session_id,
            "preview": preview_map.get(row.session_id, ""),
            "last_active_at": row.last_active_at,
        }
        for row in session_rows
    ]
    return ListResponse(
        data=jsonable_encoder(data),
        meta=Meta(offset=offset, limit=limit, total=total),
    )


@router.get("/sessions/{session_id}/messages", response_model=ListResponse)
def list_chat_session_messages(
    session_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    message_query = db.query(ChatHistory).filter(
        ChatHistory.admin_id == current_admin.id,
        ChatHistory.session_id == session_id,
        ChatHistory.is_deleted.is_(False),
        ChatHistory.message_role.in_(("user", "assistant")),
    )
    total = message_query.count()
    rows = (
        message_query.order_by(ChatHistory.created_at.asc(), ChatHistory.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    data = [
        {
            "id": row.id,
            "role": row.message_role,
            "content": row.message_content,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return ListResponse(
        data=jsonable_encoder(data),
        meta=Meta(offset=offset, limit=limit, total=total),
    )


@router.delete("/sessions/{session_id}", response_model=OkResponse)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    filters = (
        ChatHistory.admin_id == current_admin.id,
        ChatHistory.session_id == session_id,
        ChatHistory.is_deleted.is_(False),
    )
    exists = db.query(ChatHistory.id).filter(*filters).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")

    deleted = (
        db.query(ChatHistory)
        .filter(*filters)
        .update(
            {
                ChatHistory.is_deleted: True,
                ChatHistory.updated_by: current_admin.id,
                ChatHistory.updated_at: func.now(),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return OkResponse(data={"session_id": session_id, "deleted": int(deleted)})


@router.delete("/sessions", response_model=OkResponse)
def clear_chat_sessions(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    deleted = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.admin_id == current_admin.id,
            ChatHistory.is_deleted.is_(False),
        )
        .update(
            {
                ChatHistory.is_deleted: True,
                ChatHistory.updated_by: current_admin.id,
                ChatHistory.updated_at: func.now(),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return OkResponse(data={"deleted": int(deleted)})


@router.get("/downloads/{file_name}")
def download_chat_export(
    file_name: str,
    request: Request,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    bearer_token = ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()
    token_value = bearer_token or (token or "").strip()
    admin_id = decode_access_token(token_value) if token_value else None
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    current_admin = db.query(Admin).filter(Admin.id == int(admin_id), Admin.is_deleted == False).first()
    if not current_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    safe_name = Path(file_name).name
    if safe_name != file_name or not safe_name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file name")
    expected_prefix = f"admin_{current_admin.id}_"
    if not safe_name.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="No permission to download this file")

    file_path = Path(settings.chat_export_dir) / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="text/csv; charset=utf-8",
        filename=safe_name,
    )
