from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class ClassModel(AuditMixin, Base):
    __tablename__ = "class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    class_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="班级名称")
    class_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="班级编码")
    major_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("major.id"), nullable=False, index=True, comment="所属专业ID"
    )
    grade_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="入学年份")
    head_teacher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teacher.id"), nullable=True, index=True, comment="教师ID"
    )
    student_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="班级人数")