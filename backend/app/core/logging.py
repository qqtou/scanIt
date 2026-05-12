"""
日志配置
"""
import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> logging.Logger:
    """配置统一日志"""
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 根日志器
    logger = logging.getLogger("scanit")
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    # 格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
    file_handler = logging.FileHandler(
        log_dir / "app.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误文件输出
    error_handler = logging.FileHandler(
        log_dir / "error.log",
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # 屏蔽第三方库日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logger


logger = setup_logging()
