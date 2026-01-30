from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class Major(AuditMixin, Base):
    __tablename__ = "major"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    major_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="专业名称")
    major_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="专业编码")
    college_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("college.id"), nullable=False, index=True, comment="所属学院ID"
    )
    degree_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="学历类型")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
