from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class Attendance(AuditMixin, Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student.id"), nullable=False, index=True, comment="学生ID"
    )
    course_class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course_class.id"), nullable=False, index=True, comment="教学班ID"
    )
    attend_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True, comment="考勤日期")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="出勤状态")
