"""
侵权检测服务

整合搜索引擎和比对器，提供完整的侵权检测功能
"""
import asyncio
import uuid
from dataclasses import dataclass
from typing import AsyncIterator

from app.core.config import settings
from app.engines.searchers import (
    BaiduSearcher,
    BingSearcher,
    GoogleSearcher,
    SearchConfig,
    SearchResult,
    SearcherBase,
)
from app.engines.comparators import (
    CompareResult,
    ComparatorBase,
    ImageComparator,
    TextComparator,
    VideoComparator,
)


@dataclass
class DetectionResult:
    """检测结果"""

    url: str
    title: str | None
    snippet: str | None
    domain: str | None
    content_type: str
    similarity: float
    risk_level: str  # high, medium, low, safe
    search_engine: str
    search_keyword: str
    match_details: dict | None = None
    matched_regions: list[dict] | None = None
    matched_segments: list[dict] | None = None


class DetectionService:
    """
    侵权检测服务

    工作流程:
    1. 根据作品内容生成搜索关键词
    2. 使用多个搜索引擎搜索相似内容
    3. 对搜索结果进行比对
    4. 汇总结果，生成风险评估
    """

    def __init__(self):
        # 初始化搜索引擎
        self.searchers: dict[str, SearcherBase] = {}
        self._init_searchers()

        # 初始化比对器
        self.comparators: dict[str, ComparatorBase] = {
            "text": TextComparator(
                threshold=settings.text_similarity_threshold,
            ),
            "image": ImageComparator(
                threshold=settings.image_similarity_threshold,
                mode="phash",
            ),
            "video": VideoComparator(
                threshold=settings.video_similarity_threshold,
                frame_interval=5,
            ),
        }

    def _init_searchers(self):
        """初始化搜索引擎"""
        # Google
        if settings.google_api_key:
            self.searchers["google"] = GoogleSearcher(
                api_key=settings.google_api_key,
                search_engine_id=settings.google_search_engine_id,
            )
        elif settings.google_search_engine_id:
            self.searchers["google"] = GoogleSearcher(
                search_engine_id=settings.google_search_engine_id,
                use_scrape=True,
            )

        # Bing
        if settings.bing_api_key:
            self.searchers["bing"] = BingSearcher(
                api_key=settings.bing_api_key,
            )
        else:
            self.searchers["bing"] = BingSearcher()

        # Baidu
        if settings.baidu_api_key:
            self.searchers["baidu"] = BaiduSearcher(
                api_key=settings.baidu_api_key,
                secret_key=settings.baidu_api_key,
            )
        else:
            self.searchers["baidu"] = BaiduSearcher()

    def get_searcher(self, name: str) -> SearcherBase | None:
        """获取搜索引擎"""
        return self.searchers.get(name)

    def get_comparator(self, content_type: str) -> ComparatorBase | None:
        """获取比对器"""
        return self.comparators.get(content_type)

    async def detect(
        self,
        content: str | bytes,
        content_type: str,
        keywords: list[str],
        search_engines: list[str] | None = None,
        max_results: int = 50,
    ) -> AsyncIterator[DetectionResult]:
        """
        执行侵权检测

        Args:
            content: 原始内容（文本、URL 或文件路径）
            content_type: 内容类型 (text, image, video)
            keywords: 搜索关键词列表
            search_engines: 使用的搜索引擎（默认使用所有可用）
            max_results: 最大结果数量

        Yields:
            DetectionResult: 检测结果
        """
        if search_engines is None:
            search_engines = list(self.searchers.keys())

        # 获取对应类型的比对器
        comparator = self.get_comparator(content_type)
        if not comparator:
            return

        # 并发搜索和比对
        search_tasks = []
        for engine_name in search_engines:
            searcher = self.get_searcher(engine_name)
            if not searcher:
                continue

            for keyword in keywords:
                config = SearchConfig(
                    query=keyword,
                    max_results=max_results,
                    content_type=content_type,
                )
                search_tasks.append(
                    self._search_and_compare(
                        searcher=searcher,
                        comparator=comparator,
                        config=config,
                        content=content,
                        content_type=content_type,
                    )
                )

        # 并发执行
        for coro in asyncio.as_completed(search_tasks):
            result = await coro
            if result and result.similarity >= comparator.threshold:
                yield result

    async def _search_and_compare(
        self,
        searcher: SearcherBase,
        comparator: ComparatorBase,
        config: SearchConfig,
        content: str | bytes,
        content_type: str,
    ) -> DetectionResult | None:
        """搜索并比对"""
        try:
            async for search_result in searcher.search(config):
                # 比对
                compare_result = await comparator.compare(content, search_result.url)

                if compare_result.similarity >= comparator.threshold:
                    # 判断风险等级
                    risk_level = self._calculate_risk_level(
                        compare_result.similarity,
                        comparator.threshold,
                    )

                    yield DetectionResult(
                        url=search_result.url,
                        title=search_result.title,
                        snippet=search_result.snippet,
                        domain=search_result.domain,
                        content_type=content_type,
                        similarity=compare_result.similarity,
                        risk_level=risk_level,
                        search_engine=searcher.name,
                        search_keyword=config.query,
                        match_details=compare_result.details,
                        matched_regions=compare_result.matched_regions,
                        matched_segments=compare_result.matched_segments,
                    )
        except Exception:
            pass

    def _calculate_risk_level(
        self,
        similarity: float,
        threshold: float,
    ) -> str:
        """计算风险等级"""
        # 高风险: similarity >= threshold * 1.2
        # 中风险: threshold * 1.0 <= similarity < threshold * 1.2
        # 低风险: threshold <= similarity < threshold * 1.0
        high_threshold = threshold * 1.2
        medium_threshold = threshold

        if similarity >= high_threshold:
            return "high"
        elif similarity >= medium_threshold:
            return "medium"
        else:
            return "low"

    def generate_keywords(
        self,
        content: str | bytes,
        content_type: str,
        num_keywords: int = 10,
    ) -> list[str]:
        """
        生成搜索关键词

        Args:
            content: 内容
            content_type: 内容类型
            num_keywords: 关键词数量

        Returns:
            list[str]: 关键词列表
        """
        keywords = []

        if content_type == "text":
            # 从文本中提取关键词
            keywords = self._extract_text_keywords(content, num_keywords)
        elif content_type == "image":
            # 图片使用标题或描述作为关键词
            keywords = [content] if isinstance(content, str) else []
        elif content_type == "video":
            # 视频使用标题作为关键词
            keywords = [content] if isinstance(content, str) else []

        return keywords[:num_keywords]

    def _extract_text_keywords(
        self,
        content: str | bytes,
        num_keywords: int = 10,
    ) -> list[str]:
        """从文本中提取关键词"""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")

        # 简单实现：提取高频词
        import re
        from collections import Counter

        # 分词
        words = re.findall(r"[\w]+", content.lower())
        # 过滤停用词
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "is", "are", "was", "were"}
        words = [w for w in words if w not in stopwords and len(w) > 2]

        # 统计词频
        counter = Counter(words)
        keywords = [word for word, count in counter.most_common(num_keywords)]

        return keywords

    async def quick_check(
        self,
        content: str | bytes,
        content_type: str,
        url: str,
    ) -> CompareResult:
        """
        快速检查某个 URL 是否侵权

        Args:
            content: 原始内容
            content_type: 内容类型
            url: 待检查的 URL

        Returns:
            CompareResult: 比对结果
        """
        comparator = self.get_comparator(content_type)
        if not comparator:
            return CompareResult(similarity=0.0)

        return await comparator.compare(content, url)


# 全局单例
detection_service = DetectionService()
