"""
百度搜索适配器

支持: 文本搜索、图片搜索、视频搜索
API: 百度搜索开放平台 / 网页抓取
"""
import asyncio
from typing import AsyncIterator

import httpx

from app.engines.searchers.base import SearchConfig, SearchResult, SearcherBase


class BaiduSearcher(SearcherBase):
    """百度搜索适配器"""

    name = "baidu"
    supports_content_types = ["text", "image", "video"]

    def __init__(self, api_key: str | None = None, secret_key: str | None = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.secret_key = secret_key

    async def search(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """执行百度搜索"""
        if self.api_key and self.secret_key:
            async for result in self._search_via_api(config):
                yield result
        else:
            async for result in self._search_via_scrape(config):
                yield result

    async def _search_via_api(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过百度搜索开放平台 API 搜索"""
        # 百度搜索 API 需要 OAuth 认证，这里使用简化版本
        # 实际项目中需要实现完整的 OAuth 流程
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {
            "q": config.query,
            "pn": 0,
            "rn": min(config.max_results, 50),
        }

        if config.content_type == "image":
            params["tn"] = "baiduimage"
        elif config.content_type == "video":
            params["tn"] = "baiduimagesearch"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    "https://www.baidu.com/s",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()

                # 解析 HTML 结果
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "lxml")

                for item in soup.select(".c-container")[:config.max_results]:
                    result = self._parse_soup_item(item, config.content_type)
                    if result:
                        yield result
            except httpx.HTTPError:
                pass

    async def _search_via_scrape(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """通过网页抓取搜索"""
        from bs4 import BeautifulSoup

        params = {
            "word": config.query,
            "pn": 0,
            "rn": min(config.max_results, 50),
        }

        if config.content_type == "image":
            params["tn"] = "baiduimage"
        elif config.content_type == "video":
            params["tn"] = "baiduimagesearch"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        search_url = "https://image.baidu.com/search/index" if config.content_type == "image" else \
                     "https://www.baidu.com/s"

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
                    for item in soup.select(".imgitem")[:config.max_results]:
                        result = self._parse_image_item(item)
                        if result:
                            yield result
                else:
                    for item in soup.select(".c-container")[:config.max_results]:
                        result = self._parse_soup_item(item, config.content_type)
                        if result:
                            yield result
            except httpx.HTTPError:
                pass

    def _parse_soup_item(self, item, content_type: str) -> SearchResult | None:
        """解析百度搜索结果"""
        try:
            a = item.select_one("h3 a") or item.select_one("a")
            if not a:
                return None

            url = a.get("href", "")
            if not url or not url.startswith("http"):
                return None

            title = item.select_one("h3")
            snippet_elem = item.select_one(".c-abstract") or item.select_one(".content-right_8Zs40")
            snippet = snippet_elem.text.strip() if snippet_elem else None

            return SearchResult(
                url=url,
                title=title.text.strip() if title else a.text.strip(),
                snippet=snippet,
                domain=url.split("//")[-1].split("/")[0] if url else None,
                content_type=content_type,
            )
        except Exception:
            return None

    def _parse_image_item(self, item) -> SearchResult | None:
        """解析百度图片搜索结果"""
        try:
            img = item.select_one("img")
            a = item.select_one("a")
            if not img:
                return None

            return SearchResult(
                url=img.get("data-imgurl") or img.get("src", ""),
                title=img.get("alt"),
                content_type="image",
                raw_data={"a_href": a.get("href") if a else None},
            )
        except Exception:
            return None
