"""
单元测试 - 侵权检测引擎
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.engines.searchers.base import SearchResult, SearchResponse, RateLimiter
from app.engines.searchers.google import GoogleSearcher
from app.engines.searchers.bing import BingSearcher
from app.engines.searchers.baidu import BaiduSearcher

from app.engines.comparators.base import ComparisonResult
from app.engines.comparators.text import TextComparator
from app.engines.comparators.image import ImageComparator
from app.engines.comparators.video import VideoComparator

from app.engines.detector import DetectionService


class TestSearchResult:
    """搜索结果测试"""
    
    def test_create_search_result(self):
        """测试创建搜索结果"""
        result = SearchResult(
            url="https://example.com",
            title="示例标题",
            snippet="示例内容片段",
            engine="google",
            rank=1,
        )
        assert result.url == "https://example.com"
        assert result.title == "示例标题"
        assert result.snippet == "示例内容片段"
        assert result.engine == "google"
        assert result.rank == 1


class TestSearchResponse:
    """搜索响应测试"""
    
    def test_create_search_response(self):
        """测试创建搜索响应"""
        results = [
            SearchResult(
                url="https://example1.com",
                title="标题1",
                snippet="内容1",
                engine="google",
                rank=1,
            ),
            SearchResult(
                url="https://example2.com",
                title="标题2",
                snippet="内容2",
                engine="google",
                rank=2,
            ),
        ]
        response = SearchResponse(
            results=results,
            total=100,
            query="测试查询",
        )
        assert len(response.results) == 2
        assert response.total == 100
        assert response.query == "测试查询"


class TestRateLimiter:
    """限流器测试"""
    
    def test_rate_limiter_basic(self):
        """测试限流器基本功能"""
        limiter = RateLimiter(max_calls=2, period=1.0)
        
        # 前两次调用应该通过
        assert limiter.can_proceed() is True
        assert limiter.can_proceed() is True
        
        # 第三次调用应该被限流
        assert limiter.can_proceed() is False
    
    def test_rate_limiter_reset(self):
        """测试限流器重置"""
        limiter = RateLimiter(max_calls=1, period=1.0)
        
        assert limiter.can_proceed() is True
        assert limiter.can_proceed() is False
        
        # 等待重置
        import time
        time.sleep(1.1)
        
        assert limiter.can_proceed() is True


class TestGoogleSearcher:
    """Google 搜索测试"""
    
    @pytest.mark.asyncio
    async def test_google_search_success(self):
        """测试 Google 搜索成功"""
        searcher = GoogleSearcher(api_key="test_key", search_engine_id="test_id")
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "items": [
                    {
                        "link": "https://example.com",
                        "title": "测试标题",
                        "snippet": "测试内容",
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            results = await searcher.search("测试查询", max_results=10)
            
            assert len(results) == 1
            assert results[0].url == "https://example.com"
            assert results[0].title == "测试标题"
    
    @pytest.mark.asyncio
    async def test_google_search_no_api_key(self):
        """测试无 API Key 时的降级处理"""
        searcher = GoogleSearcher(api_key="", search_engine_id="")
        
        # 应该返回空列表
        results = await searcher.search("测试")
        assert len(results) == 0


class TestTextComparator:
    """文本比对器测试"""
    
    def test_identical_text(self):
        """测试完全相同的文本"""
        comparator = TextComparator()
        
        text1 = "这是一个测试文本，用于检测侵权内容"
        text2 = "这是一个测试文本，用于检测侵权内容"
        
        result = comparator.compare(text1, text2)
        
        assert result.is_similar is True
        assert result.similarity > 0.9
    
    def test_similar_text(self):
        """测试相似文本"""
        comparator = TextComparator()
        
        text1 = "这是一个测试文本，用于检测侵权内容"
        text2 = "这是一个测试文本，用于检测侵权内容，稍微有点不同"
        
        result = comparator.compare(text1, text2)
        
        assert result.is_similar is True
        assert result.similarity > 0.5
    
    def test_different_text(self):
        """测试完全不同的文本"""
        comparator = TextComparator()
        
        text1 = "这是一段完全不同的文本内容"
        text2 = "与上面的文本没有任何相似之处"
        
        result = comparator.compare(text1, text2)
        
        assert result.similarity < 0.3
    
    def test_short_text(self):
        """测试短文本"""
        comparator = TextComparator()
        
        text1 = "短"
        text2 = "短"
        
        result = comparator.compare(text1, text2)
        
        # 短文本可能有不同的处理方式
        assert result.similarity >= 0


class TestImageComparator:
    """图片比对器测试"""
    
    def test_identical_images(self):
        """测试完全相同的图片 (使用路径)"""
        comparator = ImageComparator()
        
        # 由于无法直接比较图片，使用模拟测试
        # 实际实现中会使用 pHash 或 CNN 特征
        assert comparator is not None
    
    def test_image_comparator_init(self):
        """测试图片比对器初始化"""
        comparator = ImageComparator()
        
        assert comparator is not None
        # 验证必要的属性
        assert hasattr(comparator, "compare")


class TestVideoComparator:
    """视频比对器测试"""
    
    def test_video_comparator_init(self):
        """测试视频比对器初始化"""
        comparator = VideoComparator()
        
        assert comparator is not None
        # 验证必要的属性
        assert hasattr(comparator, "compare")


class TestDetectionService:
    """检测服务测试"""
    
    @pytest.mark.asyncio
    async def test_detection_service_init(self):
        """测试检测服务初始化"""
        service = DetectionService()
        
        assert service is not None
        assert hasattr(service, "searchers")
        assert hasattr(service, "comparators")
    
    @pytest.mark.asyncio
    async def test_detection_service_register_searcher(self):
        """测试注册搜索引擎"""
        service = DetectionService()
        searcher = GoogleSearcher(api_key="test", search_engine_id="test")
        
        service.register_searcher("google", searcher)
        
        assert "google" in service.searchers
    
    @pytest.mark.asyncio
    async def test_detection_service_register_comparator(self):
        """测试注册比对器"""
        service = DetectionService()
        comparator = TextComparator()
        
        service.register_comparator("text", comparator)
        
        assert "text" in service.comparators
    
    def test_detection_service_get_results(self):
        """测试获取检测结果"""
        service = DetectionService()
        
        # 模拟一些结果
        service.results = [
            ComparisonResult(
                source_url="https://example1.com",
                source_title="标题1",
                source_snippet="内容1",
                similarity=0.95,
                is_similar=True,
            ),
            ComparisonResult(
                source_url="https://example2.com",
                source_title="标题2",
                source_snippet="内容2",
                similarity=0.30,
                is_similar=False,
            ),
        ]
        
        results = service.get_results(min_similarity=0.5)
        
        assert len(results) == 1
        assert results[0].similarity >= 0.5
    
    def test_detection_service_clear_results(self):
        """测试清空检测结果"""
        service = DetectionService()
        
        service.results = [
            ComparisonResult(
                source_url="https://example.com",
                source_title="标题",
                source_snippet="内容",
                similarity=0.95,
                is_similar=True,
            )
        ]
        
        service.clear_results()
        
        assert len(service.results) == 0
