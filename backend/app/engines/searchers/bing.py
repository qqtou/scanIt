"""
Bing 搜索适配器

支持: 文本搜索、图片搜索、视频搜索
API: Bing Web Search API v7
"""
import asyncio
from typing import AsyncIterator

import httpx

from app.engines.searchers.base import SearchConfig, SearchResult, SearcherBase


class BingSearcher(SearcherBase):
    """Bing 搜索适配器"""

    name = "bing"
    supports_content_types = ["text", "image", "video"]

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.endpoint = kwargs.get("endpoint", "https://api.bing.microsoft.com/v7.0/search")

    async def search(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """执行 Bing 搜索"""
        if not self.api_key:
            async for result in self._search_via_scrape(config):
                yield result
            return

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": config.query,
            "count": min(config.max_results, 50),
            "offset": 0,
        }

        # 设置内容类型
        if config.content_type == "image":
            params["responseFilter"] = "Images"
        elif config.content_type == "video":
            params["responseFilter"] = "Videos"
        else:
            params["responseFilter"] = "WebPages"

        # 语言
        if config.lang:
            params["setLang"] = config.lang

        # 市场
        if config.country:
            market_map = {"us": "en-US", "cn": "zh-CN", "uk": "en-GB"}
            params["mkt"] = market_map.get(config.country, "en-US")

        async with httpx.AsyncClient(timeout=30.0) as client:
            while params["offset"] < config.max_results:
                try:
                    response = await client.get(
                        self.endpoint,
                        headers=headers,
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if config.content_type == "image":
                        items = data.get("images", {}).get("value", [])
                    elif config.content_type == "video":
                        items = data.get("videos", {}).get("value", [])
                    else:
                        items = data.get("webPages", {}).get("value", [])

                    if not items:
                        break

                    for item in items:
                        result = self._parse_item(item, config.content_type)
                        yield result

                    params["offset"] += len(items)
                    if len(items) < params["count"]:
                        break

                    await asyncio.sleep(0.5)
                except httpx.HTTPError:
                    break

    async def _search_via_scrape(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过网页抓取搜索（备用方案）"""
        from bs4 import BeautifulSoup

        params = {
            "q": config.query,
            "setlang": config.lang or "en",
        }

        if config.content_type == "image":
            params["q"] = f"{config.query} images"
        elif config.content_type == "video":
            params["q"] = f"{config.query} videos"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        search_url = "https://www.bing.com/images/search" if config.content_type == "image" else \
                     "https://www.bing.com/videos/search" if config.content_type == "video" else \
                     "https://www.bing.com/search"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    search_url,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                if config.content_type == "image":
                    for item in soup.select(".img_item")[:config.max_results]:
                        result = self._parse_image_soup(item)
                        if result:
                            yield result
                elif config.content_type == "video":
                    for item in soup.select(".dv-title")[:config.max_results]:
                        result = self._parse_video_soup(item)
                        if result:
                            yield result
                else:
                    for item in soup.select(".b_algo")[:config.max_results]:
                        result = self._parse_text_soup(item)
                        if result:
                            yield result
            except httpx.HTTPError:
                pass

    def _parse_item(self, item: dict, content_type: str) -> SearchResult:
        """解析 Bing API 返回的结果"""
        if content_type == "image":
            return SearchResult(
                url=item.get("contentUrl", ""),
                title=item.get("name"),
                snippet=item.get("name"),
                domain=item.get("hostPageDisplayUrl", "").split("//")[-1].split("/")[0] if item.get("hostPageDisplayUrl") else None,
                content_type="image",
                raw_data=item,
            )
        elif content_type == "video":
            return SearchResult(
                url=item.get("contentUrl", ""),
                title=item.get("name"),
                snippet=item.get("description"),
                domain=item.get("publisher", [{}])[0].get("name") if item.get("publisher") else None,
                content_type="video",
                raw_data=item,
            )
        else:
            return SearchResult(
                url=item.get("url", ""),
                title=item.get("name"),
                snippet=item.get("snippet"),
                domain=item.get("displayHost", ""),
                content_type="text",
                raw_data=item,
            )

    def _parse_image_soup(self, item) -> SearchResult | None:
        """解析图片搜索结果"""
        try:
            img = item.select_one("img")
            a = item.select_one("a")
            if not img or not a:
                return None

            return SearchResult(
                url=a.get("href", ""),
                title=img.get("alt"),
                content_type="image",
            )
        except Exception:
            return None

    def _parse_video_soup(self, item) -> SearchResult | None:
        """解析视频搜索结果"""
        try:
            a = item.select_one("a")
            if not a:
                return None

            return SearchResult(
                url=a.get("href", ""),
                title=a.text.strip(),
                content_type="video",
            )
        except Exception:
            return None

    def _parse_text_soup(self, item) -> SearchResult | None:
        """解析文本搜索结果"""
        try:
            a = item.select_one("h2 a")
            snippet = item.select_one(".b_paractl")
            if not a:
                return None

            return SearchResult(
                url=a.get("href", ""),
                title=a.text.strip(),
                snippet=snippet.text.strip() if snippet else None,
                content_type="text",
            )
        except Exception:
            return None
