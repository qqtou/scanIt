"""
ScanIt 本地开发 - SQLite 数据库初始化脚本
用法: python scripts/init_sqlite.py

测试账号说明：
  系统管理员（system_admin）：拥有平台级管理权限，可管理所有租户和用户
  租户管理员（tenant_admin）：管理指定租户下的用户和配额
  审核员（reviewer）：审核侵权检测结果
  普通用户（user）：基础功能，上传作品、发起检测
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from passlib.context import CryptContext
from sqlalchemy import text
from app.models.base import get_engine, get_session_maker, Base
from app.models import *  # noqa - 注册所有模型
from app.core.config import settings

# ── 固定 UUID ────────────────────────────────────────────────────────────────
TENANT_DEFAULT = "00000000-0000-0000-0000-000000000001"   # 默认租户
TENANT_DEMO    = "00000000-0000-0000-0000-000000000003"   # 演示租户

# ── 测试账号定义 ─────────────────────────────────────────────────────────────
TEST_USERS = [
    # 系统管理员（无租户归属）
    {
        "id":         "00000000-0000-0000-0000-000000000002",
        "username":    "admin",
        "email":       "admin@scanit.local.com",
        "password":    "admin123",
        "role":        "system_admin",
        "tenant_id":   None,
        "api_quota":   999999,
    },
    # 演示租户 - 租户管理员
    {
        "id":         "00000000-0000-0000-0000-000000000004",
        "username":    "tenant_admin",
        "email":       "tenant_admin@demo.com",
        "password":    "demo123",
        "role":        "tenant_admin",
        "tenant_id":   TENANT_DEMO,
        "api_quota":   500,
    },
    # 演示租户 - 审核员
    {
        "id":         "00000000-0000-0000-0000-000000000005",
        "username":    "reviewer",
        "email":       "reviewer@demo.com",
        "password":    "demo123",
        "role":        "reviewer",
        "tenant_id":   TENANT_DEMO,
        "api_quota":   200,
    },
    # 演示租户 - 普通用户
    {
        "id":         "00000000-0000-0000-0000-000000000006",
        "username":    "demo_user",
        "email":       "demo_user@demo.com",
        "password":    "demo123",
        "role":        "user",
        "tenant_id":   TENANT_DEMO,
        "api_quota":   100,
    },
]

TENANT_DEFS = [
    {
        "id":            TENANT_DEFAULT,
        "name":          "默认租户",
        "slug":          "default",
        "plan":          "enterprise",
        "quota_monthly": 999999,
    },
    {
        "id":            TENANT_DEMO,
        "name":          "演示租户",
        "slug":          "demo",
        "plan":          "pro",
        "quota_monthly": 500,
    },
]


async def init_db():
    """初始化 SQLite 数据库（幂等，多次运行安全）"""
    engine = get_engine()
    print(f"[INFO] 数据库 URL: {settings.database_url}")

    # 创建所有表
    print("[INFO] 创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] 数据库表创建完成")

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    now = datetime.now(timezone.utc).isoformat()

    session_maker = get_session_maker()
    async with session_maker() as session:
        # ── 初始化租户 ────────────────────────────────────────────────────
        for t in TENANT_DEFS:
            result = await session.execute(
                text("SELECT id FROM tenants WHERE id = :id"), {"id": t["id"]}
            )
            if result.scalar_one_or_none():
                print(f"[SKIP] 租户已存在: {t['name']} ({t['slug']})")
            else:
                await session.execute(text("""
                    INSERT INTO tenants (id, name, slug, plan, quota_monthly, quota_used,
                                         quota_period_start, is_active, contact_name,
                                         created_at, updated_at)
                    VALUES (:id, :name, :slug, :plan, :quota, 0, :period, 1,
                            :contact, :created, :updated)
                """), {
                    "id":      t["id"],
                    "name":    t["name"],
                    "slug":    t["slug"],
                    "plan":    t["plan"],
                    "quota":   t["quota_monthly"],
                    "period":  now,
                    "contact": "admin",
                    "created": now,
                    "updated": now,
                })
                print(f"[OK] 租户创建: {t['name']} ({t['slug']}) - plan={t['plan']}")

        await session.commit()

        # ── 初始化测试用户 ────────────────────────────────────────────────
        for u in TEST_USERS:
            result = await session.execute(
                text("SELECT id FROM users WHERE id = :id"), {"id": u["id"]}
            )
            exists = result.scalar_one_or_none() is not None

            if exists:
                print(f"[SKIP] 用户已存在: {u['username']} ({u['role']})")
            else:
                hashed = pwd_context.hash(u["password"])
                await session.execute(text("""
                    INSERT INTO users (id, username, email, hashed_password, role,
                                       is_active, is_verified, api_quota, api_used,
                                       tenant_id, created_at, updated_at)
                    VALUES (:id, :username, :email, :password, :role,
                            1, 1, :quota, 0, :tenant_id, :created, :updated)
                """), {
                    "id":        u["id"],
                    "username":  u["username"],
                    "email":     u["email"],
                    "password":  hashed,
                    "role":      u["role"],
                    "quota":     u["api_quota"],
                    "tenant_id": u["tenant_id"],
                    "created":  now,
                    "updated":  now,
                })
                tenant_info = f" | 租户: {u['tenant_id'] or '无（系统管理员）'}"
                print(f"[OK] 用户创建: {u['username']} ({u['role']}){tenant_info}")

        await session.commit()

    await engine.dispose()

    print("\n" + "=" * 50)
    print("  ScanIt 测试账号")
    print("=" * 50)
    print("  系统管理员: admin / admin123")
    print("  租户管理员: tenant_admin / demo123")
    print("  审核员:     reviewer / demo123")
    print("  普通用户:   demo_user / demo123")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(init_db())
