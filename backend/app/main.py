"""
ScanIt - 侵权检测系统后端
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.sentry import init_sentry
from app.core.metrics import metrics_middleware
from app.models.base import engine


# 限流器
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时校验必要配置
    if not settings.jwt_secret_key:
        raise ValueError("JWT_SECRET_KEY 环境变量未设置，拒绝启动")
    if len(settings.jwt_secret_key) < 32:
        raise ValueError("JWT_SECRET_KEY 长度不足 32 字符，请使用更安全的密钥")
    
    # 初始化 Sentry
    init_sentry()
    
    logger.info(f"ScanIt API 启动完成，debug={settings.debug}")
    
    yield
    # 关闭时
    await engine.dispose()
    logger.info("ScanIt API 已关闭")


app = FastAPI(
    title="ScanIt API",
    description="侵权检测系统后端 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 限流状态
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus 指标中间件
app.middleware("http")(metrics_middleware)

# Include API routes
app.include_router(api_router)


@app.get("/")
@limiter.limit("10/second")
async def root(request: Request):
    return {"message": "ScanIt API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    """Prometheus 指标端点"""
    return metrics_endpoint()
