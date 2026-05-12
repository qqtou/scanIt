"""
API - Works
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, User, Work
from app.models.base import get_db
from app.schemas.work import (
    WorkCreate,
    WorkInDB,
    WorkListResponse,
    WorkUpdate,
)
from app.api.deps import get_current_active_user, get_current_tenant

router = APIRouter(prefix="/works", tags=["Works"])


@router.post("", response_model=WorkInDB, status_code=status.HTTP_201_CREATED)
async def create_work(
    work_data: WorkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant: Tenant = Depends(get_current_tenant),
) -> Work:
    """创建作品"""
    work = Work(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        title=work_data.title,
        description=work_data.description,
        content_type=work_data.content_type,
        content_url=work_data.content_url,
        tags=work_data.tags,
    )
    db.add(work)
    await db.commit()
    await db.refresh(work)
    return work


@router.get("", response_model=WorkListResponse)
async def list_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取作品列表"""
    query = select(Work).where(Work.user_id == current_user.id)
    # 租户隔离：非 system_admin 只看本租户数据
    if current_user.tenant_id:
        query = query.where(Work.tenant_id == current_user.tenant_id)

    if content_type:
        query = query.where(Work.content_type == content_type)
    if status:
        query = query.where(Work.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.order_by(Work.created_at.desc())
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


@router.get("/{work_id}", response_model=WorkInDB)
async def get_work(
    work_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Work:
    """获取作品详情"""
    result = await db.execute(
        select(Work).where(
            Work.id == work_id,
            Work.user_id == current_user.id,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )
    # 租户隔离校验
    if current_user.tenant_id and work.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )
    return work


@router.patch("/{work_id}", response_model=WorkInDB)
async def update_work(
    work_id: uuid.UUID,
    work_data: WorkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Work:
    """更新作品"""
    result = await db.execute(
        select(Work).where(
            Work.id == work_id,
            Work.user_id == current_user.id,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )
    if current_user.tenant_id and work.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )

    # 更新字段
    update_data = work_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(work, field, value)
    work.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(work)
    return work


@router.delete("/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work(
    work_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """删除作品"""
    result = await db.execute(
        select(Work).where(
            Work.id == work_id,
            Work.user_id == current_user.id,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )
    if current_user.tenant_id and work.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work not found",
        )
    await db.delete(work)
    await db.commit()
