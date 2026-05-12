"""
ScanIt 配额检查中间件

在创建检测任务时检查租户配额，超额返回 429。
任务完成后 quota_used += 1。
"""
import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.models import Tenant, User
from app.models.base import get_db

logger = logging.getLogger(__name__)


async def check_tenant_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """检查租户配额，超额抛 429

    用法：在创建检测任务的路由参数中加 tenant=Depends(check_tenant_quota)
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not assigned to tenant",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found",
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )

    if tenant.quota_used >= tenant.quota_monthly:
        logger.warning(
            f"[Quota] Exceeded | tenant={tenant.id} "
            f"used={tenant.quota_used}/{tenant.quota_monthly}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota exceeded: {tenant.quota_used}/{tenant.quota_monthly}",
        )

    logger.info(
        f"[Quota] OK | tenant={tenant.id} "
        f"used={tenant.quota_used}/{tenant.quota_monthly}"
    )
    return tenant


async def increment_quota_usage(
    tenant_id,
    db: AsyncSession,
) -> None:
    """任务完成后调用，quota_used += 1"""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if tenant:
        tenant.quota_used += 1
        logger.info(
            f"[Quota] Incremented | tenant={tenant.id} "
            f"used={tenant.quota_used}/{tenant.quota_monthly}"
        )
