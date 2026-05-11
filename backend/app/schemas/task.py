"""
Pydantic Schemas - Task
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    """任务基础 schema"""

    title: str | None = None
    keywords: list[str] = Field(default_factory=list)
    search_engines: list[str] = Field(default=["google"])
    content_types: list[str] = Field(default=["text", "image", "video"])
    max_results: int = Field(default=50, ge=1, le=200)
    priority: int = Field(default=5, ge=1, le=10)


class TaskCreate(TaskBase):
    """创建任务"""

    work_id: UUID


class TaskUpdate(BaseModel):
    """更新任务"""

    title: str | None = None
    keywords: list[str] | None = None
    search_engines: list[str] | None = None
    content_types: list[str] | None = None
    max_results: int | None = Field(None, ge=1, le=200)
    priority: int | None = Field(None, ge=1, le=10)
    text_threshold: float | None = Field(None, ge=0.0, le=1.0)
    image_threshold: float | None = Field(None, ge=0.0, le=1.0)
    video_threshold: float | None = Field(None, ge=0.0, le=1.0)


class TaskInDB(TaskBase):
    """数据库任务模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    user_id: UUID
    status: str
    progress: int
    error_message: str | None = None
    celery_task_id: str | None = None
    total_results: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    text_threshold: float | None = None
    image_threshold: float | None = None
    video_threshold: float | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class TaskPublic(BaseModel):
    """公开任务信息"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    title: str | None
    keywords: list[str]
    search_engines: list[str]
    content_types: list[str]
    status: str
    progress: int
    created_at: datetime
    completed_at: datetime | None = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: UUID
    status: str
    progress: int
    error_message: str | None = None
    total_results: int
    risk_summary: dict[str, int]
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskListResponse(BaseModel):
    """任务列表响应"""

    items: list[TaskInDB]
    total: int
    page: int
    page_size: int
    total_pages: int
