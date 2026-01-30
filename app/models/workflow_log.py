from sqlalchemy import Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class WorkflowLog(AuditMixin, Base):
    __tablename__ = "workflow_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="会话编号")
    step_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="步骤名称")
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="步骤输入")
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="步骤输出")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="执行状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="风险等级")