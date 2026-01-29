from sqlalchemy import DateTime, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class MetricSnapshot(AuditMixin, Base):
    __tablename__ = "metric_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    metric_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    stat_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False, index=True)
    dimension_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
