# ScanIt - 侵权内容检测系统

> 基于多搜索引擎的智能侵权检测平台，支持文本、图片、视频的全方位内容对比

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18.3-blue.svg)
![Docker](https://img.shields.io/badge/Docker-24.0+-blue.svg)

## 🎯 功能特性

### 核心功能
- **多类型检测** — 支持文本、图片、视频三种侵权类型检测
- **多搜索引擎** — 集成 Google、Bing、百度搜索，智能降级策略
- **SimHash 比对** — 文本相似度精确计算，近重复内容检测
- **感知哈希** — 图片/视频帧级特征提取与比对
- **异步任务** — Celery 分布式任务队列，支持大规模检测
- **定时任务** — 自动清理过期数据、同步配额、生成统计报告
- **告警通知** — 邮件/Webhook 多渠道侵权告警

### 用户功能
- **作品管理** — 作品上传、SimHash 预计算、分类管理
- **任务调度** — 单个/批量检测任务创建与进度跟踪
- **结果审核** — 检测结果确认/误报处理
- **报告导出** — PDF/CSV 格式检测报告下载
- **统计仪表盘** — 检测概览、趋势分析、配额使用

### 安全特性
- **JWT 认证** — Token 刷新机制，访问令牌 30 分钟有效
- **RBAC 权限** — 管理员/普通用户角色分离
- **软删除** — 数据可恢复，保护用户资产
- **敏感信息加密** — API 密钥等敏感配置加密存储

## 🛠️ 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI | Web 框架 |
| SQLAlchemy + asyncpg | 异步 ORM |
| Alembic | 数据库迁移 |
| Celery + Redis | 异步任务队列 |
| Pydantic v2 | 数据验证 |
| SimHash | 文本相似度 |
| Pillow + ResNet | 图片特征 |
| OpenCV | 视频处理 |

### 前端
| 技术 | 用途 |
|------|------|
| React 18 | UI 框架 |
| TypeScript | 类型安全 |
| Ant Design 5 | 组件库 |
| Axios | HTTP 客户端 |
| React Router | 路由管理 |

### 基础设施
| 技术 | 用途 |
|------|------|
| Docker + Compose | 容器化 |
| PostgreSQL | 主数据库 |
| Redis | 缓存/消息队列 |
| Nginx | 反向代理 |

## 📁 项目结构

```
scanit/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由
│   │   │   ├── auth.py
│   │   │   ├── works.py
│   │   │   ├── tasks.py
│   │   │   └── results.py
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── celery_app.py
│   │   ├── engines/        # 检测引擎
│   │   │   ├── searchers/  # 搜索引擎适配器
│   │   │   ├── comparators/ # 比对器
│   │   │   └── detector.py # 检测服务
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── tasks/          # Celery 任务
│   │   └── main.py         # 应用入口
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # 后端测试
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/            # API 客户端
│   │   ├── pages/           # 页面组件
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # 生产环境
├── docker-compose.dev.yml  # 开发环境
├── DEPLOY.md              # 部署文档
└── KANBAN.md              # 项目看板
```

## 🚀 快速开始

### 环境要求
- Docker 24.0+
- Docker Compose v2.20+

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

### 3. 启动服务
```bash
# 生产环境
docker-compose up -d

# 开发环境
docker-compose -f docker-compose.dev.yml up -d
```

### 4. 初始化数据库
```bash
docker-compose exec backend alembic upgrade head
```

### 5. 访问应用
- 前端：http://localhost:5173 (开发) / http://localhost (生产)
- API 文档：http://localhost:8000/docs
- Flower 监控：http://localhost:5555

## ⚙️ 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL 密码 |
| `JWT_SECRET_KEY` | ✅ | JWT 密钥 |
| `DATABASE_URL` | ✅ | 数据库连接 URL |
| `REDIS_URL` | ✅ | Redis 连接 URL |
| `GOOGLE_API_KEY` | ❌ | Google 搜索 API |
| `BING_API_KEY` | ❌ | Bing 搜索 API |
| `BAIDU_API_KEY` | ❌ | 百度搜索 API |
| `SMTP_*` | ❌ | 邮件通知配置 |

## 📖 API 文档

启动服务后访问 http://localhost:8000/docs 查看完整的 Swagger UI 文档。

### 主要接口

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | POST /api/v1/auth/login | 用户登录 |
| 认证 | POST /api/v1/auth/register | 用户注册 |
| 作品 | GET/POST /api/v1/works | 作品列表/创建 |
| 作品 | GET/PUT/DELETE /api/v1/works/{id} | 作品详情/更新/删除 |
| 任务 | GET/POST /api/v1/tasks | 任务列表/创建 |
| 任务 | GET/PUT /api/v1/tasks/{id} | 任务详情/更新 |
| 结果 | GET /api/v1/results | 检测结果列表 |
| 结果 | PUT /api/v1/results/{id}/review | 结果审核 |
| 统计 | GET /api/v1/dashboard/stats | 统计数据 |

## 🧪 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端测试
cd frontend
npm test
```

## 📈 项目看板

当前开发进度见 [KANBAN.md](KANBAN.md)。

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

**Built with ❤️ by ScanIt Team**
