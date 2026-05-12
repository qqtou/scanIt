"""
API Dependencies - 依赖注入
"""
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User, Tenant
from app.models.base import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户

    JWT payload 包含 sub(user_id), tenant_id, role。
    先从 token 解析，再从 DB 加载完整用户对象。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前管理员用户（tenant_admin 或 system_admin）"""
    if current_user.role not in ("admin", "tenant_admin", "system_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


async def get_current_tenant_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前租户管理员"""
    if current_user.role not in ("tenant_admin", "system_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin required",
        )
    return current_user


async def get_current_system_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前系统管理员"""
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin required",
        )
    return current_user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """获取当前用户的租户

    四级降级策略：
    1. system_admin → 无租户（跨租户操作）返回 None，但签名返回 Tenant | None
    2. 用户已绑定 tenant_id → 查询返回
    3. 用户未绑定 tenant_id → 400
    4. 租户不存在或已禁用 → 403
    """
    # system_admin 跨租户，无需绑定租户
    if current_user.role == "system_admin":
        return None

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not assigned to tenant",
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found",
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )
    return tenant
