"""
ScanIt 全局配置
"""
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    # App
    app_name: str = "ScanIt"
    debug: bool = False  # 生产环境默认关闭
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]

    # Database
    # 默认 SQLite（本地开发），生产环境通过 .env 切换 PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./scanit_dev.db"
    database_pool_size: int = 0  # SQLite 不支持连接池

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant (向量数据库)
    qdrant_url: str = "http://localhost:6333"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT Authentication
    jwt_secret_key: str = Field(default="", json_schema_extra={"env": "JWT_SECRET_KEY"})  # 必填，无默认值
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # 搜索引擎分层配置
    search_provider: str = "google"  # google/bing/bocha/serpapi/brightdata

    # Tier 0: 免费测试
    google_api_key: str = ""
    google_search_engine_id: str = ""
    bing_api_key: str = ""
    baidu_api_key: str = ""

    # Tier 1: 低成本（博查 AI）
    bocha_api_key: str = ""

    # Tier 2: 企业级
    serpapi_key: str = ""
    brightdata_api_key: str = ""
    brightdata_zone: str = ""

    # 搜索降级策略
    search_fallback_order: List[str] = ["bocha", "google", "bing"]
    search_scrape_enabled: bool = False  # 禁用爬虫模式（推荐）

    # 搜索限流
    search_rate_limit: int = 10  # 每秒最多 10 次
    search_timeout: int = 30     # 超时 30 秒

    # 检测阈值
    text_similarity_threshold: float = 0.8
    image_similarity_threshold: float = 0.85
    video_similarity_threshold: float = 0.8

    # 任务配置
    max_search_results: int = 50
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@scanit.com"
    smtp_tls: bool = True

    # Webhook
    webhook_timeout: int = 10

    # Sentry 错误追踪
    sentry_dsn: str = ""  # Sentry DSN，为空则禁用
    app_version: str = "0.1.0"

    # LLM
    ollama_base_url: str = "http://localhost:11434"




settings = Settings()
