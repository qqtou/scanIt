"""
API - Dashboard Stats

提供仪表盘统计数据，支持多租户隔离。
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.models import Task, Tenant, User, Work
from app.models.base import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取仪表盘统计数据"""
    tenant_id = current_user.tenant_id

    # 租户管理员/普通用户：只看当前租户
    if current_user.role in ("user", "tenant_admin"):
        tenant_filter = Work.tenant_id == tenant_id
        task_filter = Task.tenant_id == tenant_id
    # 系统管理员：看所有租户
    elif current_user.role == "system_admin":
        tenant_filter = True
        task_filter = True
    else:
        return {
            "total_works": 0, "active_works": 0,
            "total_tasks": 0, "completed_tasks": 0,
            "total_results": 0, "high_risk_results": 0,
            "medium_risk_results": 0, "low_risk_results": 0,
        }

    # 作品统计
    works_stats = await db.execute(
        select(
            func.count(Work.id).label("total"),
            func.count(Work.id).label("active"),
        ).where(tenant_filter)
    )
    works_row = works_stats.first()
    total_works = works_row.total if works_row else 0
    active_works = works_row.active if works_row else 0

    # 任务统计
    tasks_stats = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(
                Task.id
            ).label("completed"),
        ).where(task_filter)
    )
    tasks_row = tasks_stats.first()
    total_tasks = tasks_row.total if tasks_row else 0
    completed_tasks = tasks_row.completed if tasks_row else 0

    return {
        "total_works": total_works,
        "active_works": active_works,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_results": 0,
        "high_risk_results": 0,
        "medium_risk_results": 0,
        "low_risk_results": 0,
    }