"""
Google 搜索适配器

支持: 文本搜索、图片搜索、视频搜索
API: Google Custom Search API / SerpAPI
"""
import asyncio
from typing import AsyncIterator

import httpx

from app.engines.searchers.base import SearchConfig, SearchResult, SearcherBase


class GoogleSearcher(SearcherBase):
    """Google 搜索适配器"""

    name = "google"
    supports_content_types = ["text", "image", "video"]

    def __init__(self, api_key: str | None = None, search_engine_id: str | None = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.search_engine_id = search_engine_id or kwargs.get("cx")
        self.use_serpapi = kwargs.get("use_serpapi", False)
        self.serpapi_key = kwargs.get("serpapi_key")
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """执行 Google 搜索"""
        if self.use_serpapi:
            async for result in self._search_via_serpapi(config):
                yield result
        else:
            async for result in self._search_via_google_api(config):
                yield result

    async def _search_via_google_api(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过 Google Custom Search API 搜索"""
        if not self.api_key or not self.search_engine_id:
            # 如果没有 API Key，尝试网页抓取
            async for result in self._search_via_scrape(config):
                yield result
            return

        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": config.query,
            "num": min(config.max_results, 10),  # Google API 每次最多 10 个
        }

        # 设置内容类型
        if config.content_type == "image":
            params["searchType"] = "image"
        elif config.content_type == "video":
            params["searchType"] = "video"

        # 设置语言和地区
        if config.lang:
            params["lr"] = f"lang_{config.lang}"
        if config.country:
            params["cr"] = f"country{config.country.upper()}"

        # 时间范围
        if config.time_range:
            date_range_map = {"d": "d", "w": "w", "m": "m", "y": "y"}
            params["dateRestrict"] = date_range_map.get(config.time_range, "m")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = 0
            while start < config.max_results:
                params["start"] = start + 1
                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    items = data.get("items", [])
                    if not items:
                        break

                    for item in items:
                        result = self._parse_item(item, config.content_type)
                        yield result

                    start += len(items)
                    if len(items) < 10:
                        break

                    # 避免超出配额
                    await asyncio.sleep(0.5)
                except httpx.HTTPError as e:
                    break

    async def _search_via_serpapi(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过 SerpAPI 搜索"""
        if not self.serpapi_key:
            async for result in self._search_via_scrape(config):
                yield result
            return

        params = {
            "api_key": self.serpapi_key,
            "q": config.query,
            "engine": "google",
            "num": min(config.max_results, 100),
        }

        if config.content_type == "image":
            params["tbm"] = "isch"
        elif config.content_type == "video":
            params["tbm"] = "vid"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    "https://serpapi.com/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results_key = "images_results" if config.content_type == "image" else \
                              "video_results" if config.content_type == "video" else \
                              "organic_results"

                for item in data.get(results_key, [])[:config.max_results]:
                    yield self._parse_serpapi_item(item, config.content_type)
            except httpx.HTTPError:
                pass

    async def _search_via_scrape(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过网页抓取搜索（已禁用）

        网页抓取存在反爬风险（IP 封禁、验证码、429），
        生产环境请使用官方 API 或 SERP API 服务。
        """
        from app.core.config import settings
        from app.core.logging import logger

        if not settings.search_scrape_enabled:
            logger.error(
                "[Google] Scraping disabled | "
                "请配置官方 API Key 或设置 SEARCH_SCRAPE_ENABLED=true（不推荐）"
            )
            raise ValueError(
                "网页抓取模式已禁用，请配置以下任一 API Key：\n"
                "  - BOCHA_API_KEY（推荐国内使用）\n"
                "  - GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID\n"
                "  - BING_API_KEY\n"
                "或设置 SEARCH_SCRAPE_ENABLED=true 启用爬虫模式（不推荐）"
            )

        # 爬虫代码（仅在明确启用时执行）
        from bs4 import BeautifulSoup

        params = {
            "q": config.query,
            "hl": config.lang or "en",
        }

        if config.content_type == "image":
            params["tbm"] = "isch"
        elif config.content_type == "video":
            params["tbm"] = "vid"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        logger.warning("[Google] Scraping enabled (not recommended) | query=%s", config.query)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    "https://www.google.com/search",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                for item in soup.select(".g")[:config.max_results]:
                    result = self._parse_soup_item(item, config.content_type)
                    if result:
                        yield result
            except httpx.HTTPError:
                pass

    def _parse_item(self, item: dict, content_type: str) -> SearchResult:
        """解析 Google API 返回的结果"""
        return SearchResult(
            url=item.get("link", ""),
            title=item.get("title"),
            snippet=item.get("snippet"),
            domain=item.get("displayLink"),
            content_type=content_type,
            raw_data=item,
        )

    def _parse_serpapi_item(self, item: dict, content_type: str) -> SearchResult:
        """解析 SerpAPI 返回的结果"""
        if content_type == "image":
            return SearchResult(
                url=item.get("original") or item.get("link", ""),
                title=item.get("title"),
                snippet=None,
                domain=item.get("source"),
                content_type="image",
                raw_data=item,
            )
        elif content_type == "video":
            return SearchResult(
                url=item.get("link", ""),
                title=item.get("title"),
                snippet=item.get("snippet"),
                domain=item.get("source", "").split("//")[-1].split("/")[0] if item.get("source") else None,
                content_type="video",
                raw_data=item,
            )
        else:
            return SearchResult(
                url=item.get("link", ""),
                title=item.get("title"),
                snippet=item.get("snippet"),
                domain=item.get("source"),
                content_type="text",
                raw_data=item,
            )

    def _parse_soup_item(self, item, content_type: str) -> SearchResult | None:
        """解析 BeautifulSoup 解析的结果"""
        try:
            link_elem = item.select_one("a")
            if not link_elem:
                return None

            url = link_elem.get("href", "")
            if not url.startswith("http"):
                return None

            title = item.select_one("h3")
            snippet = item.select_one(".IsZvec")

            return SearchResult(
                url=url,
                title=title.text if title else None,
                snippet=snippet.text if snippet else None,
                content_type=content_type,
            )
        except Exception:
            return None
