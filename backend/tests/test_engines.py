"""
单元测试 - 搜索引擎和比对器
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.engines.searchers.base import SearchResult, SearchConfig, SearcherBase
from app.engines.searchers.google import GoogleSearcher
from app.engines.searchers.bing import BingSearcher
from app.engines.searchers.baidu import BaiduSearcher
from app.engines.comparators.text import TextComparator
from app.engines.comparators.image import ImageComparator


class TestSearchResult:
    """搜索结果测试"""
    
    def test_create_search_result(self):
        """测试创建搜索结果"""
        result = SearchResult(
            url="https://example.com/article",
            title="Example Article",
            snippet="This is an example article",
            domain="example.com",
            content_type="text",
        )
        
        assert result.url == "https://example.com/article"
        assert result.title == "Example Article"
        assert result.snippet == "This is an example article"
        assert result.domain == "example.com"
        assert result.content_type == "text"
    
    def test_domain_extraction(self):
        """测试域名自动提取"""
        result = SearchResult(url="https://example.com/path/to/page")
        assert result.domain == "example.com"


class TestSearchConfig:
    """搜索配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SearchConfig(query="test query")
        
        assert config.query == "test query"
        assert config.max_results == 50
        assert config.content_type == "text"
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SearchConfig(
            query="test",
            max_results=100,
            content_type="image",
            lang="zh",
            country="cn",
        )
        
        assert config.max_results == 100
        assert config.content_type == "image"
        assert config.lang == "zh"
        assert config.country == "cn"


class TestSearcherBase:
    """搜索引擎基类测试"""
    
    def test_supports_content_type(self):
        """测试内容类型支持检查"""
        searcher = GoogleSearcher()
        
        assert searcher.supports("text") is True
        assert searcher.supports("image") is True
        assert searcher.supports("video") is True
    
    def test_is_available(self):
        """测试搜索引擎可用性"""
        searcher_no_key = GoogleSearcher()
        assert searcher_no_key.is_available is False
        
        searcher_with_key = GoogleSearcher(api_key="test_key")
        assert searcher_with_key.is_available is True


class TestGoogleSearcher:
    """Google 搜索器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        searcher = GoogleSearcher(api_key="test_key", cx="test_cx")
        
        assert searcher.name == "google"
        assert searcher.api_key == "test_key"
    
    def test_supports(self):
        """测试支持的类型"""
        searcher = GoogleSearcher()
        
        assert "text" in searcher.supports_content_types
        assert "image" in searcher.supports_content_types


class TestBingSearcher:
    """Bing 搜索器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        searcher = BingSearcher(api_key="test_key")
        
        assert searcher.name == "bing"
        assert searcher.api_key == "test_key"


class TestBaiduSearcher:
    """百度搜索器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        searcher = BaiduSearcher()
        
        assert searcher.name == "baidu"


class TestTextComparator:
    """文本比对器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        comparator = TextComparator()
        
        assert comparator.name == "text_simhash_lsh"
        assert comparator.threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_compare_identical_text(self):
        """测试完全相同文本"""
        comparator = TextComparator()
        
        text1 = "这是一段测试文本内容"
        text2 = "这是一段测试文本内容"
        
        result = await comparator.compare(text1, text2)
        
        assert result.similarity >= 0.95
    
    @pytest.mark.asyncio
    async def test_compare_different_text(self):
        """测试完全不同文本"""
        comparator = TextComparator()
        
        text1 = "这是一段测试文本"
        text2 = "完全不同的另一段文本"
        
        result = await comparator.compare(text1, text2)
        
        assert result.similarity < 0.85


class TestImageComparator:
    """图片比对器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        comparator = ImageComparator()
        
        assert comparator.name == "image_phash_cnn"
        assert comparator.threshold == 0.85
        assert comparator.mode == "phash"
