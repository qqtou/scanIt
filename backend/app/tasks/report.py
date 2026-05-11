"""
报告生成异步任务
"""
import asyncio
from datetime import datetime
from io import BytesIO
from typing import Any

from celery import Task
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.task import DetectionTask, TaskStatus
from app.models.result import DetectionResult


class ReportTaskWithRetry(Task):
    """支持重试的报告生成任务"""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_kwargs = {"max_retries": 3}
    retry_delay = 60


def generate_html_report(task_id: int, results: list[DetectionResult]) -> str:
    """
    生成 HTML 报告

    Args:
        task_id: 任务 ID
        results: 检测结果列表

    Returns:
        str: HTML 报告内容
    """
    # 统计信息
    total = len(results)
    high_risk = sum(1 for r in results if r.risk_level == "high")
    medium_risk = sum(1 for r in results if r.risk_level == "medium")
    low_risk = sum(1 for r in results if r.risk_level == "low")

    # 按风险等级分组
    high_risk_results = [r for r in results if r.risk_level == "high"]
    medium_risk_results = [r for r in results if r.risk_level == "medium"]
    low_risk_results = [r for r in results if r.risk_level == "low"]

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>侵权检测报告 - Task #{task_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stat-card .number {{ font-size: 36px; font-weight: bold; color: #667eea; }}
        .stat-card.high .number {{ color: #e74c3c; }}
        .stat-card.medium .number {{ color: #f39c12; }}
        .stat-card.low .number {{ color: #27ae60; }}
        .stat-card .label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .section {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h2 {{ font-size: 20px; margin-bottom: 20px; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .result-item {{ padding: 20px; border-left: 4px solid; margin-bottom: 15px; background: #f9f9f9; border-radius: 5px; }}
        .result-item.high {{ border-color: #e74c3c; }}
        .result-item.medium {{ border-color: #f39c12; }}
        .result-item.low {{ border-color: #27ae60; }}
        .result-item h3 {{ font-size: 16px; margin-bottom: 10px; }}
        .result-item .url {{ color: #667eea; font-size: 14px; word-break: break-all; }}
        .result-item .meta {{ display: flex; gap: 20px; margin-top: 10px; font-size: 13px; color: #666; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
        .badge.high {{ background: #e74c3c; }}
        .badge.medium {{ background: #f39c12; }}
        .badge.low {{ background: #27ae60; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 侵权检测报告</h1>
            <p>任务编号: #{task_id} | 生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number">{total}</div>
                <div class="label">检测结果总数</div>
            </div>
            <div class="stat-card high">
                <div class="number">{high_risk}</div>
                <div class="label">高风险</div>
            </div>
            <div class="stat-card medium">
                <div class="number">{medium_risk}</div>
                <div class="label">中风险</div>
            </div>
            <div class="stat-card low">
                <div class="number">{low_risk}</div>
                <div class="label">低风险</div>
            </div>
        </div>
"""

    # 高风险结果
    if high_risk_results:
        html += f"""
        <div class="section">
            <h2>🚨 高风险结果 ({high_risk} 项)</h2>
"""
        for result in high_risk_results[:20]:
            html += f"""
            <div class="result-item high">
                <h3>{result.source_title or '无标题'}</h3>
                <div class="url"><a href="{result.source_url}" target="_blank">{result.source_url}</a></div>
                <div class="meta">
                    <span>相似度: {result.similarity_score:.1%}</span>
                    <span>来源: {result.search_engine}</span>
                    <span>关键词: {result.search_keyword}</span>
                    <span class="badge high">高风险</span>
                </div>
            </div>
"""
        html += "</div>"

    # 中风险结果
    if medium_risk_results:
        html += f"""
        <div class="section">
            <h2>⚠️ 中风险结果 ({medium_risk} 项)</h2>
"""
        for result in medium_risk_results[:10]:
            html += f"""
            <div class="result-item medium">
                <h3>{result.source_title or '无标题'}</h3>
                <div class="url"><a href="{result.source_url}" target="_blank">{result.source_url}</a></div>
                <div class="meta">
                    <span>相似度: {result.similarity_score:.1%}</span>
                    <span>来源: {result.search_engine}</span>
                    <span>关键词: {result.search_keyword}</span>
                    <span class="badge medium">中风险</span>
                </div>
            </div>
"""
        html += "</div>"

    # 低风险结果
    if low_risk_results:
        html += f"""
        <div class="section">
            <h2>✅ 低风险结果 ({low_risk} 项)</h2>
"""
        for result in low_risk_results[:5]:
            html += f"""
            <div class="result-item low">
                <h3>{result.source_title or '无标题'}</h3>
                <div class="url"><a href="{result.source_url}" target="_blank">{result.source_url}</a></div>
                <div class="meta">
                    <span>相似度: {result.similarity_score:.1%}</span>
                    <span>来源: {result.search_engine}</span>
                    <span class="badge low">低风险</span>
                </div>
            </div>
"""
        html += "</div>"

    html += """
        <div class="footer">
            <p>本报告由 ScanIt 侵权检测系统自动生成</p>
        </div>
    </div>
</body>
</html>
"""
    return html


@celery_app.task(
    bind=True,
    base=ReportTaskWithRetry,
    name="app.tasks.report.generate",
)
def generate_report(
    self,
    task_id: int,
    format: str = "html",
) -> dict[str, Any]:
    """
    生成检测报告

    Args:
        task_id: 任务 ID
        format: 报告格式 (html, pdf)

    Returns:
        dict: 报告生成结果
    """
    async def _generate():
        async with async_session_maker() as session:
            # 获取任务
            result = await session.execute(
                select(DetectionTask).where(DetectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            # 获取所有结果
            result = await session.execute(
                select(DBDetectionResult)
                .where(DBDetectionResult.task_id == task_id)
                .order_by(DBDetectionResult.similarity_score.desc())
            )
            results = result.scalars().all()

            # 生成报告
            if format == "html":
                report_content = generate_html_report(task_id, results)
                report_path = f"/reports/{task_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.html"
            elif format == "pdf":
                report_content = generate_html_report(task_id, results)
                # PDF 生成需要额外的库 (reportlab, weasyprint)
                report_path = f"/reports/{task_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
            else:
                return {"error": f"Unsupported format: {format}"}

            # 更新任务报告路径
            task.report_path = report_path
            await session.commit()

            return {
                "task_id": task_id,
                "format": format,
                "report_path": report_path,
                "total_results": len(results),
                "high_risk": sum(1 for r in results if r.risk_level == "high"),
                "medium_risk": sum(1 for r in results if r.risk_level == "medium"),
                "low_risk": sum(1 for r in results if r.risk_level == "low"),
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.report.generate_summary")
def generate_task_summary(task_id: int) -> dict[str, Any]:
    """生成任务摘要"""
    async def _generate():
        async with async_session_maker() as session:
            # 获取任务
            result = await session.execute(
                select(DetectionTask).where(DetectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            # 统计结果
            result = await session.execute(
                select(
                    DBDetectionResult.risk_level,
                    func.count(DBDetectionResult.id).label("count"),
                )
                .where(DBDetectionResult.task_id == task_id)
                .group_by(DBDetectionResult.risk_level)
            )
            stats = {row.risk_level: row.count for row in result.all()}

            # 平均相似度
            result = await session.execute(
                select(func.avg(DBDetectionResult.similarity_score))
                .where(DBDetectionResult.task_id == task_id)
            )
            avg_similarity = result.scalar() or 0

            return {
                "task_id": task_id,
                "status": task.status,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "total_results": sum(stats.values()),
                "high_risk": stats.get("high", 0),
                "medium_risk": stats.get("medium", 0),
                "low_risk": stats.get("low", 0),
                "avg_similarity": float(avg_similarity),
                "progress": task.progress,
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()
