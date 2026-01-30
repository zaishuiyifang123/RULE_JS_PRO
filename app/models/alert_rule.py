from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class AlertRule(AuditMixin, Base):
    __tablename__ = "alert_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    metric_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="指标ID")
    condition_expr: Mapped[str] = mapped_column(Text, nullable=False, comment="触发条件表达式")
    level: Mapped[str] = mapped_column(String(16), nullable=False, comment="预警等级")
    action_hint: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处置建议")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", comment="启用状态")