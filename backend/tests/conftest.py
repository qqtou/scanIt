"""
Pytest 配置和 Fixtures
"""
import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from pathlib import Path

# 设置测试环境变量
os.environ["TESTING"] = "true"

# 使用文件数据库而非 in-memory（每个 in-memory 连接会创建独立数据库）
TEST_DB_PATH = Path(__file__).parent / "test.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.main import app
from app.models.base import Base
from app.models import User, Work, Task, Result
from app.api.deps import get_password_hash


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎"""
    # 使用文件数据库，避免 in-memory 每个连接独立数据库问题
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
    
    # 删除数据库文件
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    from app.models.base import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """创建管理员用户"""
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_work(db_session: AsyncSession, test_user: User) -> Work:
    """创建测试作品"""
    work = Work(
        user_id=test_user.id,
        title="测试作品",
        content_type="text",
        content_url="https://example.com/test",
        content_hash="testhash123",
    )
    db_session.add(work)
    await db_session.commit()
    await db_session.refresh(work)
    return work


@pytest.fixture(scope="function")
async def test_task(db_session: AsyncSession, test_user: User, test_work: Work) -> Task:
    """创建测试任务"""
    task = Task(
        user_id=test_user.id,
        work_id=test_work.id,
        status="pending",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.fixture(scope="function")
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """获取认证头"""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": test_user.username,
            "password": "testpassword",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def admin_auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """获取管理员认证头"""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": admin_user.username,
            "password": "adminpassword",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
