"""
AI Provider 抽象层基类

定义 Provider 接口规范，所有 Provider 实现需继承 BaseProvider
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderTier(Enum):
    """Provider 层级"""

    TIER_1_LOCAL = "tier1_local"  # 本地免费 (Ollama)
    TIER_2_BUDGET = "tier2_budget"  # 低成本云 (豆包/智谱/Kimi)
    TIER_3_ENTERPRISE = "tier3_enterprise"  # 企业级 (阿里/GPT/Claude)


class Capability(Enum):
    """模型能力类型"""

    TEXT_GENERATION = "text_generation"  # 文本生成
    IMAGE_UNDERSTANDING = "image_understanding"  # 图片理解 (Vision)
    EMBEDDING = "embedding"  # 向量嵌入
    IMAGE_GENERATION = "image_generation"  # 图片生成 (暂不支持)


@dataclass
class ProviderConfig:
    """Provider 配置"""

    name: str  # Provider 标识名
    tier: ProviderTier  # 所属层级
    capabilities: list[Capability]  # 支持的能力列表
    api_key: str | None = None  # API Key
    base_url: str | None = None  # 自定义 API 地址
    model: str = ""  # 默认模型
    local: bool = False  # 是否本地部署
    cost_per_1k_tokens: float = 0.0  # 单千token成本 (USD)
    max_tokens: int = 4096  # 最大输出token数
    supports_streaming: bool = False  # 是否支持流式输出
    timeout: int = 60  # 超时秒数
    # 层级排序值（数字越小优先级越高）
    _tier_order: int = field(default=999, repr=False)

    def __post_init__(self):
        # 设置层级排序值，用于 Tier 选择
        self._tier_order = {
            ProviderTier.TIER_1_LOCAL: 1,
            ProviderTier.TIER_2_BUDGET: 2,
            ProviderTier.TIER_3_ENTERPRISE: 3,
        }.get(self.tier, 99)


class BaseProvider(ABC):
    """
    Provider 抽象基类

    所有 Provider (本地/云端) 必须实现此接口
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.tier = config.tier
        self.capabilities = config.capabilities
        self._initialized = False

    # ──────────────────────────────────────────────────────────
    # 基础检查
    # ──────────────────────────────────────────────────────────

    def supports(self, capability: Capability) -> bool:
        """检查是否支持指定能力"""
        return capability in self.capabilities

    def get_cost_estimate(self, input_tokens: int, output_tokens: int = 0) -> float:
        """估算单次调用成本 (USD)"""
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * self.config.cost_per_1k_tokens

    def is_available(self) -> bool:
        """Provider 是否可用（子类可覆盖）"""
        return self._initialized

    # ──────────────────────────────────────────────────────────
    # 抽象方法 (子类必须实现)
    # ──────────────────────────────────────────────────────────

    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化 Provider

        本地 Provider: 检测服务是否运行
        云端 Provider: 验证 API Key 是否有效

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: Provider 是否健康
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """
        文本生成

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 随机性 (0.0-2.0)
            max_tokens: 最大输出 token 数
            **kwargs: 其他参数

        Returns:
            str: 生成的文本
        """
        pass

    @abstractmethod
    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """
        图片理解

        Args:
            image_url: 图片 URL 或字节数据
            prompt: 提问

        Returns:
            dict: 解析后的结果 (通常为 JSON dict)
        """
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        文本向量化

        Args:
            text: 待向量化的文本

        Returns:
            list[float]: 嵌入向量
        """
        pass

    # ──────────────────────────────────────────────────────────
    # 可选方法 (子类可选实现)
    # ──────────────────────────────────────────────────────────

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批量文本向量化 (可选实现)

        默认实现为串行调用 embed_text
        子类可覆盖以实现批量优化
        """
        return [await self.embed_text(t) for t in texts]

    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        **kwargs,
    ):
        """
        流式文本生成 (可选实现)

        默认抛出 NotImplementedError
        使用 async generator 语法
        """
        raise NotImplementedError(
            f"{self.name} does not support streaming"
        )

    def get_model_info(self) -> dict:
        """获取当前模型信息"""
        return {
            "provider": self.name,
            "tier": self.tier.value,
            "model": self.config.model,
            "local": self.config.local,
            "cost_per_1k": self.config.cost_per_1k_tokens,
            "capabilities": [c.value for c in self.capabilities],
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name={self.name!r}, tier={self.tier.value}, "
            f"model={self.config.model!r})>"
        )
