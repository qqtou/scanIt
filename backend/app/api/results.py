"""
API - Results
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Result, Task, Tenant, User
from app.models.base import get_db
from app.schemas.result import (
    ResultInDB,
    ResultListResponse,
    ResultUpdate,
    RiskSummary,
    TaskReport,
)
from app.api.deps import get_current_active_user, get_current_tenant

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("", response_model=ResultListResponse)
async def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: str | None = None,
    review_status: str | None = None,
    sort_by: str = Query("similarity_score", enum=["similarity_score", "created_at"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取所有检测结果"""
    query = select(Result).where(Result.user_id == current_user.id)
    # 租户隔离
    if current_user.tenant_id:
        query = query.where(Result.tenant_id == current_user.tenant_id)

    if risk_level:
        query = query.where(Result.risk_level == risk_level)
    if review_status:
        query = query.where(Result.review_status == review_status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 排序
    if sort_by == "similarity_score":
        order_col = Result.similarity_score
    else:
        order_col = Result.created_at
    
    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/by-task/{task_id}", response_model=ResultListResponse)
async def list_results_by_task(
    task_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: str | None = None,
    review_status: str | None = None,
    sort_by: str = Query("similarity_score", enum=["similarity_score", "created_at"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取任务的结果列表"""
    # 验证任务存在且属于当前用户
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

    # 查询结果
    query = select(Result).where(Result.task_id == task_id)
    # 租户隔离
    if current_user.tenant_id:
        query = query.where(Result.tenant_id == current_user.tenant_id)

    if risk_level:
        query = query.where(Result.risk_level == risk_level)
    if review_status:
        query = query.where(Result.review_status == review_status)

    # 排序
    if sort_order == "desc":
        query = query.order_by(getattr(Result, sort_by).desc())
    else:
        query = query.order_by(getattr(Result, sort_by).asc())

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/risk-summary/{task_id}", response_model=RiskSummary)
async def get_risk_summary(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """获取任务的风险汇总"""
    # 验证任务存在
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

    # 查询风险统计
    risk_counts = {}
    for level in ["high", "medium", "low", "safe"]:
        count_query = select(func.count()).where(
            Result.task_id == task_id,
            Result.risk_level == level,
        )
        risk_counts[level] = (await db.execute(count_query)).scalar()

    # 未处理的
    unprocessed_query = select(func.count()).where(
        Result.task_id == task_id,
        Result.review_status == "pending",
    )
    unprocessed = (await db.execute(unprocessed_query)).scalar()

    return {
        "total": task.total_results,
        "high": risk_counts["high"],
        "medium": risk_counts["medium"],
        "low": risk_counts["low"],
        "safe": risk_counts["safe"],
        "unprocessed": unprocessed,
    }


@router.get("/{result_id}", response_model=ResultInDB)
async def get_result(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Result:
    """获取结果详情"""
    result = await db.execute(
        select(Result).where(
            Result.id == result_id,
            Result.user_id == current_user.id,
        )
    )
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )
    if current_user.tenant_id and result_obj.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )
    return result_obj


@router.patch("/{result_id}", response_model=ResultInDB)
async def update_result(
    result_id: uuid.UUID,
    result_data: ResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Result:
    """更新结果（审核）"""
    result = await db.execute(
        select(Result).where(
            Result.id == result_id,
            Result.user_id == current_user.id,
        )
    )
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )
    if current_user.tenant_id and result_obj.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )

    # 更新审核信息
    update_data = result_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(result_obj, field, value)

    if result_data.review_status:
        result_obj.reviewed_by = current_user.id
        result_obj.reviewed_at = datetime.now(timezone.utc)

    result_obj.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(result_obj)
    return result_obj
