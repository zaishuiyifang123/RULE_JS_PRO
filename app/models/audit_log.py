from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class AuditLog(AuditMixin, Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="管理员ID")
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="操作类型")
    action_target: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="操作对象")
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="变更前数据")
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="变更后数据")
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="风险等级")