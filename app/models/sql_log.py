from sqlalchemy import Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class SqlLog(AuditMixin, Base):
    __tablename__ = "sql_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="会话编号")
    sql_text: Mapped[str] = mapped_column(Text, nullable=False, comment="SQL语句")
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="SQL参数")
    exec_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="执行耗时ms")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="影响行数")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="执行状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="风险等级")