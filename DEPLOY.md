# ScanIt 部署文档

## 环境要求

- Docker 24.0+
- Docker Compose v2.20+
- Git

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/scanit.git
cd scanit
```

### 2. 配置环境变量

```bash
cp .env.production .env
# 编辑 .env 填写实际配置
```

**必须配置项：**
- `POSTGRES_PASSWORD` - PostgreSQL 密码
- `JWT_SECRET_KEY` - JWT 密钥 (使用 `openssl rand -hex 32` 生成)

**可选配置项：**
- `GOOGLE_API_KEY` - Google Custom Search API
- `BING_API_KEY` - Bing Search API
- `BAIDU_API_KEY` - 百度搜索 API
- `SMTP_*` - 邮件通知配置

### 3. 启动服务 (生产环境)

```bash
docker-compose up -d
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 创建初始管理员用户
docker-compose exec backend python -c "
from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email='admin@scanit.com',
            username='admin',
            hashed_password=pwd_context.hash('your-password'),
            role='admin',
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin user created')

import asyncio
asyncio.run(create_admin())
"
```

## 开发环境

### 启动开发环境

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 服务地址

| 服务 | 地址 |
|------|------|
| 前端 (开发) | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| Flower 监控 | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## 生产环境

### 服务地址

| 服务 | 地址 |
|------|------|
| 前端 | http://your-domain.com |
| API 文档 | http://your-domain.com/docs |
| Flower | http://your-domain.com/flower |

### SSL 配置

将 SSL 证书放入 `ssl/` 目录：

```
ssl/
├── cert.pem   # 证书
└── key.pem    # 私钥
```

然后取消 nginx.conf 中 SSL 相关配置的注释。

### 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f celery-worker

# 重启服务
docker-compose restart backend

# 更新代码
git pull
docker-compose build
docker-compose up -d

# 数据库迁移
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic downgrade -1
```

## 数据备份

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U postgres scanit > backup_$(date +%Y%m%d).sql

# 备份 Redis
docker-compose exec redis redis-cli SAVE
docker cp scanit-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

## 监控

### Flower (Celery 监控)

访问 http://localhost:5555 (开发) 或 http://your-domain.com/flower (生产)

### 健康检查

```bash
curl http://localhost:8000/health
```

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查端口占用
netstat -tlnp | grep -E '5432|6379|8000|80'
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 健康状态
docker-compose ps postgres

# 手动连接测试
docker-compose exec postgres psql -U postgres -d scanit
```

### Celery 任务未执行

```bash
# 检查 worker 日志
docker-compose logs celery-worker

# 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 重启 worker
docker-compose restart celery-worker celery-beat
```

## 性能优化

### 后端

- 增加 `CELERY_WORKER_CONCURRENCY` 环境变量
- 使用 `CELERY_WORKER_POOL=prefork` 提升性能

### 前端

- Nginx 启用 gzip 压缩
- 配置 CDN 加速静态资源
- 启用 HTTP/2

### 数据库

- 定期执行 `VACUUM ANALYZE`
- 配置 PostgreSQL 连接池
- 使用只读副本分流查询

## 安全建议

1. **修改默认密码** - 立即修改 .env 中的默认密码
2. **JWT 密钥** - 使用强随机密钥
3. **SSL 证书** - 生产环境必须启用 HTTPS
4. **防火墙** - 只开放必要端口 (80, 443)
5. **定期更新** - 保持 Docker 镜像最新
