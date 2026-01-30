from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class AlertEvent(AuditMixin, Base):
    __tablename__ = "alert_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    rule_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="规则ID")
    metric_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="指标快照ID")
    event_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False, comment="触发时间")
    level: Mapped[str] = mapped_column(String(16), nullable=False, comment="事件等级")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", comment="处理状态")
    handler: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="处理人")
    handle_time: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True, comment="处理时间")
    handle_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理说明")