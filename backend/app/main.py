"""
ScanIt - 侵权检测系统后端
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.models.base import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    yield
    # 关闭时
    await engine.dispose()


app = FastAPI(
    title="ScanIt API",
    description="侵权检测系统后端 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "ScanIt API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
