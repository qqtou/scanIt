"""
API - Tasks
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, Tenant, User, Work
from app.models.base import get_db
from app.schemas.task import (
    TaskCreate,
    TaskInDB,
    TaskListResponse,
    TaskStatusResponse,
    TaskUpdate,
)
from app.api.deps import get_current_active_user
from app.api.middleware import check_tenant_quota

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskInDB, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _tenant: Tenant = Depends(check_tenant_quota),
) -> Task:
    """创建检测任务"""
    # 验证作品存在且属于当前用户
    result = await db.execute(
        select(Work).where(
            Work.id == task_data.work_id,
            Work.user_id == current_user.id,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )

    # 创建任务
    task = Task(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        work_id=task_data.work_id,
        title=task_data.title or f"Scan Task for {work.title}",
        keywords=task_data.keywords,
        search_engines=task_data.search_engines,
        content_types=task_data.content_types,
        max_results=task_data.max_results,
        priority=task_data.priority,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    work_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取任务列表"""
    query = select(Task).where(Task.user_id == current_user.id)
    # 租户隔离
    if current_user.tenant_id:
        query = query.where(Task.tenant_id == current_user.tenant_id)

    if status:
        query = query.where(Task.status == status)
    if work_id:
        query = query.where(Task.work_id == work_id)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.order_by(Task.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{task_id}", response_model=TaskInDB)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Task:
    """获取任务详情"""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.tenant_id and task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取任务状态"""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.tenant_id and task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "error_message": task.error_message,
        "total_results": task.total_results,
        "risk_summary": {
            "high": task.high_risk_count,
            "medium": task.medium_risk_count,
            "low": task.low_risk_count,
        },
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


@router.patch("/{task_id}", response_model=TaskInDB)
async def update_task(
    task_id: uuid.UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Task:
    """更新任务"""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.tenant_id and task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # 只能更新 pending 状态的任务
    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update pending tasks",
        )

    # 更新字段
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    task.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """删除任务"""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.tenant_id and task.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # 只能删除 pending 或 completed 状态的任务
    if task.status not in ["pending", "completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running task",
        )

    await db.delete(task)
    await db.commit()
