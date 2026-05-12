"""
博查 AI 搜索适配器

支持: 文本搜索、图片搜索、视频搜索
API: 博查 Web Search API (国内部署)
特点: 数据不出海、中文优化、AI 应用优化

使用说明:
1. 申请 API Key: https://open.bochaai.com（微信扫码登录）
2. 配置环境变量: BOCHA_API_KEY=your_key
3. 设置搜索引擎: SEARCH_PROVIDER=bocha

定价: ¥0.002/次（月 3 万次约 ¥60）
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
        """执行博查搜索
        
        Args:
            config: 搜索配置
            
        Yields:
            SearchResult: 搜索结果
            
        Raises:
            ValueError: 未配置 API Key
            RuntimeError: API 调用失败
        """
        if not self.api_key:
            raise ValueError(
                "未配置 BOCHA_API_KEY，请在 .env 中配置：\n"
                "  BOCHA_API_KEY=your_key\n"
                "申请地址: https://open.bochaai.com"
            )

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

        logger.info(f"[Bocha] Search | query={config.query} | count={payload['count']} | freshness={freshness}")

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
                logger.error(f"[Bocha] HTTP Error | status={e.response.status_code} | body={e.response.text[:200]}")
                raise RuntimeError(f"博查搜索失败: HTTP {e.response.status_code}")
            except httpx.HTTPError as e:
                logger.error(f"[Bocha] Network Error | error={e}")
                raise RuntimeError(f"博查搜索失败: {e}")
