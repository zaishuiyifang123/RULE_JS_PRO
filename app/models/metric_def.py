from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class MetricDef(AuditMixin, Base):
    __tablename__ = "metric_def"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="指标编码")
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="指标名称")
    metric_category: Mapped[str] = mapped_column(String(32), nullable=False, comment="指标类别")
    calc_rule: Mapped[str | None] = mapped_column(Text, nullable=True, comment="计算规则")
    refresh_cycle: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="刷新周期")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="指标说明")