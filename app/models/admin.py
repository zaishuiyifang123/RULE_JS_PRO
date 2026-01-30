from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment="主键")
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="账号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="姓名")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="邮箱")
    last_login_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="状态")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="创建人")
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="更新人")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="逻辑删除")
