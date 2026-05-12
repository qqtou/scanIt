"""
ScanIt 租户模型 — 多租户架构核心
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Uuid, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TenantPlan(str):
    """租户套餐"""

    BASIC = "basic"          # 基础版
    PRO = "pro"              # 专业版
    ENTERPRISE = "enterprise"  # 企业版


class Tenant(Base):
    """租户模型"""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="租户标识，用于子域名等",
    )

    # 套餐与配额
    plan: Mapped[str] = mapped_column(
        Enum("basic", "pro", "enterprise", name="tenant_plan_enum"),
        default="basic",
        index=True,
    )
    quota_monthly: Mapped[int] = mapped_column(
        default=100,
        comment="月度检测配额",
    )
    quota_used: Mapped[int] = mapped_column(
        default=0,
        comment="已使用配额",
    )
    quota_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="当前配额周期起始时间",
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # 租户级配置（继承全局配置，可覆盖）
    # 示例: {"image_threshold": 0.85, "video_threshold": 0.8, "search_engines": ["google", "baidu"], "llm_tier": "tier_2"}
    settings: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="租户级配置，覆盖全局配置",
    )

    # 联系信息
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

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

    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tenants_plan_active", "plan", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', plan='{self.plan}')>"
