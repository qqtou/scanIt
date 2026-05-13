# ScanIt 后端 Dockerfile - 多阶段构建
# Stage 1: Builder
FROM python:3.14-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir --prefix=/install -e .

# Stage 2: Runtime
FROM python:3.14-slim AS runtime

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# 从 builder 复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY --chown=appuser:appuser backend/ ./app/

# 切换到非 root 用户
USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
