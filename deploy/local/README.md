# ScanIt 本机部署指南

本目录包含 Windows 本机开发环境的快速部署脚本。

## 文件说明

| 文件 | 用途 |
|------|------|
| `docker-compose.dev.yml` | 开发环境容器编排配置 |
| `.env.example` | 环境变量模板 |
| `start.ps1` | 一键启动脚本 |
| `stop.ps1` | 停止脚本 |
| `logs.ps1` | 日志查看脚本 |

## 快速开始

### 1. 前置条件

1. **安装 Docker Desktop for Windows**
   - 下载地址: https://www.docker.com/products/docker-desktop
   - 安装后启动 Docker Desktop，确保状态为 "Running"

2. **配置 Ollama（可选，用于本地 LLM）**
   ```powershell
   # 安装 Ollama
   winget install Ollama.Ollama
   
   # 启动服务
   ollama serve
   
   # 下载模型
   ollama pull llama3.2
   ```

### 2. 配置环境变量

```powershell
# 复制模板
copy deploy\local\.env.example .env

# 编辑 .env，填写以下配置：
# - GOOGLE_API_KEY 或 BOCHA_API_KEY（搜索引擎，至少一个）
# - JWT_SECRET_KEY（建议运行命令生成）
```

**生成 JWT 密钥**：
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. 启动服务

```powershell
# 首次启动（构建镜像）
.\deploy\local\start.ps1 -Build

# 后续启动（不重新构建）
.\deploy\local\start.ps1
```

### 4. 访问应用

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| Flower (Celery 监控) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## 常用命令

```powershell
# 停止服务
.\deploy\local\stop.ps1

# 停止并清理所有数据（重置）
.\deploy\local\stop.ps1 -Clean

# 查看所有服务日志
.\deploy\local\logs.ps1 -Follow

# 查看后端日志
.\deploy\local\logs.ps1 backend -Tail 100

# 进入后端容器
docker exec -it scanit-backend bash

# 运行数据库迁移
docker exec scanit-backend alembic upgrade head

# 创建管理员用户
docker exec scanit-backend python -m scripts.create_admin
```

## 故障排查

### 问题 1: 端口被占用

错误信息：`Error: port is already allocated`

**解决方案**：
```powershell
# 查看端口占用
netstat -ano | findstr ":3000"
netstat -ano | findstr ":8000"

# 停止占用端口的进程（用 PID 替换 <PID>）
taskkill /PID <PID> /F
```

### 问题 2: Docker Desktop 未启动

错误信息：`error during connect: This error may indicate that the docker daemon is not running`

**解决方案**：
启动 Docker Desktop 并等待其完全启动（状态栏图标变为绿色）

### 问题 3: 数据库连接失败

错误信息：`Connection refused` 或 `database "scanit" does not exist`

**解决方案**：
```powershell
# 重启服务
.\deploy\local\stop.ps1
.\deploy\local\start.ps1

# 检查数据库状态
docker exec scanit-postgres pg_isready
```

### 问题 4: Ollama 连接失败

错误信息：`Failed to connect to Ollama at http://host.docker.internal:11434`

**解决方案**：
1. 确保 Ollama 已安装并运行：`ollama serve`
2. 确保已下载模型：`ollama pull llama3.2`
3. Docker Desktop 需启用 "Expose daemon on tcp://localhost:2375"

## 数据持久化

数据存储在 Docker Volume 中：
- `scanit_postgres_dev` - PostgreSQL 数据
- `scanit_redis_dev` - Redis 数据

**备份数据库**：
```powershell
docker exec scanit-postgres pg_dump -U postgres scanit > backup.sql
```

**恢复数据库**：
```powershell
Get-Content backup.sql | docker exec -i scanit-postgres psql -U postgres scanit
```

## 下一步

- 阅读 [API 文档](http://localhost:8000/docs) 了解接口
- 查看 [DEPLOY.md](../../DEPLOY.md) 了解生产部署
- 查看 [docs/DESIGN_MULTI_TENANT.md](../../docs/DESIGN_MULTI_TENANT.md) 了解架构设计
