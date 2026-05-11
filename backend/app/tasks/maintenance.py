"""
定时任务

系统维护相关的定时任务
"""
import asyncio
from datetime import datetime, timedelta

from celery import Task
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.task import DetectionTask, TaskStatus


class MaintenanceTask(Task):
    """维护任务（不允许重试）"""

    autoretry_for = ()
    max_retries = 0


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name="app.tasks.maintenance.cleanup_expired_tasks",
)
def cleanup_expired_tasks(self) -> dict:
    """
    清理过期的任务

    清理条件:
    - 任务状态为 PENDING 或 RUNNING
    - 创建时间超过 7 天
    - 没有关联的结果
    """
    async def _cleanup():
        async with async_session_maker() as session:
            # 查找过期任务
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            result = await session.execute(
                select(DetectionTask).where(
                    DetectionTask.created_at < cutoff_date,
                    DetectionTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING]),
                )
            )
            expired_tasks = result.scalars().all()

            cleaned_count = 0
            for task in expired_tasks:
                # 检查是否有结果
                from app.models.result import DetectionResult
                result_check = await session.execute(
                    select(DetectionResult)
                    .where(DetectionResult.task_id == task.id)
                    .limit(1)
                )
                if not result_check.scalar_one_or_none():
                    # 删除无结果的任务
                    await session.delete(task)
                    cleaned_count += 1

            await session.commit()
            return {"cleaned_tasks": cleaned_count}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name="app.tasks.maintenance.cleanup_old_results",
)
def cleanup_old_results(self, days: int = 90) -> dict:
    """
    清理旧的结果数据

    Args:
        days: 保留天数
    """
    async def _cleanup():
        async with async_session_maker() as session:
            from app.models.result import DetectionResult

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # 查找需要删除的结果
            result = await session.execute(
                select(DetectionResult).where(
                    DetectionResult.created_at < cutoff_date,
                    DetectionResult.review_status == "reviewed",
                )
            )
            old_results = result.scalars().all()

            deleted_count = 0
            for r in old_results:
                await session.delete(r)
                deleted_count += 1

            await session.commit()
            return {"deleted_results": deleted_count}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name="app.tasks.maintenance.sync_user_quota",
)
def sync_user_quota(self) -> dict:
    """同步用户配额"""
    async def _sync():
        async with async_session_maker() as session:
            from app.models.user import User
            from app.models.task import DetectionTask, TaskStatus

            # 获取所有用户
            result = await session.execute(select(User))
            users = result.scalars().all()

            synced_count = 0
            for user in users:
                # 计算本月已使用的配额
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                result = await session.execute(
                    select(DetectionTask).where(
                        DetectionTask.user_id == user.id,
                        DetectionTask.created_at >= month_start,
                    )
                )
                tasks_this_month = result.scalars().all()

                # 计算已用配额
                used_quota = len(tasks_this_month)

                # 更新用户配额
                user.api_quota_used = used_quota
                synced_count += 1

            await session.commit()
            return {"synced_users": synced_count}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_sync())
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name="app.tasks.maintenance.update_statistics",
)
def update_statistics(self) -> dict:
    """更新系统统计信息"""
    async def _update():
        async with async_session_maker() as session:
            from app.models.result import DetectionResult
            from app.models.user import User
            from sqlalchemy import func

            stats = {}

            # 总用户数
            result = await session.execute(select(func.count(User.id)))
            stats["total_users"] = result.scalar() or 0

            # 总检测任务数
            result = await session.execute(select(func.count(DetectionTask.id)))
            stats["total_tasks"] = result.scalar() or 0

            # 总检测结果数
            result = await session.execute(select(func.count(DetectionResult.id)))
            stats["total_results"] = result.scalar() or 0

            # 高风险结果数
            result = await session.execute(
                select(func.count(DetectionResult.id))
                .where(DetectionResult.risk_level == "high")
            )
            stats["high_risk_results"] = result.scalar() or 0

            return stats

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_update())
    finally:
        loop.close()
