from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.mixins import AuditMixin


class Enroll(AuditMixin, Base):
    __tablename__ = "enroll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student.id"), nullable=False, index=True, comment="学生ID"
    )
    course_class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course_class.id"), nullable=False, index=True, comment="教学班ID"
    )
    enroll_time: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="选课时间"
    )
    status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="选课状态")
