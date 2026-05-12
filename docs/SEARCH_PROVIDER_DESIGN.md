# 搜索引擎分层架构设计文档

**项目：** ScanIt/扫客
**日期：** 2026-05-12
**状态：** 已确认

---

## 1. 设计目标

### 1.1 业务需求

| 需求 | 场景 | 解决方案 |
|------|------|----------|
| 临时测试/演示 | 开发测试、功能演示、个人学习 | Tier 0（免费 API） |
| 预算有限 | 个人项目、初创团队、月检测 < 10万 | Tier 1（博查 AI ¥0.002/次） |
| 预算充足 | 专业版权机构、大规模检测 | Tier 2（Bright Data 企业级） |

### 1.2 技术需求

- **反爬规避**：禁用网页抓取，强制使用官方 API
- **自动降级**：主 Provider 失败时自动切换备选
- **成本可控**：按量计费，预算超限告警
- **合规安全**：国内数据不出海（博查 AI）

---

## 2. 分层架构

### 2.1 Tier 0: 免费测试层

**适用场景**：开发测试、功能演示、个人学习

| 搜索引擎 | 免费额度 | 单次限制 | 申请地址 |
|----------|----------|----------|----------|
| Google Custom Search | 100次/天 | 10条/次 | https://console.cloud.google.com |
| Bing Web Search | 1000次/月 | 50条/次 | https://portal.azure.com |

**特点**：
- ✅ 官方 API，稳定可靠
- ✅ 无反爬风险
- ❌ 免费额度有限
- ❌ Google 需配置 CX（搜索引擎 ID）

**配置**：
```env
SEARCH_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
GOOGLE_SEARCH_ENGINE_ID=017576...
```

---

### 2.2 Tier 1: 低成本层

**适用场景**：个人项目、初创团队、月检测 < 10万

| 方案 | 月成本 | 次数 | 单次成本 | 特点 |
|------|--------|------|----------|------|
| **博查 AI（推荐）** | ¥60 | 30000 | ¥0.002 | 国内部署、数据不出海 |
| DataForSEO | $60 | 100000 | ¥0.004 | 按量计费 |
| SerpAPI | $50 | 5000 | ¥0.07 | 多引擎聚合 |

**博查 AI 优势**：
- ✅ 国内部署，延迟 < 200ms
- ✅ 数据不出海，符合合规要求
- ✅ 中文搜索优化，准确率高
- ✅ 专为 AI 应用优化（RAG、Agent）
- ✅ 支持多模态搜索（网页/图片/视频）

**配置**：
```env
SEARCH_PROVIDER=bocha
BOCHA_API_KEY=your_bocha_key
```

**申请地址**：https://open.bochaai.com（微信扫码登录）

---

### 2.3 Tier 2: 企业级层

**适用场景**：专业版权机构、大规模检测、高可用要求

| 方案 | 月成本 | 成功率 | 特点 |
|------|--------|--------|------|
| **Bright Data SERP** | $500+ | 99.9% | 全球代理、按成功付费 |
| Oxylabs | $99+ | 99.5% | 高级代理、无头浏览 |
| 自建代理池 | ¥2000+ | - | 完全可控 |

**Bright Data 优势**：
- ✅ 全球 195+ 国家代理
- ✅ 自动绕过反爬、验证码
- ✅ 按成功付费（失败不收费）
- ✅ 支持 Google/Bing/Baidu/Yandex
- ✅ Web Unlocker 技术（自动解锁）

**配置**：
```env
SEARCH_PROVIDER=brightdata
BRIGHTDATA_API_KEY=your_key
BRIGHTDATA_UNLOCKER_ZONE=serp_api
```

**申请地址**：https://brightdata.com

---

## 3. 技术实现

### 3.1 配置层设计

**新增配置项**（`backend/app/core/config.py`）：

```python
class Settings(BaseSettings):
    # 搜索引擎分层配置
    search_provider: str = "google"  # google/bing/bocha/serpapi/brightdata

    # Tier 0: 免费测试
    google_api_key: str = ""
    google_search_engine_id: str = ""
    bing_api_key: str = ""

    # Tier 1: 低成本（博查 AI）
    bocha_api_key: str = ""

    # Tier 2: 企业级
    serpapi_key: str = ""
    brightdata_api_key: str = ""
    brightdata_zone: str = ""

    # 搜索降级策略
    search_fallback_order: List[str] = ["bocha", "google", "bing"]
    search_scrape_enabled: bool = False  # 禁用爬虫模式

    # 搜索限流
    search_rate_limit: int = 10  # 每秒最多 10 次
    search_timeout: int = 30     # 超时 30 秒
```

---

### 3.2 博查 AI Searcher 实现

**文件**：`backend/app/engines/searchers/bocha.py`

```python
"""
博查 AI 搜索适配器

支持: 文本搜索、图片搜索、视频搜索
API: 博查 Web Search API (国内部署)
特点: 数据不出海、中文优化、AI 应用优化
"""
import httpx
from typing import AsyncIterator
from app.engines.searchers.base import SearchConfig, SearchResult, SearcherBase
from app.core.logging import logger


class BochaSearcher(SearcherBase):
    """博查 AI 搜索适配器"""

    name = "bocha"
    supports_content_types = ["text", "image", "video"]

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = "https://api.bochaai.com/v1/web-search"

    async def search(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """执行博查搜索"""
        if not self.api_key:
            raise ValueError("未配置 BOCHA_API_KEY，请在 .env 中配置")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 时间范围映射
        freshness_map = {
            "d": "oneDay",
            "w": "oneWeek",
            "m": "oneMonth",
            "y": "oneYear",
        }
        freshness = freshness_map.get(config.time_range, "noLimit")

        payload = {
            "query": config.query,
            "count": min(config.max_results, 50),
            "freshness": freshness,
            "summary": True  # 启用长文本摘要
        }

        logger.info(f"[Bocha] Search | query={config.query} | count={payload['count']}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                results = data.get("webpage", [])
                logger.info(f"[Bocha] Success | results={len(results)}")

                for item in results[:config.max_results]:
                    yield SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title"),
                        snippet=item.get("summary") or item.get("snippet"),
                        domain=item.get("source"),
                        content_type=config.content_type,
                        raw_data=item
                    )
            except httpx.HTTPStatusError as e:
                logger.error(f"[Bocha] HTTP Error | status={e.response.status_code}")
                raise RuntimeError(f"博查搜索失败: HTTP {e.response.status_code}")
            except httpx.HTTPError as e:
                logger.error(f"[Bocha] Network Error | error={e}")
                raise RuntimeError(f"博查搜索失败: {e}")
```

---

### 3.3 搜索引擎选择器

**文件**：`backend/app/engines/searchers/selector.py`

```python
"""
搜索引擎选择器

根据配置选择搜索引擎，支持自动降级
"""
from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.engines.searchers.base import SearcherBase
from app.engines.searchers.google import GoogleSearcher
from app.engines.searchers.bing import BingSearcher
from app.engines.searchers.baidu import BaiduSearcher
from app.engines.searchers.bocha import BochaSearcher


class SearcherSelector:
    """搜索引擎选择器"""

    @staticmethod
    def get_searcher(provider: Optional[str] = None) -> SearcherBase:
        """获取搜索引擎实例

        Args:
            provider: 指定 Provider，None 时使用配置

        Returns:
            SearcherBase: 搜索引擎实例

        Raises:
            ValueError: 未配置任何可用搜索引擎
        """
        provider = provider or settings.search_provider
        searcher = SearcherSelector._create_searcher(provider)

        if searcher:
            logger.info(f"[Searcher] Selected | provider={provider}")
            return searcher

        # 降级策略
        for fallback in settings.search_fallback_order:
            if fallback != provider:
                searcher = SearcherSelector._create_searcher(fallback)
                if searcher:
                    logger.warning(f"[Searcher] Fallback | from={provider} to={fallback}")
                    return searcher

        raise ValueError(
            "未配置任何搜索引擎 API Key，请配置以下任一项：\n"
            "  - BOCHA_API_KEY（推荐国内使用）\n"
            "  - GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID\n"
            "  - BING_API_KEY"
        )

    @staticmethod
    def _create_searcher(provider: str) -> Optional[SearcherBase]:
        """创建搜索引擎实例"""
        if provider == "bocha" and settings.bocha_api_key:
            return BochaSearcher(api_key=settings.bocha_api_key)

        if provider == "google" and settings.google_api_key and settings.google_search_engine_id:
            return GoogleSearcher(
                api_key=settings.google_api_key,
                search_engine_id=settings.google_search_engine_id
            )

        if provider == "bing" and settings.bing_api_key:
            return BingSearcher(api_key=settings.bing_api_key)

        if provider == "serpapi" and settings.serpapi_key:
            return GoogleSearcher(serpapi_key=settings.serpapi_key, use_serpapi=True)

        if provider == "brightdata" and settings.brightdata_api_key:
            # TODO: 实现 Bright Data Searcher
            logger.warning("Bright Data Searcher 尚未实现")
            return None

        return None


# 便捷函数
def get_searcher() -> SearcherBase:
    return SearcherSelector.get_searcher()
```

---

### 3.4 禁用爬虫模式

**修改文件**：`backend/app/engines/searchers/google.py`、`bing.py`、`baidu.py`

```python
async def _search_via_scrape(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
    """网页抓取（已禁用）

    网页抓取存在反爬风险（IP 封禁、验证码、429），
    生产环境请使用官方 API 或 SERP API 服务。
    """
    if not settings.search_scrape_enabled:
        logger.error(
            "[Searcher] Scraping disabled | "
            "请配置官方 API Key 或设置 SEARCH_SCRAPE_ENABLED=true（不推荐）"
        )
        raise ValueError(
            "网页抓取模式已禁用，请配置以下任一 API Key：\n"
            "  - BOCHA_API_KEY（推荐）\n"
            "  - GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID\n"
            "  - BING_API_KEY\n"
            "或设置 SEARCH_SCRAPE_ENABLED=true 启用爬虫模式（不推荐）"
        )

    # 爬虫代码（仅在明确启用时执行）
    # ...
```

---

## 4. 使用说明

### 4.1 Tier 0: 免费测试配置

**Step 1: 申请 Google Custom Search API**

1. 访问 https://console.cloud.google.com
2. 创建项目（或选择现有项目）
3. 启用 "Custom Search JSON API"
   - 导航：API 和服务 → 库 → 搜索 "Custom Search" → 启用
4. 创建 API 凭据
   - 导航：API 和服务 → 凭据 → 创建凭据 → API 密钥
5. 复制 API Key

**Step 2: 创建自定义搜索引擎**

1. 访问 https://cse.google.com/all
2. 点击 "添加"
3. 配置搜索引擎：
   - 名称：ScanIt Search
   - 搜索范围：搜索整个网络
   - 语言：简体中文
4. 创建后获取搜索引擎 ID（CX）
   - 格式：`017576662512468239146:omuauf_lfve`

**Step 3: 配置环境变量**

```env
# backend/.env
SEARCH_PROVIDER=google
GOOGLE_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_ENGINE_ID=017576662512468239146:omuauf_lfve
```

**Step 4: 验证**

```bash
cd backend
python -c "
from app.engines.searchers import get_searcher
import asyncio

async def test():
    searcher = get_searcher()
    results = []
    async for r in searcher.search('test'):
        results.append(r)
    print(f'找到 {len(results)} 条结果')

asyncio.run(test())
"
```

---

### 4.2 Tier 1: 博查 AI 配置（推荐国内）

**Step 1: 申请博查 API Key**

1. 访问 https://open.bochaai.com
2. 微信扫码登录
3. 点击右上角 "API KEY 管理"
4. 点击 "创建 API Key"
5. 复制 API Key（格式：`bocha_xxxxxxxxxxxxx`）

**Step 2: 配置环境变量**

```env
# backend/.env
SEARCH_PROVIDER=bocha
BOCHA_API_KEY=bocha_xxxxxxxxxxxxx
```

**Step 3: 验证**

```bash
curl -X POST "https://api.bochaai.com/v1/web-search" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "count": 5}'
```

---

### 4.3 Tier 2: Bright Data 配置

**Step 1: 申请 Bright Data**

1. 访问 https://brightdata.com
2. 注册账户
3. 创建 SERP API Zone
   - 导航：My Proxies → Add → SERP API
   - 配置目标搜索引擎（Google/Bing/Baidu）
4. 获取 API Key 和 Zone 名称

**Step 2: 配置环境变量**

```env
# backend/.env
SEARCH_PROVIDER=brightdata
BRIGHTDATA_API_KEY=your_api_key
BRIGHTDATA_UNLOCKER_ZONE=serp_api
```

---

## 5. 成本对比

| 月检测量 | Tier 0 | Tier 1 (博查) | Tier 2 (Bright Data) |
|----------|--------|---------------|----------------------|
| 100 | ¥0 | ¥0.2 | - |
| 1,000 | ¥0 | ¥2 | - |
| 3,000 | 超限 | ¥6 | - |
| 10,000 | 超限 | ¥20 | - |
| 30,000 | 超限 | ¥60 | $500 |
| 100,000 | 超限 | ¥200 | $1,500 |
| 500,000 | 超限 | ¥1,000 | $5,000 |

---

## 6. 注意事项

### 6.1 安全

- ✅ 禁用爬虫模式（默认）
- ✅ API Key 通过环境变量配置，禁止硬编码
- ✅ 博查 AI 数据不出海，符合合规要求

### 6.2 性能

- ✅ 博查 AI 延迟 < 200ms（国内部署）
- ✅ 自动降级策略，提高可用性
- ✅ 请求限流（默认 10 req/s）

### 6.3 成本

- ✅ 按量计费，无固定成本
- ✅ Tier 0 免费额度足够测试
- ✅ Tier 1 博查 ¥0.002/次，月 3 万次仅 ¥60

---

**确认人：** 左左
**确认时间：** 2026-05-12 09:50
