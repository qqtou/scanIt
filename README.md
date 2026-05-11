# ScanIt / 扫客 - 侵权检测系统

通过搜索引擎检索，对比文本、图片、视频，检测侵权内容。

## 功能

- 搜索引擎检索（Google、Bing、百度等）
- 文本侵权检测（大篇幅重复检测）
- 图片侵权检测（相似度、部分匹配）
- 视频侵权检测（关键帧比对）
- 报告生成与告警

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL + Qdrant |
| 比对引擎 | SimHash / PyTorch / OpenCV |
| 前端 | React + Ant Design |
| 部署 | Docker Compose |

## 快速开始

### 本地开发

```bash
# 1. 克隆项目
git clone <repo-url>
cd ScanIt

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，填入 API Keys

# 5. 启动服务
docker-compose up -d postgres redis qdrant
uvicorn app.main:app --reload

# 6. 访问
# API: http://localhost:8000/docs
```

### Docker 部署

```bash
docker-compose up -d
# 访问 http://localhost
```

## 项目结构

```
ScanIt/
├── backend/
│   ├── app/
│   │   ├── api/        # API 路由
│   │   ├── services/   # 业务逻辑
│   │   ├── models/     # 数据模型
│   │   ├── engines/   # 比对引擎
│   │   └── core/      # 核心配置
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       └── api/
├── docker/
├── scripts/
├── tests/
└── docker-compose.yml
```

## 配置

环境变量配置见 `backend/.env.example`：

- `DATABASE_URL` - PostgreSQL 连接
- `REDIS_URL` - Redis 连接
- `QDRANT_URL` - Qdrant 向量库
- `GOOGLE_API_KEY` / `GOOGLE_SEARCH_ENGINE_ID` - Google API
- `BING_API_KEY` - Bing API
- `BAIDU_API_KEY` - 百度 API

## 许可证

MIT