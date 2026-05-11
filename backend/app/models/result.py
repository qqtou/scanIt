"""
ScanIt 检测结果模型
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, JSON, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RiskLevel(str):
    """风险等级"""

    HIGH = "high"  # 高风险
    MEDIUM = "medium"  # 中风险
    LOW = "low"  # 低风险
    SAFE = "safe"  # 安全 (相似度低于阈值)


class Result(Base):
    """检测结果模型"""

    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("works.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 来源信息
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_snapshot_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # 内容类型 (与 works.content_type 一致)
    content_type: Mapped[str] = mapped_column(
        Enum("text", "image", "video", name="result_content_type_enum"),
        nullable=False,
        index=True,
    )

    # 比对结果
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )  # 0.0 - 1.0
    risk_level: Mapped[str] = mapped_column(
        Enum("high", "medium", "low", "safe", name="risk_level_enum"),
        nullable=False,
        index=True,
    )

    # 详细比对数据 (使用 JSON 存储)
    match_details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )  # 存储具体的匹配片段、区域等信息
    matched_regions: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
    )  # 图片匹配区域坐标
    matched_segments: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
    )  # 视频匹配时间段

    # 搜索引擎信息
    search_engine: Mapped[str] = mapped_column(String(50), nullable=False)
    search_keyword: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 审核状态
    review_status: Mapped[str] = mapped_column(
        Enum("pending", "reviewed", "confirmed", "false_positive", name="review_status_enum"),
        default="pending",
        index=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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
    task = relationship("Task", back_populates="results")
    work = relationship("Work")
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_results_task_risk", "task_id", "risk_level"),
        Index("ix_results_user_risk", "user_id", "risk_level"),
        Index("ix_results_similarity", "similarity_score"),
        Index("ix_results_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Result(id={self.id}, risk='{self.risk_level}', score={self.similarity_score:.2f})>"
