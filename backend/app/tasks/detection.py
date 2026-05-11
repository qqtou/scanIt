"""
侵权检测异步任务
"""
import asyncio
from datetime import datetime
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import async_session_maker, get_db
from app.engines.detector import DetectionService, DetectionResult
from app.models.task import TaskStatus, DetectionTask
from app.models.result import DetectionResult as DBDetectionResult
from app.models.work import WorkContentType


class DetectionTaskWithRetry(Task):
    """支持重试的检测任务"""

    autoretry_for = (Exception, SoftTimeLimitExceeded)
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3}
    retry_delay = 60


@celery_app.task(
    bind=True,
    base=DetectionTaskWithRetry,
    name="app.tasks.detection.run_detection",
)
def run_detection(
    self,
    task_id: int,
    work_id: int,
    keywords: list[str],
    search_engines: list[str] | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """
    执行侵权检测任务

    Args:
        task_id: 任务 ID
        work_id: 作品 ID
        keywords: 搜索关键词
        search_engines: 使用的搜索引擎
        max_results: 最大结果数量

    Returns:
        dict: 任务执行结果
    """
    async def _run():
        async with async_session_maker() as session:
            # 获取任务
            result = await session.execute(
                select(DetectionTask).where(DetectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found", "task_id": task_id}

            # 获取作品
            from app.models.work import Work
            result = await session.execute(
                select(Work).where(Work.id == work_id)
            )
            work = result.scalar_one_or_none()
            if not work:
                return {"error": "Work not found", "work_id": work_id}

            # 更新任务状态为进行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            await session.commit()

            try:
                # 初始化检测服务
                detection_service = DetectionService()

                # 确定内容类型
                content_type_map = {
                    WorkContentType.TEXT: "text",
                    WorkContentType.IMAGE: "image",
                    WorkContentType.VIDEO: "video",
                }
                content_type = content_type_map.get(work.content_type, "text")

                # 获取原始内容
                content = work.content_url or work.content_hash or ""

                # 执行检测
                total_results = 0
                high_risk_count = 0
                medium_risk_count = 0
                low_risk_count = 0

                async for detection_result in detection_service.detect(
                    content=content,
                    content_type=content_type,
                    keywords=keywords,
                    search_engines=search_engines,
                    max_results=max_results,
                ):
                    # 保存检测结果到数据库
                    db_result = DBDetectionResult(
                        task_id=task_id,
                        source_url=detection_result.url,
                        source_title=detection_result.title,
                        source_snippet=detection_result.snippet,
                        source_domain=detection_result.domain,
                        similarity_score=detection_result.similarity,
                        risk_level=detection_result.risk_level,
                        search_engine=detection_result.search_engine,
                        search_keyword=detection_result.search_keyword,
                        match_details=detection_result.match_details,
                        matched_regions=detection_result.matched_regions,
                        matched_segments=detection_result.matched_segments,
                        review_status="pending",
                    )
                    session.add(db_result)

                    total_results += 1
                    if detection_result.risk_level == "high":
                        high_risk_count += 1
                    elif detection_result.risk_level == "medium":
                        medium_risk_count += 1
                    else:
                        low_risk_count += 1

                    # 更新任务进度
                    task.progress = min(int(total_results / max_results * 100), 99)
                    await session.commit()

                # 任务完成
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.progress = 100
                await session.commit()

                return {
                    "task_id": task_id,
                    "status": "completed",
                    "total_results": total_results,
                    "high_risk_count": high_risk_count,
                    "medium_risk_count": medium_risk_count,
                    "low_risk_count": low_risk_count,
                }

            except SoftTimeLimitExceeded:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = "Task timed out"
                await session.commit()
                raise

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = str(e)
                await session.commit()
                raise

    # 在事件循环中运行异步代码
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.detection.retry_detection")
def retry_detection(task_id: int, max_retries: int = 3) -> dict[str, Any]:
    """重试失败的检测任务"""
    async def _retry():
        async with async_session_maker() as session:
            result = await session.execute(
                select(DetectionTask).where(DetectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            if task.status != TaskStatus.FAILED:
                return {"error": "Task is not in failed state"}

            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.error_message = None
            task.retry_count = (task.retry_count or 0) + 1
            await session.commit()

            # 重新执行任务
            if task.retry_count <= max_retries:
                run_detection.delay(
                    task_id=task.id,
                    work_id=task.work_id,
                    keywords=task.keywords or [],
                    search_engines=task.search_engines,
                    max_results=50,
                )
                return {"status": "retry_scheduled", "retry_count": task.retry_count}
            else:
                return {"error": "Max retries exceeded"}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_retry())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.detection.batch_run")
def batch_run_detection(task_ids: list[int]) -> dict[str, Any]:
    """批量执行检测任务"""
    from app.celery_app import celery_app

    # 并发执行所有任务
    async_results = []
    for task_id in task_ids:
        async_results.append(run_detection.delay(task_id=task_id))

    # 等待所有任务完成
    results = []
    for ar in async_results:
        try:
            result = ar.get(timeout=3600)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})

    return {
        "total": len(task_ids),
        "completed": sum(1 for r in results if r.get("status") == "completed"),
        "failed": sum(1 for r in results if "error" in r),
        "results": results,
    }
