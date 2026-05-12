"""
LLM Provider 单元测试

测试 Provider 基类、各 Provider 实现和 ProviderManager

注意: 实际 API 调用需要配置相应的 API Key，
测试会自动跳过不可用的 Provider（SKIP_IF_NOT_AVAILABLE 模式）。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# 测试 Provider 基类
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseProvider:
    """测试 BaseProvider 基类"""

    def test_supports_capability(self):
        from app.engines.llm_provider.base import (
            BaseProvider,
            ProviderConfig,
            Capability,
            ProviderTier,
        )

        config = ProviderConfig(
            name="test",
            tier=ProviderTier.TIER_1_LOCAL,
            capabilities=[Capability.TEXT_GENERATION, Capability.IMAGE_UNDERSTANDING],
        )

        class TestProvider(BaseProvider):
            async def initialize(self) -> bool:
                return True

            async def health_check(self) -> bool:
                return True

            async def generate_text(self, prompt: str, **kwargs) -> str:
                return "test"

            async def understand_image(self, image_url: str | bytes, prompt: str) -> dict:
                return {}

            async def embed_text(self, text: str) -> list[float]:
                return [0.1, 0.2, 0.3]

        provider = TestProvider(config)

        assert provider.supports(Capability.TEXT_GENERATION)
        assert provider.supports(Capability.IMAGE_UNDERSTANDING)
        assert not provider.supports(Capability.EMBEDDING)

    def test_get_cost_estimate(self):
        from app.engines.llm_provider.base import (
            BaseProvider,
            ProviderConfig,
            Capability,
            ProviderTier,
        )

        config = ProviderConfig(
            name="test",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[Capability.TEXT_GENERATION],
            cost_per_1k_tokens=0.001,  # $0.001 / 1K tokens
        )

        class TestProvider(BaseProvider):
            async def initialize(self) -> bool:
                return True

            async def health_check(self) -> bool:
                return True

            async def generate_text(self, prompt: str, **kwargs) -> str:
                return "test"

            async def understand_image(self, image_url: str | bytes, prompt: str) -> dict:
                return {}

            async def embed_text(self, text: str) -> list[float]:
                return [0.1]

        provider = TestProvider(config)

        # 1000 tokens in + 500 tokens out = 1500 total
        cost = provider.get_cost_estimate(1000, 500)
        assert cost == pytest.approx(0.0015, rel=1e-4)

    def test_get_model_info(self):
        from app.engines.llm_provider.base import (
            BaseProvider,
            ProviderConfig,
            Capability,
            ProviderTier,
        )

        config = ProviderConfig(
            name="test-provider",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[Capability.TEXT_GENERATION],
            model="test-model",
        )

        class TestProvider(BaseProvider):
            async def initialize(self) -> bool:
                return True

            async def health_check(self) -> bool:
                return True

            async def generate_text(self, prompt: str, **kwargs) -> str:
                return "test"

            async def understand_image(self, image_url: str | bytes, prompt: str) -> dict:
                return {}

            async def embed_text(self, text: str) -> list[float]:
                return [0.1]

        provider = TestProvider(config)
        info = provider.get_model_info()

        assert info["provider"] == "test-provider"
        assert info["tier"] == "tier2_budget"
        assert info["model"] == "test-model"
        assert info["local"] is False
        assert Capability.TEXT_GENERATION.value in info["capabilities"]


# ─────────────────────────────────────────────────────────────────────────────
# 测试 ProviderTier 和 Capability 枚举
# ─────────────────────────────────────────────────────────────────────────────


class TestEnums:
    def test_provider_tier_values(self):
        from app.engines.llm_provider.base import ProviderTier

        assert ProviderTier.TIER_1_LOCAL.value == "tier1_local"
        assert ProviderTier.TIER_2_BUDGET.value == "tier2_budget"
        assert ProviderTier.TIER_3_ENTERPRISE.value == "tier3_enterprise"

    def test_capability_values(self):
        from app.engines.llm_provider.base import Capability

        assert Capability.TEXT_GENERATION.value == "text_generation"
        assert Capability.IMAGE_UNDERSTANDING.value == "image_understanding"
        assert Capability.EMBEDDING.value == "embedding"

    def test_provider_config_tier_order(self):
        from app.engines.llm_provider.base import ProviderConfig, ProviderTier

        config_local = ProviderConfig(
            name="local", tier=ProviderTier.TIER_1_LOCAL, capabilities=[]
        )
        config_budget = ProviderConfig(
            name="budget", tier=ProviderTier.TIER_2_BUDGET, capabilities=[]
        )
        config_enterprise = ProviderConfig(
            name="enterprise", tier=ProviderTier.TIER_3_ENTERPRISE, capabilities=[]
        )

        assert config_local._tier_order == 1
        assert config_budget._tier_order == 2
        assert config_enterprise._tier_order == 3


# ─────────────────────────────────────────────────────────────────────────────
# 测试 OllamaProvider (本地，需 Ollama 服务运行)
# ─────────────────────────────────────────────────────────────────────────────


class TestOllamaProvider:
    """测试 OllamaProvider"""

    @pytest.fixture
    def provider(self):
        from app.engines.llm_provider.local import OllamaProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="ollama",
            tier=ProviderTier.TIER_1_LOCAL,
            capabilities=[
                Capability.TEXT_GENERATION,
                Capability.IMAGE_UNDERSTANDING,
                Capability.EMBEDDING,
            ],
            local=True,
            cost_per_1k_tokens=0.0,
            base_url="http://localhost:11434",
            model="qwen2.5:7b",
        )
        return OllamaProvider(config)

    @pytest.mark.asyncio
    async def test_initialize_no_server(self):
        """测试 Ollama 服务不可用时初始化失败"""
        from app.engines.llm_provider.local import OllamaProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="ollama",
            tier=ProviderTier.TIER_1_LOCAL,
            capabilities=[Capability.TEXT_GENERATION],
            base_url="http://localhost:19999",  # 不存在的端口
        )
        provider = OllamaProvider(config)
        ok = await provider.initialize()
        assert ok is False

    @pytest.mark.asyncio
    async def test_health_check_no_server(self, provider):
        ok = await provider.health_check()
        # 如果 Ollama 没运行，返回 False
        assert isinstance(ok, bool)

    def test_provider_repr(self, provider):
        r = repr(provider)
        assert "OllamaProvider" in r
        assert "ollama" in r

    def test_parse_json_response_valid(self, provider):
        result = provider._parse_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_response_with_markdown(self, provider):
        content = '```json\n{"key": "value"}\n```'
        result = provider._parse_response(content)
        assert result == {"key": "value"}

    def test_parse_json_response_plain_text(self, provider):
        content = "这是一段普通文本响应"
        result = provider._parse_response(content)
        assert result == {"raw_response": content}

    def test_prepare_image_data_from_bytes(self, provider):
        b64 = provider._prepare_image_data(b"\xff\xd8\xff\xe0")
        assert b64.startswith("data:image/jpeg;base64,")

    def test_prepare_image_data_from_url(self, provider):
        url = "https://example.com/image.jpg"
        result = provider._prepare_image_data(url)
        assert result == url

    @pytest.mark.asyncio
    async def test_embed_batch(self, provider):
        """测试批量向量化"""
        # provider.client is a property that caches httpx.AsyncClient.
        # We need to mock _client directly.
        # Note: httpx response.json() is synchronous (not async)
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Replace the cached client
        provider._client = mock_client

        results = await provider.embed_batch(["text1", "text2"])

        assert len(results) == 2
        assert mock_client.post.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# 测试云端 Provider（使用 mock）
# ─────────────────────────────────────────────────────────────────────────────


class TestDouyinProvider:
    """测试豆包 Provider"""

    @pytest.fixture
    def provider(self):
        from app.engines.llm_provider.cloud import DouyinProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="douyin",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[Capability.TEXT_GENERATION],
            api_key="test-key",
            model="doubao-pro-32k",
            cost_per_1k_tokens=0.00014,
        )
        return DouyinProvider(config)

    def test_initialized_no_key(self):
        from app.engines.llm_provider.cloud import DouyinProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="douyin",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[Capability.TEXT_GENERATION],
        )
        provider = DouyinProvider(config)
        assert provider.config.api_key is None

    @pytest.mark.asyncio
    async def test_generate_text_success(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "测试回复"}}]
            }

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await provider.generate_text("你好")
            assert result == "测试回复"

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "回复"}}]
            }

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await provider.generate_text(
                "问题",
                system_prompt="你是一个助手",
            )

            # 验证调用参数
            call_args = mock_client.post.call_args
            json_body = call_args.kwargs.get("json", call_args[1].get("json", {}))
            messages = json_body["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"


class TestZhipuProvider:
    """测试智谱 Provider"""

    @pytest.fixture
    def provider(self):
        from app.engines.llm_provider.cloud import ZhipuProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="zhipu",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[
                Capability.TEXT_GENERATION,
                Capability.IMAGE_UNDERSTANDING,
            ],
            api_key="test-key",
            model="glm-4",
            cost_per_1k_tokens=0.0014,
        )
        return ZhipuProvider(config)

    @pytest.mark.asyncio
    async def test_understand_image(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": '{"description": "一张图片", "risk": "low"}'
                        }
                    }
                ]
            }

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await provider.understand_image(
                "https://example.com/image.jpg",
                "描述这张图",
            )

            assert result["description"] == "一张图片"
            assert result["risk"] == "low"


class TestKimiProvider:
    """测试 Kimi Provider"""

    @pytest.fixture
    def provider(self):
        from app.engines.llm_provider.cloud import KimiProvider
        from app.engines.llm_provider.base import ProviderConfig, Capability, ProviderTier

        config = ProviderConfig(
            name="kimi",
            tier=ProviderTier.TIER_2_BUDGET,
            capabilities=[Capability.TEXT_GENERATION],
            api_key="test-key",
            model="moonshot-v1-128k",
            cost_per_1k_tokens=0.0014,
            max_tokens=128000,
        )
        return KimiProvider(config)

    @pytest.mark.asyncio
    async def test_generate_text_long_context(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "长文本回复"}}]
            }

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await provider.generate_text("生成长文本")

            assert result == "长文本回复"
            # 验证使用了长上下文模型
            call_args = mock_client.post.call_args
            json_body = call_args.kwargs.get("json", {})
            assert "moonshot" in json_body.get("model", "")


# ─────────────────────────────────────────────────────────────────────────────
# 测试 ProviderManager
# ─────────────────────────────────────────────────────────────────────────────


class TestProviderManager:
    """测试 ProviderManager"""

    @pytest.fixture
    def manager(self):
        # 不触发真实网络请求的 manager
        from app.engines.llm_provider.manager import ProviderManager
        import app.engines.llm_provider.manager as m

        # Patch _auto_detect_and_select 以避免网络调用
        with patch.object(m.ProviderManager, "__post_init__", lambda self: None):
            manager = ProviderManager.__new__(ProviderManager)
            manager._providers = {}
            manager._capability_routes = {}
            manager._total_cost_usd = 0.0
            manager._call_counts = {}
            manager._token_counts = {}
            manager._default_tier = None
            return manager

    def test_register_provider(self, manager):
        from app.engines.llm_provider.base import (
            BaseProvider,
            ProviderConfig,
            Capability,
            ProviderTier,
        )

        class DummyProvider(BaseProvider):
            async def initialize(self) -> bool:
                return True

            async def health_check(self) -> bool:
                return True

            async def generate_text(self, prompt: str, **kwargs) -> str:
                return "ok"

            async def understand_image(self, image_url: str | bytes, prompt: str) -> dict:
                return {}

            async def embed_text(self, text: str) -> list[float]:
                return [0.1]

        config = ProviderConfig(
            name="dummy",
            tier=ProviderTier.TIER_1_LOCAL,
            capabilities=[Capability.TEXT_GENERATION],
        )
        provider = DummyProvider(config)
        manager._register_provider(provider)

        assert "dummy" in manager._providers
        assert manager._providers["dummy"].name == "dummy"

    def test_record_call_cost(self, manager):
        from app.engines.llm_provider.base import ProviderTier

        manager._providers = {
            "test": MagicMock(
                name="test",
                tier=ProviderTier.TIER_1_LOCAL,
            )
        }
        manager._providers["test"].get_cost_estimate = MagicMock(return_value=0.005)

        manager.record_call("test", input_tokens=1000, output_tokens=500)

        assert manager._total_cost_usd == 0.005
        assert manager._call_counts["test"] == 1
        assert manager._token_counts["test"] == 1500

    def test_get_cost_summary(self, manager):
        from app.engines.llm_provider.base import Capability

        manager._providers = {}
        manager._total_cost_usd = 0.025
        manager._call_counts = {"test": 10}
        manager._token_counts = {"test": 5000}
        manager._capability_routes = {
            Capability.TEXT_GENERATION: "test",
        }

        summary = manager.get_cost_summary()

        assert summary["total_cost_usd"] == 0.025
        assert summary["total_cost_cny"] == pytest.approx(0.18, rel=0.01)
        assert summary["call_counts"] == {"test": 10}
        assert summary["active_routes"] == {"text_generation": "test"}

    def test_get_status(self, manager):
        from app.engines.llm_provider.base import Capability, ProviderTier

        class DummyProvider:
            name = "test"
            tier = ProviderTier.TIER_1_LOCAL
            capabilities = [Capability.TEXT_GENERATION]
            config = MagicMock(
                model="test-model",
                cost_per_1k_tokens=0.0,
            )
            _initialized = True
            is_available = lambda self: True

        manager._providers = {"test": DummyProvider()}
        manager._capability_routes = {}

        status = manager.get_status()

        assert "test" in status
        assert status["test"]["tier"] == "tier1_local"
        assert status["test"]["model"] == "test-model"
        assert status["test"]["cost_per_1k"] == 0.0

    def test_set_tier(self, manager):
        from app.engines.llm_provider.base import Capability, ProviderTier

        class DummyProvider:
            name = "dummy"
            tier = ProviderTier.TIER_2_BUDGET
            capabilities = [Capability.TEXT_GENERATION]
            _initialized = True
            is_available = lambda self: True
            config = MagicMock(model="model")

        manager._providers = {"dummy": DummyProvider()}
        manager._capability_routes = {}
        manager._default_tier = None

        # 模拟 _do_select 在指定 tier 下会选择 dummy
        with patch.object(manager, "_do_select"):
            manager.set_tier(ProviderTier.TIER_2_BUDGET)

        assert manager._default_tier == ProviderTier.TIER_2_BUDGET

    def test_list_capabilities(self, manager):
        caps = manager.list_capabilities()
        assert "text_generation" in caps
        assert "image_understanding" in caps
        assert "embedding" in caps

    def test_repr(self, manager):
        from app.engines.llm_provider.base import Capability

        manager._capability_routes = {
            Capability.TEXT_GENERATION: "test",
        }
        r = repr(manager)
        assert "ProviderManager" in r
        assert "text_generation" in r


# ─────────────────────────────────────────────────────────────────────────────
# 测试 LLMDetectionService
# ─────────────────────────────────────────────────────────────────────────────


class TestLLMDetectionService:
    """测试 LLM 增强检测服务"""

    @pytest.fixture
    def service(self):
        from app.engines.detector_llm import LLMDetectionService

        service = LLMDetectionService()
        # 不初始化 manager，避免网络请求
        service._manager = MagicMock()
        service._provider_cache = {}
        return service

    def test_parse_json_list_valid(self, service):
        result = service._parse_json_list('["关键词1", "关键词2"]')
        assert result == ["关键词1", "关键词2"]

    def test_parse_json_list_with_markdown(self, service):
        content = '```json\n["kw1", "kw2", "kw3"]\n```'
        result = service._parse_json_list(content)
        assert result == ["kw1", "kw2", "kw3"]

    def test_parse_json_list_with_extra_text(self, service):
        content = '以下是关键词：["kw1", "kw2"]，仅供参考'
        result = service._parse_json_list(content)
        assert "kw1" in result
        assert "kw2" in result

    def test_parse_json_list_invalid(self, service):
        result = service._parse_json_list("这不是 JSON")
        assert result == []

    def test_generate_fallback_report(self, service):
        from app.engines.detector import DetectionResult

        results = [
            DetectionResult(
                url="https://example.com/1",
                title="侵权图片1",
                snippet=None,
                domain="example.com",
                content_type="image",
                similarity=0.92,
                risk_level="high",
                search_engine="google",
                search_keyword="test",
            ),
            DetectionResult(
                url="https://example.com/2",
                title="侵权图片2",
                snippet=None,
                domain="example.com",
                content_type="image",
                similarity=0.75,
                risk_level="medium",
                search_engine="baidu",
                search_keyword="test",
            ),
        ]

        report = service._generate_fallback_report(results, "image")

        assert "高风险" in report
        assert "中风险" in report
        assert "侵权图片1" in report
        assert "example.com/1" in report

    @pytest.mark.asyncio
    async def test_generate_keywords_llm_no_provider(self, service):
        """没有可用 Provider 时降级到规则提取"""
        service._provider_cache = {}
        service._manager = MagicMock()
        service._manager.get_provider = MagicMock(return_value=None)

        keywords = await service.generate_keywords_llm(
            "这是一段测试文本内容",
            "text",
        )

        # 应该使用规则提取（返回空列表，因为规则提取需要实际文件内容）
        assert isinstance(keywords, list)

    @pytest.mark.asyncio
    async def test_generate_keywords_llm_with_mock_provider(self, service):
        """测试 LLM 关键词生成（mock）"""
        mock_provider = AsyncMock()
        mock_provider.name = "ollama"
        mock_provider.generate_text = AsyncMock(
            return_value='["关键词1", "关键词2", "关键词3"]'
        )
        mock_provider.is_available = MagicMock(return_value=True)

        service._provider_cache = {}
        service._get_provider = MagicMock(return_value=mock_provider)

        keywords = await service.generate_keywords_llm("测试内容", "text")

        assert len(keywords) == 3
        assert "关键词1" in keywords
        mock_provider.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_image_llm_error(self, service):
        """Vision Provider 不可用时返回错误"""
        service._provider_cache = {}
        service._manager = MagicMock()
        service._manager.get_provider = MagicMock(return_value=None)

        result = await service.analyze_image_llm(
            "https://example.com/image.jpg",
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_image_llm_success(self, service):
        """测试 Vision LLM 分析（mock）"""
        mock_provider = AsyncMock()
        mock_provider.name = "qwen-vl"
        mock_provider.understand_image = AsyncMock(
            return_value={
                "description": "测试图片",
                "infringement_likelihood": "medium",
            }
        )
        mock_provider.is_available = MagicMock(return_value=True)

        service._provider_cache = {}
        service._get_provider = MagicMock(return_value=mock_provider)

        result = await service.analyze_image_llm(b"\xff\xd8\xff\xe0")

        assert result["description"] == "测试图片"
        assert result["infringement_likelihood"] == "medium"

    @pytest.mark.asyncio
    async def test_compute_similarity_embedding_no_provider(self, service):
        service._provider_cache = {}
        service._manager = MagicMock()
        service._manager.get_provider = MagicMock(return_value=None)

        sim = await service.compute_similarity_embedding("text1", "text2")

        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_compute_similarity_embedding_success(self, service):
        """测试 Embedding 相似度计算"""
        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(side_effect=[[0.1, 0.2], [0.1, 0.2]])

        service._provider_cache = {}
        service._get_provider = MagicMock(return_value=mock_provider)

        sim = await service.compute_similarity_embedding("text1", "text2")

        # 完全相同的向量，余弦相似度应为 1.0
        assert sim == pytest.approx(1.0, rel=1e-4)

    @pytest.mark.asyncio
    async def test_generate_report_no_provider(self, service):
        """没有 Provider 时生成降级报告"""
        service._provider_cache = {}
        service._manager = MagicMock()
        service._manager.get_provider = MagicMock(return_value=None)

        from app.engines.detector import DetectionResult

        results = [
            DetectionResult(
                url="https://example.com",
                title="Test",
                snippet=None,
                domain="example.com",
                content_type="image",
                similarity=0.95,
                risk_level="high",
                search_engine="google",
                search_keyword="test",
            ),
        ]

        report = await service.generate_report(
            content="测试内容",
            content_type="image",
            results=results,
            keywords=["test"],
        )

        assert "高风险" in report
        assert "example.com" in report

    @pytest.mark.asyncio
    async def test_generate_report_with_mock_provider(self, service):
        """测试报告生成（mock）"""
        mock_provider = AsyncMock()
        mock_provider.name = "douyin"
        mock_provider.generate_text = AsyncMock(
            return_value="这是一份专业的侵权检测报告。"
        )
        mock_provider.is_available = MagicMock(return_value=True)

        service._provider_cache = {}
        service._get_provider = MagicMock(return_value=mock_provider)

        from app.engines.detector import DetectionResult

        results = [
            DetectionResult(
                url="https://example.com",
                title="Test",
                snippet=None,
                domain="example.com",
                content_type="image",
                similarity=0.95,
                risk_level="high",
                search_engine="google",
                search_keyword="test",
            ),
        ]

        report = await service.generate_report(
            content="测试内容",
            content_type="image",
            results=results,
            keywords=["test"],
        )

        assert "侵权检测报告" in report
        mock_provider.generate_text.assert_called_once()

    def test_proxy_properties(self, service):
        """测试透传 DetectionService 属性"""
        assert service.searchers == service._base.searchers
        assert service.comparators == service._base.comparators

    def test_get_searcher(self, service):
        """测试透传 get_searcher"""
        service._base.searchers = {"google": MagicMock()}
        assert service.get_searcher("google") is not None
        assert service.get_searcher("nonexistent") is None
