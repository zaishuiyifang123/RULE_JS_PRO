from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ImportLog(Base):
    __tablename__ = "import_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="表名")
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总行数")
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功行数")
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败行数")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误摘要")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="创建人")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")