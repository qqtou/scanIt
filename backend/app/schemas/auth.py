"""
Pydantic Schemas - Auth
"""
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """访问令牌"""

    access_token: str
    token_type: str = "bearer"
    tenant_id: str | None = None
    role: str | None = None


class TokenData(BaseModel):
    """令牌数据"""

    user_id: str | None = None


class LoginRequest(BaseModel):
    """登录请求"""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    invite_code: str | None = None  # 邀请码，用于租户分配


class PasswordChange(BaseModel):
    """修改密码"""

    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    """重置密码请求"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """确认重置密码"""

    token: str
    new_password: str
