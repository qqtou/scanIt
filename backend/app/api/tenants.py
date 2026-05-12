"""
ScanIt 租户管理 API（System Admin）
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_system_admin, get_current_user, get_db
from app.models import Tenant, User
from app.models.base import get_db as get_session
from app.schemas.tenant import (
    TenantCreate,
    TenantQuotaResponse,
    TenantResponse,
    TenantSettingsUpdate,
    TenantUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/tenants", tags=["system-tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_system_admin),
):
    """创建租户（System Admin）"""
    # 检查 slug 唯一性
    existing = await db.execute(
        select(Tenant).where(Tenant.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Tenant slug '{data.slug}' already exists")

    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        plan=data.plan,
        quota_monthly=data.quota_monthly,
        settings=data.settings or {},
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    logger.info(f"[Tenant] Created | id={tenant.id} | slug={tenant.slug} | plan={tenant.plan}")
    return tenant


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool | None = None,
    plan: str | None = None,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_system_admin),
):
    """租户列表（System Admin）"""
    query = select(Tenant)
    if is_active is not None:
        query = query.where(Tenant.is_active == is_active)
    if plan:
        query = query.where(Tenant.plan == plan)
    query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_system_admin),
):
    """获取租户详情（System Admin）"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_system_admin),
):
    """更新租户（System Admin）"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)

    await db.flush()
    await db.refresh(tenant)
    logger.info(f"[Tenant] Updated | id={tenant.id} | fields={list(update_data.keys())}")
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_system_admin),
):
    """禁用租户（System Admin）— 不删除，仅禁用"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    tenant.is_active = False
    await db.flush()
    logger.info(f"[Tenant] Deactivated | id={tenant_id}")


# ---------- 租户内管理（Tenant Admin） ----------

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/quota", response_model=TenantQuotaResponse)
async def get_tenant_quota(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """查看当前租户配额（Tenant Admin）"""
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    return TenantQuotaResponse(
        tenant_id=tenant.id,
        plan=tenant.plan,
        quota_monthly=tenant.quota_monthly,
        quota_used=tenant.quota_used,
        quota_remaining=max(0, tenant.quota_monthly - tenant.quota_used),
        quota_period_start=tenant.quota_period_start,
    )


@admin_router.get("/settings")
async def get_tenant_settings(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取当前租户配置"""
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    return {"tenant_id": str(tenant.id), "settings": tenant.settings or {}}


@admin_router.put("/settings")
async def update_tenant_settings(
    data: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """更新当前租户配置（Tenant Admin）"""
    from app.api.deps import get_current_tenant_admin
    # 权限检查：需要 tenant_admin 或 system_admin
    if current_user.role not in ("tenant_admin", "system_admin"):
        raise HTTPException(403, "Tenant admin required")

    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # 合并配置
    current_settings = tenant.settings or {}
    update_data = data.model_dump(exclude_unset=True)
    current_settings.update(update_data)
    tenant.settings = current_settings

    await db.flush()
    logger.info(f"[Tenant] Settings updated | tenant_id={tenant.id} | keys={list(update_data.keys())}")
    return {"tenant_id": str(tenant.id), "settings": tenant.settings}


# ---------- 租户内用户管理（Tenant Admin） ----------

@admin_router.get("/users")
async def list_tenant_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取当前租户用户列表"""
    if current_user.role not in ("tenant_admin", "system_admin"):
        raise HTTPException(403, "Tenant admin required")
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    query = select(User).where(User.tenant_id == current_user.tenant_id)
    if role:
        query = query.where(User.role == role)
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()
    return [{"id": str(u.id), "username": u.username, "email": u.email, "role": u.role, "is_active": u.is_active} for u in users]


@admin_router.post("/users")
async def create_tenant_user(
    email: str,
    username: str,
    password: str,
    role: str = "user",
    full_name: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """在当前租户下创建用户"""
    if current_user.role not in ("tenant_admin", "system_admin"):
        raise HTTPException(403, "Tenant admin required")
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    # 检查邮箱/用户名
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username already taken")

    from app.api.deps import get_password_hash
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        tenant_id=current_user.tenant_id,
        role=role,
    )
    db.add(user)
    await db.flush()
    logger.info(f"[Admin] User created | tenant={current_user.tenant_id} | user={user.id} | role={role}")
    return {"id": str(user.id), "username": user.username, "role": user.role}


@admin_router.patch("/users/{user_id}")
async def update_tenant_user(
    user_id: UUID,
    role: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """更新租户内用户（角色、状态）"""
    if current_user.role not in ("tenant_admin", "system_admin"):
        raise HTTPException(403, "Tenant admin required")
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "User not found in tenant")

    # tenant_admin 不能修改 system_admin
    if user.role == "system_admin" and current_user.role != "system_admin":
        raise HTTPException(403, "Cannot modify system admin")

    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active

    await db.flush()
    logger.info(f"[Admin] User updated | user={user_id} | role={user.role} | active={user.is_active}")
    return {"id": str(user.id), "username": user.username, "role": user.role, "is_active": user.is_active}
