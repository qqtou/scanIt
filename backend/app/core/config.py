"""
ScanIt 全局配置
"""
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    # App
    app_name: str = "ScanIt"
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/scanit"
    database_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant (向量数据库)
    qdrant_url: str = "http://localhost:6333"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"  # 请在生产环境替换
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # API Keys (请替换为真实密钥)
    google_api_key: str = ""
    google_search_engine_id: str = ""
    bing_api_key: str = ""
    baidu_api_key: str = ""

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




settings = Settings()
