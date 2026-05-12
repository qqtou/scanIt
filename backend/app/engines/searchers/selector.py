"""
搜索引擎选择器

根据配置选择搜索引擎，支持自动降级

使用说明:
1. 配置 SEARCH_PROVIDER 环境变量（google/bing/bocha/serpapi/brightdata）
2. 配置对应的 API Key
3. 系统自动选择并降级

示例:
    SEARCH_PROVIDER=bocha
    BOCHA_API_KEY=your_key
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
        logger.warning(f"[Searcher] Primary failed | provider={provider}")
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
            "  - BING_API_KEY\n"
            "详见: docs/SEARCH_PROVIDER_DESIGN.md"
        )

    @staticmethod
    def _create_searcher(provider: str) -> Optional[SearcherBase]:
        """创建搜索引擎实例
        
        Args:
            provider: 搜索引擎名称
            
        Returns:
            SearcherBase 或 None
        """
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
            # SerpAPI 通过 GoogleSearcher 的 serpapi_key 参数使用
            return GoogleSearcher(serpapi_key=settings.serpapi_key)

        if provider == "brightdata" and settings.brightdata_api_key:
            # TODO: 实现 Bright Data Searcher
            logger.warning("Bright Data Searcher 尚未实现，请使用 bocha 或 serpapi")
            return None

        return None

    @staticmethod
    def list_available() -> list[str]:
        """列出所有可用的搜索引擎
        
        Returns:
            list[str]: 可用的搜索引擎名称列表
        """
        available = []
        
        if settings.bocha_api_key:
            available.append("bocha")
        if settings.google_api_key and settings.google_search_engine_id:
            available.append("google")
        if settings.bing_api_key:
            available.append("bing")
        if settings.serpapi_key:
            available.append("serpapi")
        if settings.brightdata_api_key:
            available.append("brightdata")
            
        return available


# 便捷函数
def get_searcher() -> SearcherBase:
    """获取搜索引擎实例（使用配置的 Provider）"""
    return SearcherSelector.get_searcher()


def list_available_searchers() -> list[str]:
    """列出所有可用的搜索引擎"""
    return SearcherSelector.list_available()
