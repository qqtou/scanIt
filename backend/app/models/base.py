"""
ScanIt 数据库配置和基础类
"""
import os
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# 命名约束 (解决单复数命名冲突)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有模型的基类"""

    metadata = MetaData(naming_convention=convention)

    created_at: datetime
    updated_at: datetime | None = None


# 测试模式检测
TESTING = os.getenv("TESTING", "false").lower() == "true"

# 懒加载引擎
_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """获取数据库引擎 (懒加载)"""
    global _engine
    if _engine is None:
        # 测试模式使用 SQLite
        if TESTING:
            url = "sqlite+aiosqlite:///:memory:"
        else:
            url = settings.database_url
        
        is_sqlite = "sqlite" in url
        
        # SQLite 不支持 pool_size 和 pool_pre_ping，需要完全跳过这些参数
        engine_kwargs = {"echo": settings.debug}
        if not (TESTING or is_sqlite):
            engine_kwargs["pool_size"] = settings.database_pool_size
            engine_kwargs["pool_pre_ping"] = True
        else:
            engine_kwargs["pool_pre_ping"] = False
        
        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂"""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# 为了向后兼容，提供属性访问
class _EngineProxy:
    """引擎代理，支持懒加载"""
    def __call__(self):
        return get_engine()
    
    def __getattr__(self, name):
        return getattr(get_engine(), name)
    
    def __repr__(self):
        return f"<Engine proxy for {get_engine()}>"


class _SessionMakerProxy:
    """会话工厂代理，支持懒加载"""
    def __call__(self):
        return get_session_maker()
    
    def __getattr__(self, name):
        return getattr(get_session_maker(), name)


# 兼容旧代码的导出
engine = _EngineProxy()
async_session_maker = _SessionMakerProxy()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：获取数据库会话"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
