from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class Score(AuditMixin, Base):
    __tablename__ = "score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student.id"), nullable=False, index=True, comment="学生ID"
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course.id"), nullable=False, index=True, comment="课程ID"
    )
    course_class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("course_class.id"), nullable=False, index=True, comment="教学班ID"
    )
    term: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="学期")
    score_value: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成绩")
    score_level: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="成绩等级")
