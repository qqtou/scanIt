"""
Pydantic Schemas - User
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """用户基础 schema"""

    email: EmailStr
    username: str
    full_name: str | None = None
    role: str = "user"  # system_admin / tenant_admin / reviewer / user
    tenant_id: UUID | None = None


class UserCreate(UserBase):
    """创建用户"""

    password: str


class UserUpdate(BaseModel):
    """更新用户"""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserInDB(UserBase):
    """数据库用户模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None = None
    is_active: bool
    is_verified: bool
    api_quota: int
    api_used: int
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None


class UserPublic(UserBase):
    """公开用户信息"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime


class UserStats(BaseModel):
    """用户统计信息"""

    total_works: int
    total_tasks: int
    total_results: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
