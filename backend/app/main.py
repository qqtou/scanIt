"""
ScanIt - 侵权检测系统后端
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="ScanIt API",
    description="侵权检测系统后端 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "ScanIt API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}