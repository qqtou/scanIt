"""
搜索引擎适配器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class SearchResult:
    """搜索结果"""

    url: str
    title: str | None = None
    snippet: str | None = None
    domain: str | None = None
    content_type: str = "text"  # text, image, video
    raw_data: dict | None = None

    def __post_init__(self):
        """从 URL 提取 domain"""
        if self.domain is None and self.url:
            try:
                from urllib.parse import urlparse
                self.domain = urlparse(self.url).netloc
            except Exception:
                pass


@dataclass
class SearchConfig:
    """搜索配置"""

    query: str
    max_results: int = 50
    content_type: str = "text"  # text, image, video
    lang: str | None = None  # en, zh, etc.
    country: str | None = None  # us, cn, etc.
    time_range: str | None = None  # d, w, m, y (day, week, month, year)


class SearcherBase(ABC):
    """搜索引擎适配器基类"""

    name: str = "base"
    supports_content_types: list[str] = ["text"]

    def __init__(self, api_key: str | None = None, **kwargs):
        """
        初始化搜索引擎适配器

        Args:
            api_key: API 密钥
            **kwargs: 其他配置参数
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def search(self, config: SearchConfig) -> AsyncIterator[SearchResult]:
        """
        执行搜索

        Args:
            config: 搜索配置

        Yields:
            SearchResult: 搜索结果
        """
        raise NotImplementedError

    async def search_text(self, query: str, max_results: int = 50) -> AsyncIterator[SearchResult]:
        """搜索文本"""
        config = SearchConfig(
            query=query,
            max_results=max_results,
            content_type="text",
        )
        async for result in self.search(config):
            yield result

    async def search_images(self, query: str, max_results: int = 50) -> AsyncIterator[SearchResult]:
        """搜索图片"""
        config = SearchConfig(
            query=query,
            max_results=max_results,
            content_type="image",
        )
        async for result in self.search(config):
            yield result

    async def search_videos(self, query: str, max_results: int = 50) -> AsyncIterator[SearchResult]:
        """搜索视频"""
        config = SearchConfig(
            query=query,
            max_results=max_results,
            content_type="video",
        )
        async for result in self.search(config):
            yield result

    def supports(self, content_type: str) -> bool:
        """检查是否支持该内容类型"""
        return content_type in self.supports_content_types

    @property
    def is_available(self) -> bool:
        """检查是否可用（已配置 API Key）"""
        return self.api_key is not None or self.config.get("use_free_api", False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
