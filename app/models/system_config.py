from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class SystemConfig(AuditMixin, Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    config_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True, comment="配置键")
    config_value: Mapped[str | None] = mapped_column(Text, nullable=True, comment="配置值")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="配置说明")