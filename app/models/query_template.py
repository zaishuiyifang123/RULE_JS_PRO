from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class QueryTemplate(AuditMixin, Base):
    __tablename__ = "query_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    template_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板说明")
    template_sql: Mapped[str] = mapped_column(Text, nullable=False, comment="模板SQL")
    params_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="参数结构")
    source_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源会话")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", comment="启用状态")