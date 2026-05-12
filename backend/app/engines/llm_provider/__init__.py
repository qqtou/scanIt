"""
ScanIt AI Provider 统一接口包

提供多 Provider 自动检测和切换能力，支持 Tier 1-3 分层调度。

快速使用:
    from app.engines.llm_provider import ProviderManager, Capability, ProviderTier

    manager = ProviderManager()

    # 文本生成
    provider = manager.get_text_provider()
    text = await provider.generate_text("描述这张图片的内容")

    # 图片理解
    provider = manager.get_vision_provider()
    result = await provider.understand_image(image_bytes, "这张图描述了什么？")

    # 向量嵌入
    provider = manager.get_embed_provider()
    vec = await provider.embed_text("待向量化的文本")

    # 成本查询
    print(manager.get_cost_summary())

环境变量:
    AI_TIER=auto|tier1_local|tier2_budget|tier3_enterprise

    # Tier 1 本地
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_TEXT_MODEL=qwen2.5:7b
    OLLAMA_VISION_MODEL=qwen-vl:7b
    OLLAMA_EMBED_MODEL=nomic-embed-text

    # Tier 2 低成本云
    DOUYIN_API_KEY=...        # 豆包 ¥0.001/K
    ZHIPU_API_KEY=...          # 智谱 ¥0.01/K
    KIMI_API_KEY=...           # Kimi ¥0.01/K

    # Tier 3 企业级
    ALIYUN_API_KEY=...         # 阿里通义
    OPENAI_API_KEY=...        # OpenAI
    ANTHROPIC_API_KEY=...     # Claude
"""

from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderTier,
    Capability,
)

from .manager import ProviderManager

from .local import OllamaProvider

from .cloud import (
    DouyinProvider,
    ZhipuProvider,
    KimiProvider,
    AliyunProvider,
    OpenAIProvider,
    AnthropicProvider,
)

__all__ = [
    # 核心
    "ProviderManager",
    "BaseProvider",
    "ProviderConfig",
    "ProviderTier",
    "Capability",
    # Tier 1
    "OllamaProvider",
    # Tier 2
    "DouyinProvider",
    "ZhipuProvider",
    "KimiProvider",
    # Tier 3
    "AliyunProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    # 快捷函数
    "get_manager",
    "get_text_provider",
    "get_vision_provider",
    "get_embed_provider",
]

# 单例管理器实例 (延迟初始化)
_manager: ProviderManager | None = None


def get_manager() -> ProviderManager:
    """获取 ProviderManager 单例"""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def get_text_provider(tier: ProviderTier | str | None = None):
    """快捷方法: 获取文本生成 Provider"""
    return get_manager().get_text_provider(tier)


def get_vision_provider(tier: ProviderTier | str | None = None):
    """快捷方法: 获取图片理解 Provider"""
    return get_manager().get_vision_provider(tier)


def get_embed_provider(tier: ProviderTier | str | None = None):
    """快捷方法: 获取向量嵌入 Provider"""
    return get_manager().get_embed_provider(tier)


# 别名
get_provider_manager = get_manager
