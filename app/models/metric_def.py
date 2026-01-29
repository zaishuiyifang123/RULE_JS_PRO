from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class MetricDef(AuditMixin, Base):
    __tablename__ = "metric_def"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_category: Mapped[str] = mapped_column(String(32), nullable=False)
    calc_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_cycle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
