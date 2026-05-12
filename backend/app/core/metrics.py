"""
Prometheus 指标收集模块
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from time import time
import threading

# 请求计数器
REQUEST_COUNT = Counter(
    'scanit_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'scanit_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 检测任务计数
DETECTION_COUNT = Counter(
    'scanit_detection_total',
    'Total detection tasks',
    ['tenant_id', 'content_type', 'status']
)

# 检测延迟
DETECTION_LATENCY = Histogram(
    'scanit_detection_duration_seconds',
    'Detection task latency',
    ['content_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

# 活跃任务数
ACTIVE_TASKS = Gauge(
    'scanit_active_tasks',
    'Number of active detection tasks'
)

# LLM Provider 调用
LLM_CALL_COUNT = Counter(
    'scanit_llm_calls_total',
    'Total LLM API calls',
    ['provider', 'tier', 'status']
)

# 配额使用
QUOTA_USAGE = Gauge(
    'scanit_quota_usage',
    'Tenant quota usage',
    ['tenant_id']
)


async def metrics_middleware(request: Request, call_next):
    """FastAPI 中间件：收集请求指标"""
    start_time = time()

    response = await call_next(request)

    # 记录请求
    elapsed = time() - start_time
    endpoint = request.url.path

    # 排除 metrics 端点自身
    if not endpoint.startswith('/metrics'):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(elapsed)

    return response


def metrics_endpoint():
    """Prometheus metrics 端点"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class MetricsCollector:
    """检测任务指标收集器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._active_count = 0
        return cls._instance

    def start_task(self, content_type: str):
        """任务开始"""
        ACTIVE_TASKS.inc()
        self._active_count += 1
        return time()

    def end_task(
        self,
        start_time: float,
        tenant_id: str,
        content_type: str,
        status: str
    ):
        """任务结束"""
        elapsed = time() - start_time
        ACTIVE_TASKS.dec()
        self._active_count -= 1

        DETECTION_COUNT.labels(
            tenant_id=tenant_id,
            content_type=content_type,
            status=status
        ).inc()

        DETECTION_LATENCY.labels(
            content_type=content_type
        ).observe(elapsed)

    def record_llm_call(
        self,
        provider: str,
        tier: str,
        status: str
    ):
        """记录 LLM 调用"""
        LLM_CALL_COUNT.labels(
            provider=provider,
            tier=tier,
            status=status
        ).inc()

    def update_quota(self, tenant_id: str, used: int, total: int):
        """更新配额使用率"""
        QUOTA_USAGE.labels(tenant_id=tenant_id).set(used / total if total > 0 else 0)


# 全局收集器实例
metrics = MetricsCollector()
