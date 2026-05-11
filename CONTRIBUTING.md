# ScanIt 开发规范

## 分支策略

```
main          ──── 生产环境代码 ──── 只接受 PR 合并
    │
    └── dev   ──── 开发主分支 ──── 日常开发合并目标
          │
          └── feature/*   ──── 功能分支
          └── bugfix/*    ──── 修复分支
          └── hotfix/*    ──── 紧急修复分支
```

### 分支命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 功能 | `feature/<issue-id>-<简短描述>` | `feature/123-user-auth` |
| 修复 | `bugfix/<issue-id>-<简短描述>` | `bugfix/456-fix-login` |
| 热修 | `hotfix/<issue-id>-<简短描述>` | `hotfix/789-critical-security` |
| 重构 | `refactor/<模块名>-<简短描述>` | `refactor/search-engine` |

### 工作流程

```bash
# 1. 从 dev 创建功能分支
git checkout dev
git pull origin dev
git checkout -b feature/123-add-search

# 2. 开发 & 提交
git add .
git commit -m "feat: 添加搜索功能"

# 3. 保持 dev 最新
git fetch origin
git rebase origin/dev

# 4. 推送 & 创建 PR
git push -u origin feature/123-add-search
# 在 GitHub/GitLab 创建 Pull Request

# 5. Code Review 后合并到 dev
```

## 提交信息规范

### 格式

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（非新功能非修复） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖更新 |
| `ci` | CI/CD 配置 |

### 示例

```bash
# 新功能
git commit -m "feat(search): 添加 Google 搜索适配器

- 实现 SearchEngineAdapter 接口
- 支持分页和去重
- 关闭 #123"

# Bug 修复
git commit -m "fix(image): 修复 pHash 计算时内存溢出

问题：处理大图片时 OOM
解决方案：添加图片尺寸限制和缩放

关闭 #456"

# 重构
git commit -m "refactor(config): 迁移配置到 Pydantic Settings"
```

## 代码规范

### Python (后端)

- 遵循 PEP 8
- 使用 Black 格式化代码 (line-length: 100)
- 使用 Ruff 检查代码
- 使用 Mypy 进行类型检查
- 所有公共函数/类必须添加 docstring

```python
def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度。

    Args:
        text1: 源文本
        text2: 目标文本

    Returns:
        相似度分数，范围 0.0 - 1.0

    Raises:
        ValueError: 当输入文本为空时
    """
    if not text1 or not text2:
        raise ValueError("输入文本不能为空")
    
    # ... implementation
    return similarity_score
```

### TypeScript/React (前端)

- 遵循 ESLint 配置
- 使用 Prettier 格式化
- 组件使用 `.tsx`，工具函数使用 `.ts`
- Props 和 State 必须有类型定义
- 优先使用函数组件 + Hooks

```typescript
interface SearchResult {
  id: string;
  title: string;
  url: string;
  snippet: string;
  score?: number;
}

interface SearchProps {
  query: string;
  onResults: (results: SearchResult[]) => void;
}

// 使用 FC 时显式声明 props 类型
export const SearchComponent: React.FC<SearchProps> = ({ 
  query, 
  onResults 
}) => {
  // ...
};
```

## 代码审查

### PR 要求

- [ ] 代码通过所有 CI 检查
- [ ] 添加/更新相关测试
- [ ] 更新相关文档
- [ ] 关联对应的 Issue

### Review 检查清单

- [ ] 代码逻辑正确
- [ ] 没有安全漏洞
- [ ] 性能影响可接受
- [ ] 代码可读性良好
- [ ] 测试覆盖充分

## 测试要求

### 覆盖率目标

| 模块 | 覆盖率目标 |
|------|------------|
| 核心业务逻辑 | ≥ 80% |
| API 路由 | ≥ 70% |
| 工具函数 | ≥ 90% |

### 测试文件命名

```
tests/
├── unit/           # 单元测试
│   ├── test_text_engine.py
│   └── test_image_engine.py
├── integration/    # 集成测试
│   └── test_api_tasks.py
└── fixtures/       # 测试数据
    └── sample_text.txt
```

## 项目结构

```
ScanIt/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由 (按资源分组)
│   │   │   ├── works.py
│   │   │   ├── tasks.py
│   │   │   └── reports.py
│   │   ├── core/         # 核心配置
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── engines/      # 检测引擎
│   │   │   ├── base.py
│   │   │   ├── text.py
│   │   │   ├── image.py
│   │   │   └── video.py
│   │   ├── models/       # 数据模型
│   │   ├── services/     # 业务服务
│   │   ├── schemas/      # Pydantic schemas
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/          # API 调用封装
│   │   ├── components/   # 通用组件
│   │   ├── pages/        # 页面组件
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── utils/        # 工具函数
│   │   └── types/        # 类型定义
│   └── public/
├── docker/
├── scripts/
└── docs/
```

## 开发环境

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### 启动开发环境

```bash
# 1. 启动依赖服务
docker-compose up -d postgres redis qdrant

# 2. 后端
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 编辑填入配置
alembic upgrade head
uvicorn app.main:app --reload

# 3. 前端
cd frontend
npm install
npm run dev
```

## 问题反馈

- Issue: https://github.com/xxx/scanit/issues
- 讨论: https://github.com/xxx/scanit/discussions
