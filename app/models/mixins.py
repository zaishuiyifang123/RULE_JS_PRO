from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class AuditMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="创建人")
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="更新人")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="逻辑删除")
