"""
告警任务

发送邮件、Webhook 告警
"""
import asyncio
from typing import Any

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.task import DetectionTask, TaskStatus


class AlertTaskWithRetry(Task):
    """告警任务（支持重试）"""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_kwargs = {"max_retries": 3}
    retry_delay = 30


async def send_email_alert(
    to: str,
    subject: str,
    body: str,
) -> bool:
    """发送邮件"""
    if not settings.smtp_host:
        return False

    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        message = MIMEText(body, "html", "utf-8")
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
        )
        return True
    except Exception:
        return False


async def send_webhook_alert(
    url: str,
    payload: dict,
) -> bool:
    """发送 Webhook 告警"""
    if not url:
        return False

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            return response.status_code < 400
    except Exception:
        return False


@celery_app.task(
    bind=True,
    base=AlertTaskWithRetry,
    name="app.tasks.alert.task_completed",
)
def alert_task_completed(
    self,
    task_id: int,
    user_id: int,
) -> dict[str, Any]:
    """
    任务完成告警

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
    """
    async def _alert():
        async with async_session_maker() as session:
            # 获取任务
            result = await session.execute(
                select(DetectionTask).where(DetectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            # 获取用户信息
            from app.models.user import User
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}

            # 获取统计信息
            from app.models.result import DetectionResult
            from sqlalchemy import func

            result = await session.execute(
                select(
                    DetectionResult.risk_level,
                    func.count(DetectionResult.id).label("count"),
                )
                .where(DetectionResult.task_id == task_id)
                .group_by(DetectionResult.risk_level)
            )
            stats = {row.risk_level: row.count for row in result.all()}

            total = sum(stats.values())
            high_risk = stats.get("high", 0)

            # 发送邮件
            if user.email:
                subject = f"🔔 侵权检测任务 #{task_id} 已完成"
                body = f"""
<h2>检测任务已完成</h2>
<p>您好，</p>
<p>您的侵权检测任务已全部完成。</p>
<ul>
    <li>任务编号: #{task_id}</li>
    <li>作品名称: {task.keywords or 'N/A'}</li>
    <li>总检测结果: {total} 项</li>
    <li>高风险: {high_risk} 项</li>
</ul>
<p>请登录系统查看详细报告。</p>
"""
                await send_email_alert(user.email, subject, body)

            # 发送 Webhook
            if user.webhook_url:
                payload = {
                    "event": "task_completed",
                    "task_id": task_id,
                    "user_id": user_id,
                    "stats": {
                        "total": total,
                        "high_risk": high_risk,
                        "medium_risk": stats.get("medium", 0),
                        "low_risk": stats.get("low", 0),
                    },
                }
                await send_webhook_alert(user.webhook_url, payload)

            return {
                "task_id": task_id,
                "email_sent": bool(user.email),
                "webhook_sent": bool(user.webhook_url),
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_alert())
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=AlertTaskWithRetry,
    name="app.tasks.alert.high_risk_alert",
)
def alert_high_risk(
    self,
    task_id: int,
    result_id: int,
    user_id: int,
) -> dict[str, Any]:
    """
    高风险告警

    当检测到高风险结果时立即通知用户
    """
    async def _alert():
        async with async_session_maker() as session:
            from app.models.user import User
            from app.models.result import DetectionResult

            # 获取用户
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}

            # 获取结果
            result = await session.execute(
                select(DetectionResult).where(DetectionResult.id == result_id)
            )
            detection_result = result.scalar_one_or_none()
            if not detection_result:
                return {"error": "Result not found"}

            # 发送紧急告警
            if user.email:
                subject = f"🚨 紧急：高风险侵权内容发现！"
                body = f"""
<h2>🚨 高风险侵权内容发现</h2>
<p>您好，</p>
<p>系统在任务 #{task_id} 中检测到高风险侵权内容，请立即查看：</p>
<ul>
    <li>标题: {detection_result.source_title or '无标题'}</li>
    <li>URL: <a href="{detection_result.source_url}">{detection_result.source_url}</a></li>
    <li>相似度: {detection_result.similarity_score:.1%}</li>
    <li>来源: {detection_result.search_engine}</li>
</ul>
<p>请登录系统进行审核和处理。</p>
"""
                await send_email_alert(user.email, subject, body)

            # Webhook 实时通知
            if user.webhook_url:
                payload = {
                    "event": "high_risk_detected",
                    "task_id": task_id,
                    "result_id": result_id,
                    "severity": "high",
                    "source_url": detection_result.source_url,
                    "source_title": detection_result.source_title,
                    "similarity": detection_result.similarity_score,
                }
                await send_webhook_alert(user.webhook_url, payload)

            return {
                "result_id": result_id,
                "email_sent": bool(user.email),
                "webhook_sent": bool(user.webhook_url),
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_alert())
    finally:
        loop.close()
