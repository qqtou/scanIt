"""
Celery 异步任务

导出所有任务
"""
from app.tasks import detection, report, maintenance, alert

__all__ = [
    "detection",
    "report",
    "maintenance",
    "alert",
]
