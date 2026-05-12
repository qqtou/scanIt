# ScanIt 搜索引擎部署指南

**项目：** ScanIt/扫客
**日期：** 2026-05-12
**适用版本：** v1.0+

---

## 目录

1. [前置条件](#1-前置条件)
2. [快速部署](#2-快速部署)
3. [分层配置](#3-分层配置)
4. [验证测试](#4-验证测试)
5. [常见问题](#5-常见问题)

---

## 1. 前置条件

### 1.1 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 / macOS 10.15 / Ubuntu 20.04 | - |
| Docker | 24.0+ | 最新稳定版 |
| Docker Compose | v2.20+ | 最新稳定版 |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 10GB | 50GB+（含向量库） |

### 1.2 必需服务

| 服务 | 用途 | 默认端口 |
|------|------|----------|
| PostgreSQL | 主数据库 | 5432 |
| Redis | 缓存/消息队列 | 6379 |
| Qdrant | 向量数据库（可选） | 6333 |

### 1.3 必需 API Key

**至少配置以下任一搜索引擎 API Key**：

| 优先级 | API Key | 免费额度 | 申请地址 |
|--------|---------|----------|----------|
| **推荐** | `BOCHA_API_KEY` | 有试用 | https://open.bochaai.com |
| 备选 | `GOOGLE_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` | 100次/天 | https://console.cloud.google.com |
| 备选 | `BING_API_KEY` | 1000次/月 | https://portal.azure.com |

### 1.4 可选 API Key

| API Key | 用途 | 申请地址 |
|---------|------|----------|
| `JWT_SECRET_KEY` | JWT 签名密钥 | 随机生成 |
| `OLLAMA_BASE_URL` | 本地 LLM | http://localhost:11434 |
| `DOUYIN_API_KEY` | 豆包 LLM | https://console.volcengine.com |
| `ZHIPU_API_KEY` | 智谱 GLM-4 | https://open.bigmodel.cn |

---

## 2. 快速部署

### 2.1 克隆项目

```bash
git clone https://github.com/your-org/scanit.git
cd scanit
```

### 2.2 配置环境变量

**复制模板**：
```bash
cp .env.example .env
```

**编辑 `.env`**：
```env
# ============ 基础配置 ============
# 数据库（Docker 自动创建）
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@localhost:5432/scanit
REDIS_URL=redis://localhost:6379/0

# JWT 密钥（必须修改！）
JWT_SECRET_KEY=your_random_secret_key_at_least_32_chars

# ============ 搜索引擎配置 ============
# 推荐使用博查 AI（国内部署，数据不出海）
SEARCH_PROVIDER=bocha
BOCHA_API_KEY=your_bocha_api_key

# 或使用 Google Custom Search（免费 100 次/天）
# SEARCH_PROVIDER=google
# GOOGLE_API_KEY=AIzaSy...
# GOOGLE_SEARCH_ENGINE_ID=017576...

# 或使用 Bing（免费 1000 次/月）
# SEARCH_PROVIDER=bing
# BING_API_KEY=your_bing_key

# ============ LLM 配置（可选）============
# Tier 1: 本地（免费）
AI_TIER=local
OLLAMA_BASE_URL=http://localhost:11434

# Tier 2: 低成本云（¥1-10/月）
# AI_TIER=budget
# ZHIPU_API_KEY=your_zhipu_key

# ============ 爬虫配置 ============
# 禁用爬虫模式（推荐）
SEARCH_SCRAPE_ENABLED=false
```

### 2.3 启动服务

**开发环境**：
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**生产环境**：
```bash
docker-compose up -d
```

### 2.4 初始化数据库

```bash
# 运行迁移
docker-compose exec backend alembic upgrade head

# 创建默认租户（首次部署）
docker-compose exec backend python scripts/migrate_default_tenant.py
```

### 2.5 访问应用

| 服务 | 地址 |
|------|------|
| 前端（开发） | http://localhost:5173 |
| 前端（生产） | http://localhost |
| API 文档 | http://localhost:8000/docs |
| Flower 监控 | http://localhost:5555 |

---

## 3. 分层配置

### 3.1 Tier 0: 免费测试（推荐开发/演示）

**适用场景**：开发测试、功能演示、个人学习

#### 方案 A: Google Custom Search

**Step 1: 申请 API Key**

1. 访问 https://console.cloud.google.com
2. 创建项目 → 启用 "Custom Search JSON API"
3. 创建凭据 → API 密钥 → 复制

**Step 2: 创建搜索引擎**

1. 访问 https://cse.google.com/all
2. 点击 "添加"
3. 配置：
   - 名称：ScanIt Search
   - 搜索范围：搜索整个网络
   - 语言：简体中文
4. 创建后复制搜索引擎 ID（CX）

**Step 3: 配置**

```env
SEARCH_PROVIDER=google
GOOGLE_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_ENGINE_ID=017576662512468239146:omuauf_lfve
```

**限制**：100 次/天

---

#### 方案 B: Bing Web Search

**Step 1: 申请 API Key**

1. 访问 https://portal.azure.com
2. 创建资源 → 搜索 "Bing Search v7"
3. 定价层：F1（免费）
4. 获取 API Key

**Step 2: 配置**

```env
SEARCH_PROVIDER=bing
BING_API_KEY=your_bing_api_key
```

**限制**：1000 次/月

---

### 3.2 Tier 1: 低成本（推荐国内生产）

**适用场景**：个人项目、初创团队、月检测 < 10万

#### 方案: 博查 AI（推荐）

**Step 1: 申请 API Key**

1. 访问 https://open.bochaai.com
2. 微信扫码登录
3. 点击右上角 "API KEY 管理"
4. 点击 "创建 API Key"
5. 复制 API Key

**Step 2: 配置**

```env
SEARCH_PROVIDER=bocha
BOCHA_API_KEY=bocha_xxxxxxxxxxxxx
```

**优势**：
- ✅ 国内部署，延迟 < 200ms
- ✅ 数据不出海，符合合规要求
- ✅ 中文搜索优化
- ✅ ¥0.002/次，月 3 万次仅 ¥60

---

### 3.3 Tier 2: 企业级

**适用场景**：专业版权机构、大规模检测

#### 方案: Bright Data SERP API

**Step 1: 申请 Bright Data**

1. 访问 https://brightdata.com
2. 注册账户
3. 创建 SERP API Zone
4. 获取 API Key 和 Zone 名称

**Step 2: 配置**

```env
SEARCH_PROVIDER=brightdata
BRIGHTDATA_API_KEY=your_api_key
BRIGHTDATA_UNLOCKER_ZONE=serp_api
```

**优势**：
- ✅ 99.9% 成功率
- ✅ 全球 195+ 国家代理
- ✅ 自动绕过反爬

---

## 4. 验证测试

### 4.1 检查搜索引擎配置

```bash
cd backend

# 方式 1: Python 脚本
python -c "
from app.engines.searchers.selector import list_available_searchers
print('可用搜索引擎:', list_available_searchers())
"

# 方式 2: API 测试
curl http://localhost:8000/api/search/providers
```

### 4.2 测试搜索功能

```bash
cd backend

python -c "
import asyncio
from app.engines.searchers import get_searcher

async def test():
    searcher = get_searcher()
    print(f'使用搜索引擎: {searcher.name}')
    
    results = []
    async for r in searcher.search('Python FastAPI'):
        results.append(r)
        print(f'  - {r.title}: {r.url}')
    
    print(f'找到 {len(results)} 条结果')

asyncio.run(test())
"
```

### 4.3 运行测试套件

```bash
cd backend
pytest tests/ -v -k "search"
```

---

## 5. 常见问题

### Q1: 未配置 API Key 报错

**错误信息**：
```
ValueError: 未配置任何搜索引擎 API Key
```

**解决方案**：
```env
# 在 .env 中配置至少一个 API Key
SEARCH_PROVIDER=bocha
BOCHA_API_KEY=your_key
```

---

### Q2: 网页抓取被禁用

**错误信息**：
```
ValueError: 网页抓取模式已禁用
```

**原因**：爬虫模式存在反爬风险，默认禁用

**解决方案 A（推荐）**：配置官方 API Key

**解决方案 B（不推荐）**：强制启用爬虫
```env
SEARCH_SCRAPE_ENABLED=true
```

---

### Q3: Google API 返回 403

**原因**：
- API Key 未启用 Custom Search API
- 免费额度已用完（100 次/天）
- CX 配置错误

**解决方案**：
1. 检查 API Key 是否启用 Custom Search API
2. 检查 CX 是否正确
3. 查看配额使用：https://console.cloud.google.com → API 和服务 → 凭据

---

### Q4: 博查 API 返回 401

**原因**：API Key 无效或过期

**解决方案**：
1. 重新申请 API Key：https://open.bochaai.com
2. 检查 Key 格式（应以 `bocha_` 开头）

---

### Q5: 搜索结果为空

**可能原因**：
1. 关键词过于特殊
2. API 限流
3. 网络问题

**排查步骤**：
```bash
# 查看日志
docker-compose logs backend | grep -i search

# 测试 API 连通性
curl -X POST "https://api.bochaai.com/v1/web-search" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "count": 5}'
```

---

## 6. 成本参考

| 月检测量 | Tier 0 | Tier 1 (博查) | Tier 2 (Bright Data) |
|----------|--------|---------------|----------------------|
| 100 | ¥0 | ¥0.2 | - |
| 1,000 | ¥0 | ¥2 | - |
| 3,000 | 超限 | ¥6 | - |
| 10,000 | 超限 | ¥20 | - |
| 30,000 | 超限 | ¥60 | $500 |
| 100,000 | 超限 | ¥200 | $1,500 |

---

## 7. 安全建议

1. **JWT_SECRET_KEY**：使用强随机密钥（至少 32 字符）
   ```bash
   # 生成随机密钥
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **API Key 管理**：
   - ✅ 通过环境变量配置
   - ❌ 禁止硬编码在代码中
   - ❌ 禁止提交到 Git

3. **爬虫模式**：
   - ✅ 保持禁用（默认）
   - ❌ 仅在测试环境启用

4. **数据安全**：
   - ✅ 博查 AI 数据不出海（国内部署）
   - ✅ 符合数据合规要求

---

**文档版本：** v1.0
**最后更新：** 2026-05-12
