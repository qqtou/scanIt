"""
T1.5 数据迁移：为现有数据分配默认租户

用法：
    python -m scripts.migrate_default_tenant

功能：
1. 创建默认租户（slug=default）
2. 将所有现有用户分配到默认租户
3. 将所有现有 works/tasks/results 的 tenant_id 设为默认租户
4. 将 admin 角色迁移为 tenant_admin
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_session_maker, get_engine


DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_TENANT_SLUG = "default"
DEFAULT_TENANT_NAME = "Default Tenant"


async def migrate():
    engine = get_engine()
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            # 1. 创建默认租户
            await session.execute(text("""
                INSERT INTO tenants (id, name, slug, plan, quota_monthly, quota_used, is_active, settings, created_at)
                VALUES (:id, :name, :slug, 'enterprise', 999999, 0, true, '{}', :now)
                ON CONFLICT (slug) DO NOTHING
            """), {
                "id": DEFAULT_TENANT_ID,
                "name": DEFAULT_TENANT_NAME,
                "slug": DEFAULT_TENANT_SLUG,
                "now": datetime.now(timezone.utc),
            })
            print(f"[OK] 默认租户已创建: {DEFAULT_TENANT_NAME} ({DEFAULT_TENANT_ID})")

            # 2. 迁移 admin → tenant_admin
            result = await session.execute(text("""
                UPDATE users SET role = 'tenant_admin' WHERE role = 'admin'
            """))
            print(f"[OK] 迁移 admin → tenant_admin: {result.rowcount} 行")

            # 3. 为所有用户分配默认租户
            result = await session.execute(text("""
                UPDATE users SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": DEFAULT_TENANT_ID})
            print(f"[OK] 用户分配默认租户: {result.rowcount} 行")

            # 4. 为 works 分配默认租户
            result = await session.execute(text("""
                UPDATE works SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": DEFAULT_TENANT_ID})
            print(f"[OK] Works 分配默认租户: {result.rowcount} 行")

            # 5. 为 tasks 分配默认租户
            result = await session.execute(text("""
                UPDATE tasks SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": DEFAULT_TENANT_ID})
            print(f"[OK] Tasks 分配默认租户: {result.rowcount} 行")

            # 6. 为 results 分配默认租户
            result = await session.execute(text("""
                UPDATE results SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": DEFAULT_TENANT_ID})
            print(f"[OK] Results 分配默认租户: {result.rowcount} 行")

            await session.commit()
            print("\n✅ 数据迁移完成！")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 迁移失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate())
