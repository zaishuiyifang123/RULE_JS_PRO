from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class ChatHistory(AuditMixin, Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="管理员ID")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="会话编号")
    message_role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色")
    message_content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容")
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="消耗tokens")
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模型名称")