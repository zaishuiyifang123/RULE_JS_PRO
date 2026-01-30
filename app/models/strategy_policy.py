from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class StrategyPolicy(AuditMixin, Base):
    __tablename__ = "strategy_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="策略名称")
    policy_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="策略类型")
    policy_rule: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="策略规则")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", comment="启用状态")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="策略说明")