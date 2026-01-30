from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class Student(AuditMixin, Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    student_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="学号")
    real_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="性别")
    id_card: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="身份证号")
    birth_date: Mapped[Date | None] = mapped_column(Date, nullable=True, comment="出生日期")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="邮箱")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="家庭住址")
    class_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("class.id"), nullable=True, index=True, comment="所属班级ID"
    )
    major_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("major.id"), nullable=True, index=True, comment="所属专业ID"
    )
    college_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("college.id"), nullable=True, index=True, comment="所属学院ID"
    )
    enroll_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="入学年份")
    status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="学籍状态")