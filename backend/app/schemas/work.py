"""
Pydantic Schemas - Work
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkBase(BaseModel):
    """作品基础 schema"""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    content_type: Literal["text", "image", "video"]
    content_url: str = Field(..., max_length=1024)
    tags: list[str] = Field(default_factory=list)


class WorkCreate(WorkBase):
    """创建作品"""

    pass


class WorkUpdate(BaseModel):
    """更新作品"""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    status: Literal["pending", "processing", "completed", "failed"] | None = None


class WorkInDB(WorkBase):
    """数据库作品模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    content_hash: str | None = None
    content_size: int | None = None
    mime_type: str | None = None
    metadata_: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None


class WorkPublic(BaseModel):
    """公开作品信息"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content_type: str
    content_url: str
    status: str
    created_at: datetime


class WorkListResponse(BaseModel):
    """作品列表响应"""

    items: list[WorkInDB]
    total: int
    page: int
    page_size: int
    total_pages: int


class WorkStats(BaseModel):
    """作品统计"""

    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]
