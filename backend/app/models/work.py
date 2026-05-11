"""
ScanIt 用户作品模型
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ContentType(str):
    """内容类型枚举"""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"


class Work(Base):
    """客户作品模型"""

    __tablename__ = "works"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 内容信息
    content_type: Mapped[str] = mapped_column(
        Enum("text", "image", "video", name="content_type_enum"),
        nullable=False,
        index=True,
    )
    content_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    content_size: Mapped[int | None] = mapped_column(default=None)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 元数据
    tags: Mapped[list[str] | None] = mapped_column(default=list)  # JSON array
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        default=dict,
    )  # JSON object

    # 审核状态
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed", name="work_status_enum"),
        default="pending",
        index=True,
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # 关系
    user = relationship("User", back_populates="works")
    tasks = relationship("Task", back_populates="work", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_works_user_content_type", "user_id", "content_type"),
        Index("ix_works_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Work(id={self.id}, title='{self.title}', type={self.content_type})>"
