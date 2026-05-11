"""
ScanIt 检测任务模型
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, JSON, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TaskStatus(str):
    """任务状态枚举"""

    PENDING = "pending"  # 等待处理
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskPriority(int):
    """任务优先级"""

    LOW = 1
    NORMAL = 5
    HIGH = 10


class Task(Base):
    """检测任务模型"""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
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

    # 任务配置
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # 使用 JSON 存储
    search_engines: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=["google"],
    )  # google, bing, baidu
    content_types: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=["text", "image", "video"],
    )  # text, image, video

    # 阈值配置 (覆盖全局配置)
    text_threshold: Mapped[Optional[float]] = mapped_column(Float, default=None)
    image_threshold: Mapped[Optional[float]] = mapped_column(Float, default=None)
    video_threshold: Mapped[Optional[float]] = mapped_column(Float, default=None)

    # 执行参数
    max_results: Mapped[int] = mapped_column(Integer, default=50)
    priority: Mapped[int] = mapped_column(Integer, default=TaskPriority.NORMAL)

    # 状态
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            name="task_status_enum",
        ),
        default="pending",
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Celery 任务 ID (用于关联异步任务)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 执行结果统计
    total_results: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    low_risk_count: Mapped[int] = mapped_column(Integer, default=0)

    # 计划/执行时间
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
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
    work = relationship("Work", back_populates="tasks")
    user = relationship("User", back_populates="tasks")
    results = relationship(
        "Result",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_work_status", "work_id", "status"),
        Index("ix_tasks_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status='{self.status}', progress={self.progress}%)>"
