from sqlalchemy import DateTime, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class MetricSnapshot(AuditMixin, Base):
    __tablename__ = "metric_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    metric_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="指标ID")
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="指标值")
    stat_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False, index=True, comment="统计时间")
    dimension_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="维度信息")