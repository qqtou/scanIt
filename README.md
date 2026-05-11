# ScanIt - 侵权内容检测系统

> 基于多搜索引擎的智能侵权检测平台，支持文本、图片、视频的全方位内容对比

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18.3-blue.svg)
![Docker](https://img.shields.io/badge/Docker-24.0+-blue.svg)
![CI](https://github.com/your-org/scanit/actions/workflows/ci.yml/badge.svg)
![Tests](https://img.shields.io/badge/Tests-78%20passed-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

##  功能特性

### 核心功能
- **多类型检测** — 支持文本、图片、视频三种侵权类型检测
- **多搜索引擎** — 集成 Google、Bing、百度搜索，智能降级策略
- **SimHash 比对** — 文本相似度精确计算，近重复内容检测
- **感知哈希** — 图片/视频帧级特征提取与比对
- **AI 关键词生成** — LLM 智能生成搜索关键词，比规则提取更全面
- **AI 侵权报告** — LLM 生成专业侵权分析报告，支持文本/图片/视频
- **异步任务** — Celery 分布式任务队列，支持大规模检测
- **定时任务** — 自动清理过期数据、同步配额、生成统计报告
- **告警通知** — 邮件/Webhook 多渠道侵权告警

### 用户功能
- **作品管理** — 作品上传、SimHash 预计算、分类管理
- **任务调度** — 单个/批量检测任务创建与进度跟踪
- **结果审核** — 检测结果确认/误报处理
- **报告导出** — PDF/CSV 格式检测报告下载
- **统计仪表盘** — 检测概览、趋势分析、配额使用
- **AI 设置面板** — 前端实时切换 LLM Provider / Tier，查看费用

### AI 分层架构（Tier 1-3）

| Tier | 模式 | 代表方案 | 成本 | 适用场景 |
|------|------|---------|------|---------|
| Tier 1 | 本地推理 | Ollama + Llama3/Qwen2 | **¥0** | 有 GPU 的开发者 |
| Tier 2 | 低成本云 | 豆包/智谱 GLM-4/Kimi | ¥1-10/月 | 个人摄影师 |
| Tier 3 | 企业级 | GPT-4o / 通义千问 | ¥500+/月 | 专业版权机构 |

### 安全特性
- **JWT 认证** — Token 刷新机制，访问令牌 30 分钟有效
- **RBAC 权限** — 管理员/普通用户角色分离
- **软删除** — 数据可恢复，保护用户资产
- **敏感信息加密** — API 密钥等敏感配置加密存储

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

##  项目结构

```
scanit/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由
│   │   │   ├── auth.py
│   │   │   ├── works.py
│   │   │   ├── tasks.py
│   │   │   ├── results.py
│   │   │   └── llm.py      # LLM 增强检测 API
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── celery_app.py
│   │   ├── engines/        # 检测引擎
│   │   │   ├── searchers/  # 搜索引擎适配器
│   │   │   ├── comparators/ # 比对器
│   │   │   ├── detector.py      # 基础检测服务
│   │   │   ├── detector_llm.py   # LLM 增强检测服务
│   │   │   └── llm_provider/    # AI Provider 分层架构
│   │   │       ├── __init__.py  # 单例 + 快捷函数
│   │   │       ├── base.py      # BaseProvider + 枚举
│   │   │       ├── local.py     # Ollama (Tier1)
│   │   │       ├── cloud.py      # 云端 Provider (Tier2/3)
│   │   │       └── manager.py    # ProviderManager
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── tasks/          # Celery 任务
│   │   └── main.py         # 应用入口
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # 后端测试
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts   # 包含 llmApi
│   │   ├── pages/
│   │   │   ├── Settings.tsx # 含 AI 设置面板
│   │   │   └── ...
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml        # 生产环境
├── docker-compose.dev.yml   # 开发环境
├── DEPLOY.md               # 部署文档
├── AI_PROVIDER_ARCHITECTURE.md # AI 分层架构设计
└── KANBAN.md               # 项目看板
```

##  快速开始

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

##  环境变量

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

##  API 文档

启动服务后访问 http://localhost:8000/docs 查看完整的 Swagger UI 文档。

### 认证接口
| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | POST /api/auth/login | 用户登录 |
| 认证 | POST /api/auth/register | 用户注册 |
| 认证 | GET /api/auth/me | 当前用户信息 |

### 作品接口
| 模块 | 端点 | 说明 |
|------|------|------|
| 作品 | GET/POST /api/works | 作品列表/创建 |
| 作品 | GET/PUT/DELETE /api/works/{id} | 作品详情/更新/删除 |

### 任务接口
| 模块 | 端点 | 说明 |
|------|------|------|
| 任务 | GET/POST /api/tasks | 任务列表/创建 |
| 任务 | GET/PUT /api/tasks/{id} | 任务详情/更新 |

### 结果接口
| 模块 | 端点 | 说明 |
|------|------|------|
| 结果 | GET /api/results | 检测结果列表 |
| 结果 | PUT /api/results/{id}/review | 结果审核 |

### LLM AI 接口
| 模块 | 端点 | 说明 |
|------|------|------|
| LLM | GET /api/llm/providers/status | 获取所有 Provider 状态 |
| LLM | POST /api/llm/providers/switch | 切换 Provider 或 Tier |
| LLM | GET /api/llm/providers/cost | 获取费用汇总 |
| LLM | POST /api/llm/detect | LLM 增强侵权检测 |
| LLM | POST /api/llm/report | 生成 LLM 侵权分析报告 |

##  AI 配置指南

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

##  Demo 演示

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

##  运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端测试
cd frontend
npm test
```

##  项目看板

当前开发进度见 [KANBAN.md](KANBAN.md)。

##  贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

##  许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

**Built with ❤️ by ScanIt Team**
