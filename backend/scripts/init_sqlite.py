"""
ScanIt 本地开发 - SQLite 数据库初始化脚本
用法: python scripts/init_sqlite.py
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from sqlalchemy import text
from app.models.base import get_engine, get_session_maker, Base
from app.models import *  # noqa - 注册所有模型
from app.core.config import settings


async def init_db():
    """初始化 SQLite 数据库"""
    engine = get_engine()
    url = settings.database_url

    print(f"[INFO] 数据库 URL: {url}")

    # 创建所有表
    print("[INFO] 创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] 数据库表创建完成")

    # 初始化默认租户
    print("[INFO] 初始化默认租户...")
    session_maker = get_session_maker()
    async with session_maker() as session:
        # 检查是否已存在默认租户
        result = await session.execute(
            text("SELECT id FROM tenants WHERE slug = 'default'")
        )
        if result.scalar_one_or_none():
            print("[OK] 默认租户已存在，跳过")
        else:
            # 创建默认租户
            await session.execute(text("""
                INSERT INTO tenants (id, name, slug, plan, quota_monthly, quota_used,
                                     quota_period_start, is_active, contact_name,
                                     created_at, updated_at)
                VALUES (:id, :name, :slug, :plan, :quota, :used, :period, :active,
                        :contact, :created, :updated)
            """), {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "默认租户",
                "slug": "default",
                "plan": "enterprise",
                "quota": 999999,
                "used": 0,
                "period": datetime.now(timezone.utc).isoformat(),
                "active": True,
                "contact": "admin",
                "created": datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
            })
            await session.commit()
            print("[OK] 默认租户创建完成")

        # 检查是否已存在管理员
        result = await session.execute(
            text("SELECT id FROM users WHERE username = 'admin'")
        )
        if result.scalar_one_or_none():
            print("[OK] 管理员用户已存在，跳过")
        else:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed_password = pwd_context.hash("admin123")

            await session.execute(text("""
                INSERT INTO users (id, username, email, hashed_password, role,
                                   is_active, is_verified, api_quota, api_used, tenant_id, created_at, updated_at)
                VALUES (:id, :username, :email, :password, :role, :active,
                        :verified, :quota, :used, :tenant_id, :created, :updated)
            """), {
                "id": "00000000-0000-0000-0000-000000000002",
                "username": "admin",
                "email": "admin@scanit.local",
                "password": hashed_password,
                "role": "system_admin",
                "active": True,
                "verified": True,
                "quota": 999999,
                "used": 0,
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "created": datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
            })
            await session.commit()
            print("[OK] 管理员用户创建完成")
            print("[INFO] 用户名: admin")
            print("[INFO] 密码: admin123")
            print("[WARN] 请登录后立即修改密码！")

    await engine.dispose()
    print("")
    print("=== 初始化完成 ===")


if __name__ == "__main__":
    asyncio.run(init_db())
