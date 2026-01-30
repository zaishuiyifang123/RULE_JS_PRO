from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class Classroom(AuditMixin, Base):
    __tablename__ = "classroom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    building: Mapped[str] = mapped_column(String(64), nullable=False, comment="教学楼")
    room_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="教室编号")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="容量")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available", comment="状态")