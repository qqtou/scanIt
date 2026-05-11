"""
搜索引擎适配器

导出所有搜索引擎适配器
"""
from app.engines.searchers.base import SearchConfig, SearchResult, SearcherBase
from app.engines.searchers.google import GoogleSearcher
from app.engines.searchers.bing import BingSearcher
from app.engines.searchers.baidu import BaiduSearcher

__all__ = [
    "SearcherBase",
    "SearchConfig",
    "SearchResult",
    "GoogleSearcher",
    "BingSearcher",
    "BaiduSearcher",
]
