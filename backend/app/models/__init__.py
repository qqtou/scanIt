"""
ScanIt 数据模型
"""
from app.models.base import Base, get_db, get_engine, get_session_maker
from app.models.user import User, UserRole
from app.models.work import Work, ContentType
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.result import Result, RiskLevel

# 为了向后兼容，提供这些属性的访问
engine = None
async_session_maker = None

def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    if name == "async_session_maker":
        return get_session_maker()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Base
    "Base",
    "engine",
    "get_db",
    "get_engine",
    "get_session_maker",
    "async_session_maker",
    # User
    "User",
    "UserRole",
    # Work
    "Work",
    "ContentType",
    # Task
    "Task",
    "TaskStatus",
    "TaskPriority",
    # Result
    "Result",
    "RiskLevel",
]
