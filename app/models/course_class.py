from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class CourseClass(AuditMixin, Base):
    __tablename__ = "course_class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course.id"), nullable=False, index=True, comment="课程ID"
    )
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("class.id"), nullable=False, index=True, comment="所属班级ID"
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teacher.id"), nullable=False, index=True, comment="教师ID"
    )
    term: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="学期")
    schedule_info: Mapped[str | None] = mapped_column(Text, nullable=True, comment="上课时间地点")
    max_students: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最大人数")