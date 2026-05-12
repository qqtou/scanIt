"""
ScanIt 用户模型
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str):
    """用户角色（多租户）"""

    SYSTEM_ADMIN = "system_admin"    # 平台管理
    TENANT_ADMIN = "tenant_admin"  # 租户管理
    REVIEWER = "reviewer"          # 结果审核
    USER = "user"                  # 基础功能


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 用户信息
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 租户
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属租户，system_admin 无需绑定",
    )

    # 角色和权限（多租户角色）
    role: Mapped[str] = mapped_column(
        Enum(
            "system_admin",
            "tenant_admin",
            "reviewer",
            "user",
            name="user_role_enum",
        ),
        default="user",
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # API 配额
    api_quota: Mapped[int] = mapped_column(default=100)  # 每月配额
    api_used: Mapped[int] = mapped_column(default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 关系
    tenant = relationship("Tenant", back_populates="users")
    works = relationship("Work", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
