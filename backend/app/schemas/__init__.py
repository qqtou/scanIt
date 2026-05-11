"""
Pydantic Schemas
"""
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    RegisterRequest,
    Token,
    TokenData,
)
from app.schemas.result import (
    ResultBase,
    ResultDetail,
    ResultInDB,
    ResultListResponse,
    ResultPublic,
    ResultUpdate,
    RiskSummary,
    TaskReport,
)
from app.schemas.task import (
    TaskBase,
    TaskCreate,
    TaskInDB,
    TaskListResponse,
    TaskPublic,
    TaskStatusResponse,
    TaskUpdate,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserInDB,
    UserPublic,
    UserStats,
    UserUpdate,
)
from app.schemas.work import (
    WorkBase,
    WorkCreate,
    WorkInDB,
    WorkListResponse,
    WorkPublic,
    WorkStats,
    WorkUpdate,
)

__all__ = [
    # Auth
    "Token",
    "TokenData",
    "LoginRequest",
    "RegisterRequest",
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserPublic",
    "UserStats",
    # Work
    "WorkBase",
    "WorkCreate",
    "WorkUpdate",
    "WorkInDB",
    "WorkPublic",
    "WorkListResponse",
    "WorkStats",
    # Task
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskInDB",
    "TaskPublic",
    "TaskStatusResponse",
    "TaskListResponse",
    # Result
    "ResultBase",
    "ResultInDB",
    "ResultPublic",
    "ResultUpdate",
    "ResultDetail",
    "ResultListResponse",
    "RiskSummary",
    "TaskReport",
]
