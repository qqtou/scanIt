# ScanIt / 扫客 — 多租户侵权检测平台

> AI 驱动的智能侵权检测系统，支持多租户 SaaS 部署，覆盖文本、图片、视频全类型检测

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18.3-blue.svg)
![Docker](https://img.shields.io/badge/Docker-24.0+-blue.svg)
![Tests](https://img.shields.io/badge/Tests-68%20passed-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 功能特性

### 核心检测能力
- **多类型检测** — 文本（SimHash）、图片（pHash + CNN）、视频（帧采样）
- **多搜索引擎** — Google、Bing、百度，智能降级策略
- **AI 关键词生成** — LLM 智能提取搜索关键词，比规则更全面
- **AI 侵权报告** — 自动生成专业分析报告，支持中英文
- **双引擎融合** — pHash（快速过滤）+ MobileNetV2（精准识别），相似度加权融合

### 多租户 SaaS 架构
- **租户隔离** — Tenant ID 逻辑隔离，数据安全隔离
- **双门户入口** — `/app` 用户端 + `/admin` 管理端
- **四级角色体系** — system_admin / tenant_admin / reviewer / user
- **配额管理** — 按租户配额限制检测次数，超额返回 429
- **邀请码注册** — 支持邀请码绑定租户，无邀请码分配默认租户

### LLM 三层架构
| Tier | Provider | 成本 | 适用场景 |
|------|----------|------|----------|
| Tier 1 | Ollama（本地） | **¥0** | 涉密机构、隐私敏感 |
| Tier 2 | 豆包/智谱/Kimi | ¥1-10/月 | 摄影师、版权机构 |
| Tier 3 | GPT-4o/Claude/通义 | ¥500+/月 | 大型企业 |

### 用户功能
- **作品管理** — 上传、预计算、分类、批量检测
- **任务调度** — Celery 异步队列，进度跟踪
- **结果审核** — 确认/误报处理、风险评级
- **报告导出** — PDF/CSV 格式
- **管理后台** — 租户管理、用户管理、配额配置

### AI 分层架构（Tier 1-3）

| Tier | 模式 | 代表方案 | 成本 | 适用场景 |
|------|------|---------|------|---------|
| Tier 1 | 本地推理 | Ollama + Llama3/Qwen2 | **¥0** | 有 GPU 的开发者 |
| Tier 2 | 低成本云 | 豆包/智谱 GLM-4/Kimi | ¥1-10/月 | 个人摄影师 |
| Tier 3 | 企业级 | GPT-4o / 通义千问 | ¥500+/月 | 专业版权机构 |

### 安全特性
- **JWT 认证** — Token 含 tenant_id + role，30 分钟有效
- **RBAC 权限** — 四级角色，API 级权限控制
- **软删除** — 数据可恢复
- **环境变量密钥** — JWT_SECRET_KEY 强制环境变量，禁止硬编码

##  技术栈

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

### AI / LLM
| 技术 | 用途 |
|------|------|
| Ollama | Tier1 本地推理引擎 |
| 豆包 (doubao-pro-32k) | Tier2 低成本中文生成 |
| 智谱 GLM-4 / GLM-4V | Tier2 中文生成 + 图片理解 |
| Kimi (moonshot-v1-128k) | Tier2 超长上下文 |
| 阿里通义千问 (qwen-vl-max) | Tier3 企业级图片理解 |
| OpenAI GPT-4o | Tier3 企业级多模态 |
| Anthropic Claude | Tier3 企业级推理 |

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
ScanIt/
├── backend/                         # FastAPI 后端
│   ├── app/
│   │   ├── api/                     # API 路由层（8 个模块）
│   │   │   ├── auth.py              # 认证（JWT + 邀请码注册）
│   │   │   ├── deps.py              # 依赖注入（租户/用户/权限）
│   │   │   ├── tenants.py           # 租户 CRUD + 用户管理
│   │   │   ├── middleware.py        # 配额检查中间件
│   │   │   ├── llm.py               # LLM 配置/检测/报告 API
│   │   │   ├── works.py             # 作品管理
│   │   │   ├── tasks.py             # 检测任务
│   │   │   └── results.py           # 检测结果
│   │   ├── core/                    # 核心配置
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   └── celery_app.py        # Celery 任务调度
│   │   ├── engines/                 # 核心引擎（13 个模块）
│   │   │   ├── detector.py          # 基础检测服务
│   │   │   ├── detector_llm.py      # LLM 增强检测
│   │   │   ├── comparators/         # 相似度比较器
│   │   │   │   ├── image.py         # pHash + CNN 融合
│   │   │   │   ├── text.py          # SimHash
│   │   │   │   └── video.py         # 帧采样 + 图片比对
│   │   │   ├── searchers/           # 搜索引擎适配器
│   │   │   │   ├── google.py
│   │   │   │   ├── bing.py
│   │   │   │   └── baidu.py
│   │   │   └── llm_provider/        # LLM Provider 三层架构
│   │   │       ├── base.py          # BaseProvider 抽象基类
│   │   │       ├── local.py         # Tier 1: Ollama 本地
│   │   │       ├── cloud.py         # Tier 2-3: 云端 Provider
│   │   │       └── manager.py       # Provider 选择/降级管理
│   │   ├── models/                  # SQLAlchemy 模型（6 个）
│   │   │   ├── tenant.py            # 租户模型（M6 新增）
│   │   │   ├── user.py              # 用户（含 tenant_id FK）
│   │   │   ├── work.py              # 作品
│   │   │   ├── task.py              # 任务
│   │   │   └── result.py            # 结果
│   │   ├── schemas/                 # Pydantic Schema（6 个）
│   │   │   ├── tenant.py            # 租户 Schema（M6 新增）
│   │   │   └── ...
│   │   ├── tasks/                   # Celery 异步任务
│   │   │   ├── detection.py         # 检测任务
│   │   │   ├── report.py            # 报告生成
│   │   │   ├── alert.py             # 告警通知
│   │   │   └── maintenance.py       # 定时维护
│   │   └── main.py                  # 应用入口
│   ├── alembic/                     # 数据库迁移
│   │   └── versions/
│   │       └── m6_001_multi_tenant.py  # M6 多租户迁移
│   ├── scripts/                     # 工具脚本
│   │   └── migrate_default_tenant.py   # 数据迁移脚本
│   ├── tests/                       # 测试套件（68 passed）
│   ├── .env                         # 环境变量
│   ├── pyproject.toml               # 项目配置
│   └── requirements.txt             # 依赖
│
├── frontend/                        # React + TypeScript 前端
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # API 客户端（含 tenantsApi）
│   │   ├── pages/                   # 页面组件（7 个）
│   │   │   ├── AdminDashboard.tsx   # 管理后台（M6 新增）
│   │   │   ├── Dashboard.tsx        # 用户仪表盘
│   │   │   ├── Works.tsx            # 作品管理
│   │   │   ├── Tasks.tsx            # 任务列表
│   │   │   ├── Reports.tsx          # 报告查看
│   │   │   └── Settings.tsx         # 设置（含 LLM 配置）
│   │   ├── App.tsx                  # 双门户路由
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docker/                          # Docker 配置
├── docs/                             # 文档
│   ├── DESIGN_MULTI_TENANT.md       # M6 架构设计
│   ├── 概要设计.md
│   └── 需求设计.md
│
├── KANBAN.md                        # 项目看板
├── README.md                         # 项目说明
├── DEPLOY.md                         # 部署文档
├── AI_ENHANCEMENT.md                 # LLM 增强设计
├── AI_PROVIDER_ARCHITECTURE.md       # Provider 三层架构
├── docker-compose.yml                # 生产编排
└── docker-compose.dev.yml            # 开发编排
```

### 模块统计

| 模块 | 数量 | 说明 |
|------|------|------|
| API 路由 | 8 | auth, deps, tenants, middleware, llm, works, tasks, results |
| 核心引擎 | 13 | detector, detector_llm, 4 comparators, 3 searchers, 5 llm_provider |
| 数据模型 | 6 | tenant, user, work, task, result, base |
| Schema | 6 | auth, tenant, user, work, task, result |
| Celery 任务 | 4 | detection, report, alert, maintenance |
| 测试 | 5 | conftest, test_api, test_engines, test_llm_provider, test_models |
| 前端页面 | 7 | AdminDashboard, Dashboard, Works, Tasks, Reports, Settings, App |

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

### 基础配置
| 变量 | 必填 | 说明 |
|------|------|------|
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL 密码 |
| `JWT_SECRET_KEY` | ✅ | JWT 密钥 |
| `DATABASE_URL` | ✅ | 数据库连接 URL |
| `REDIS_URL` | ✅ | Redis 连接 URL |

### 搜索引擎
| 变量 | 必填 | 说明 |
|------|------|------|
| `GOOGLE_API_KEY` | ❌ | Google 搜索 API |
| `BING_API_KEY` | ❌ | Bing 搜索 API |
| `BAIDU_API_KEY` | ❌ | 百度搜索 API |

### 邮件
| 变量 | 必填 | 说明 |
|------|------|------|
| `SMTP_HOST` | ❌ | SMTP 服务器 |
| `SMTP_PORT` | ❌ | SMTP 端口 |
| `SMTP_USER` | ❌ | SMTP 用户名 |
| `SMTP_PASSWORD` | ❌ | SMTP 密码 |

### AI / LLM 配置
| 变量 | 必填 | 说明 |
|------|------|------|
| `OLLAMA_BASE_URL` | Tier1 | Ollama 服务地址（默认 http://localhost:11434）|
| `OLLAMA_MODEL` | Tier1 | Ollama 模型名（默认 llama3.2）|
| `OLLAMA_EMBED_MODEL` | Tier1 | Ollama Embedding 模型（默认 nomic-embed-text）|
| `AI_TIER` | ❌ | AI 模式：local / budget / enterprise（默认 local）|
| `DOUYIN_API_KEY` | Tier2 | 豆包 API Key（¥0.001/K tokens）|
| `ZHIPU_API_KEY` | Tier2 | 智谱 GLM-4 API Key（¥0.01/K tokens）|
| `KIMI_API_KEY` | Tier2 | Kimi API Key（¥0.01/K tokens）|
| `ALIYUN_API_KEY` | Tier3 | 阿里云百炼 API Key |
| `OPENAI_API_KEY` | Tier3 | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Tier3 | Anthropic API Key |

## 📖 API 文档

启动服务后访问 http://localhost:8000/docs 查看 Swagger UI。

### 认证接口
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/auth/login | POST | 用户登录 |
| /api/auth/register | POST | 用户注册（支持邀请码） |
| /api/auth/me | GET | 当前用户信息 |

### 租户接口（system_admin）
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/system/tenants | GET/POST | 租户列表/创建 |
| /api/system/tenants/{id} | GET/PUT/DELETE | 租户详情/更新/删除 |

### 租户管理接口（tenant_admin）
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/admin/quota | GET/PUT | 配额查看/配置 |
| /api/admin/settings | GET/PUT | 租户设置 |
| /api/admin/users | GET | 用户列表 |
| /api/admin/users/{id} | GET/PUT/DELETE | 用户管理 |

### 业务接口
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/works | GET/POST | 作品列表/创建 |
| /api/works/{id} | GET/PUT/DELETE | 作品详情/更新/删除 |
| /api/tasks | GET/POST | 任务列表/创建 |
| /api/tasks/{id} | GET/PUT | 任务详情/更新 |
| /api/results | GET | 检测结果列表 |
| /api/results/{id}/review | PUT | 结果审核 |

### LLM 接口
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/llm/providers/status | GET | Provider 状态 |
| /api/llm/providers/switch | POST | 切换 Provider/Tier |
| /api/llm/providers/cost | GET | 费用汇总 |
| /api/llm/detect | POST | LLM 增强检测 |
| /api/llm/report | POST | 生成报告 |

## 🤖 AI 配置指南

### Tier 1: 本地推理（免费）

适合有 NVIDIA GPU 的开发者，模型完全本地运行，数据不外传。

**安装 Ollama：**
```bash
# macOS / Linux
brew install ollama && ollama serve

# Windows: https://ollama.com/download
# 下载安装后运行: ollama serve

#拉取模型
ollama pull llama3.2        # 文本生成（约 2GB）
ollama pull nomic-embed-text # 向量化（约 274MB）
ollama pull llava           # 图片理解（约 4.7GB，可选）
```

**环境变量配置（.env）：**
```env
AI_TIER=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text
```

**Docker Compose（后端 + Ollama）：**
```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Tier 2: 低成本云（¥1-10/月）

适合个人用户，无需 GPU，按量付费。

**申请 API Key：**

| 服务商 | 获取地址 | 定价 |
|--------|---------|------|
| 豆包 | https://console.volcengine.com/ark | ¥0.001/K tokens |
| 智谱 | https://open.bigmodel.cn/ | ¥0.01/K tokens |
| Kimi | https://platform.moonshot.cn/ | ¥0.01/K tokens |

**环境变量配置（.env）：**
```env
AI_TIER=budget
# 至少填写一个
DOUYIN_API_KEY=your_douyin_key
ZHIPU_API_KEY=your_zhipu_key
KIMI_API_KEY=your_kimi_key
```

### Tier 3: 企业级（¥500+/月）

适合专业版权机构，需要更高准确率。

**申请 API Key：**

| 服务商 | 获取地址 | 定价 |
|--------|---------|------|
| 阿里云百炼 | https://help.aliyun.com/zh/model-studio/ | ¥0.02/K tokens |
| OpenAI | https://platform.openai.com/ | $0.003/K tokens |
| Anthropic | https://console.anthropic.com/ | $0.015/K tokens |

**环境变量配置（.env）：**
```env
AI_TIER=enterprise
# 至少填写一个
ALIYUN_API_KEY=your_aliyun_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 前端实时切换

在 Settings 页面（⚙️）的 AI 设置面板中，可以：
- 实时切换 Tier（local / budget / enterprise）
- 查看各 Provider 的连接状态
- 查看 AI 调用费用汇总

## 🎬 Demo 演示

运行以下命令快速体验不同 Tier 的效果对比：

```bash
cd backend

# Tier 1 (本地，需先安装 Ollama + 模型)
python demo_tiers.py

# Tier 2 (低成本云)
$env:AI_TIER="budget"
$env:ZHIPU_API_KEY="your_key"
python demo_tiers.py

# Tier 3 (企业级)
$env:AI_TIER="enterprise"
$env:OPENAI_API_KEY="your_key"
python demo_tiers.py
```

演示内容：
- Provider 状态检测
- 关键词生成对比（LLM vs 规则提取）
- 图片侵权深度分析
- LLM 侵权报告生成
- Embedding 语义相似度计算

## 🧪 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端测试
cd frontend
npm test
```

## 📊 项目进度

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0-M5 | ✅ 100% | 基础功能 |
| M6 | ✅ 100% | 多租户架构 |
| LLM 增强 | ✅ 100% | 三层 Provider |
| 测试 | ✅ 68 passed | 全部通过 |

详细看板见 [KANBAN.md](KANBAN.md)。

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
