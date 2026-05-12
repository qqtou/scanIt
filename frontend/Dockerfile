# ScanIt 前端 Dockerfile - 多阶段构建
# Stage 1: Builder
FROM node:26-alpine AS builder

WORKDIR /app

# 安装依赖
COPY frontend/package*.json ./
RUN npm ci

# 复制源代码
COPY frontend/ ./

# 构建
RUN npm run build

# Stage 2: Nginx Runtime
FROM nginx:alpine AS runtime

# 复制 nginx 配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 从 builder 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
