"""
ScanIt 租户 Schema（多租户）
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------- Tenant ----------

class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    plan: str = Field(default="basic", pattern=r"^(basic|pro|enterprise)$")
    quota_monthly: int = Field(default=100, ge=1)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class TenantCreate(TenantBase):
    """创建租户"""
    settings: Optional[dict] = None


class TenantUpdate(BaseModel):
    """更新租户"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[str] = Field(None, pattern=r"^(basic|pro|enterprise)$")
    quota_monthly: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    settings: Optional[dict] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class TenantResponse(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    quota_monthly: int
    quota_used: int
    quota_period_start: Optional[datetime] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TenantQuotaResponse(BaseModel):
    """租户配额信息"""
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    plan: str
    quota_monthly: int
    quota_used: int
    quota_remaining: int
    quota_period_start: Optional[datetime] = None


# ---------- Tenant Settings ----------

class TenantSettingsUpdate(BaseModel):
    """租户配置更新"""
    image_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    video_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    text_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    search_engines: Optional[list[str]] = None
    llm_tier: Optional[str] = Field(None, pattern=r"^(tier_1|tier_2|tier_3)$")
