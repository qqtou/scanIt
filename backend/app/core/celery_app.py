"""
Celery 异步任务配置

配置 Redis 作为消息代理和结果后端
"""
from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

# Celery 配置
celery_app = Celery(
    "scanit",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.detection", "app.tasks.report"],
)

# 路由配置
celery_app.conf.task_routes = {
    "app.tasks.detection.*": {"queue": "detection"},
    "app.tasks.report.*": {"queue": "report"},
    "app.tasks.alert.*": {"queue": "alert"},
}

# 队列配置
celery_app.conf.task_queues = (
    Queue("detection", Exchange("detection"), routing_key="detection"),
    Queue("report", Exchange("report"), routing_key="report"),
    Queue("alert", Exchange("alert"), routing_key="alert"),
    Queue("celery", Exchange("celery"), routing_key="celery"),
)

# 任务配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 小时超时
    task_soft_time_limit=3000,  # 50 分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,  # 每个 worker 最多执行 100 个任务后重启
    result_expires=86400,  # 结果 24 小时后过期
    task_acks_late=True,  # 任务执行完成后才确认
    task_reject_on_worker_lost=True,  # worker 丢失时重新排队
)

# Beat 调度器配置（定时任务）
celery_app.conf.beat_schedule = {
    "cleanup-expired-tasks": {
        "task": "app.tasks.maintenance.cleanup_expired_tasks",
        "schedule": 3600.0,  # 每小时执行一次
    },
    "cleanup-old-results": {
        "task": "app.tasks.maintenance.cleanup_old_results",
        "schedule": 86400.0,  # 每天执行一次
    },
    "sync-user-quota": {
        "task": "app.tasks.maintenance.sync_user_quota",
        "schedule": 300.0,  # 每 5 分钟执行一次
    },
}


def init_celery(app):
    """初始化 Celery 应用"""
    app.config_from_object("app.core.celery_app")
    return app
