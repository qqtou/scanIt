"""
Pydantic Schemas - Result
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResultBase(BaseModel):
    """结果基础 schema"""

    source_url: str = Field(..., max_length=2048)
    source_title: str | None = Field(None, max_length=500)
    source_snippet: str | None = None
    content_type: Literal["text", "image", "video"]
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    search_engine: str


class ResultInDB(ResultBase):
    """数据库结果模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    work_id: UUID
    user_id: UUID
    source_domain: str | None = None
    source_snapshot_url: str | None = None
    risk_level: str
    match_details: dict | None = None
    matched_regions: list[dict] | None = None
    matched_segments: list[dict] | None = None
    search_keyword: str | None = None
    review_status: str
    review_notes: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ResultPublic(BaseModel):
    """公开结果信息"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    source_url: str
    source_title: str | None
    content_type: str
    similarity_score: float
    risk_level: str
    search_engine: str
    created_at: datetime


class ResultUpdate(BaseModel):
    """更新结果（审核）"""

    review_status: Literal["pending", "reviewed", "confirmed", "false_positive"] | None = None
    review_notes: str | None = None


class ResultDetail(BaseModel):
    """结果详情（含匹配细节）"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    work_id: UUID
    source_url: str
    source_title: str | None
    source_snippet: str | None = None
    source_domain: str | None = None
    content_type: str
    similarity_score: float
    risk_level: str
    match_details: dict | None = None
    matched_regions: list[dict] | None = None
    matched_segments: list[dict] | None = None
    search_engine: str
    search_keyword: str | None = None
    review_status: str
    review_notes: str | None = None
    created_at: datetime


class ResultListResponse(BaseModel):
    """结果列表响应"""

    items: list[ResultInDB]
    total: int
    page: int
    page_size: int
    total_pages: int


class RiskSummary(BaseModel):
    """风险汇总"""

    total: int
    high: int
    medium: int
    low: int
    safe: int
    unprocessed: int


class TaskReport(BaseModel):
    """任务报告"""

    task_id: UUID
    work_id: UUID
    work_title: str
    status: str
    total_results: int
    risk_summary: RiskSummary
    top_results: list[ResultDetail]
    created_at: datetime
    completed_at: datetime | None = None
