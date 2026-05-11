"""
AI Provider 管理器

核心职责:
1. 注册所有 Provider (本地 + 云端)
2. 启动时自动检测可用 Provider
3. 根据配置和 Tier 选择最优 Provider
4. 能力路由 (不同任务自动分发到合适的 Provider)
5. 自动降级 (Provider 不可用时切换到备选)
6. 成本追踪
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings

from .base import BaseProvider, Capability, ProviderConfig, ProviderTier

from .local import OllamaProvider
from .cloud import (
    DouyinProvider,
    ZhipuProvider,
    KimiProvider,
    AliyunProvider,
    OpenAIProvider,
    AnthropicProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderManager:
    """
    AI Provider 管理器

    用法示例:

        # 自动检测并选择最优 Provider
        manager = ProviderManager()

        # 获取文本生成 Provider
        text_provider = manager.get_provider(Capability.TEXT_GENERATION)

        # 获取图片理解 Provider
        vision_provider = manager.get_provider(Capability.IMAGE_UNDERSTANDING)

        # 获取向量嵌入 Provider
        embed_provider = manager.get_provider(Capability.EMBEDDING)

        # 手动指定 Tier (覆盖自动选择)
        manager.set_tier(ProviderTier.TIER_1_LOCAL)

        # 查看成本
        print(manager.get_cost_summary())
    """

    # 所有注册的 Provider: name → provider
    _providers: dict[str, BaseProvider] = field(default_factory=dict)

    # 能力 → 当前选中的 provider name
    _capability_routes: dict[Capability, str] = field(default_factory=dict)

    # 成本追踪
    _total_cost_usd: float = 0.0
    _call_counts: dict[str, int] = field(default_factory=dict)
    _token_counts: dict[str, int] = field(default_factory=dict)

    # 配置的默认 Tier
    _default_tier: ProviderTier | None = None

    def __post_init__(self):
        # 读取配置决定默认 Tier
        tier_config = os.getenv("AI_TIER", "auto").lower()
        if tier_config == "tier1" or tier_config == "tier1_local" or tier_config == "local":
            self._default_tier = ProviderTier.TIER_1_LOCAL
        elif tier_config == "tier2" or tier_config == "tier2_budget" or tier_config == "budget":
            self._default_tier = ProviderTier.TIER_2_BUDGET
        elif tier_config == "tier3" or tier_config == "tier3_enterprise" or tier_config == "enterprise":
            self._default_tier = ProviderTier.TIER_3_ENTERPRISE
        else:
            self._default_tier = None  # auto

        self._register_all_providers()
        self._auto_detect_and_select()

    # ──────────────────────────────────────────────────────────
    # Provider 注册
    # ──────────────────────────────────────────────────────────

    def _register_all_providers(self):
        """注册所有可能的 Provider"""

        # ─── Tier 1: 本地免费 ───
        self._register_provider(
            OllamaProvider(
                config=ProviderConfig(
                    name="ollama",
                    tier=ProviderTier.TIER_1_LOCAL,
                    capabilities=[
                        Capability.TEXT_GENERATION,
                        Capability.IMAGE_UNDERSTANDING,
                        Capability.EMBEDDING,
                    ],
                    local=True,
                    cost_per_1k_tokens=0.0,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    model=os.getenv("OLLAMA_TEXT_MODEL", "qwen2.5:7b"),
                    timeout=120,
                )
            )
        )

        # ─── Tier 2: 低成本云 ───
        douyin_key = os.getenv("DOUYIN_API_KEY", "")
        if douyin_key:
            self._register_provider(
                DouyinProvider(
                    config=ProviderConfig(
                        name="douyin",
                        tier=ProviderTier.TIER_2_BUDGET,
                        capabilities=[Capability.TEXT_GENERATION],
                        api_key=douyin_key,
                        model=os.getenv("DOUYIN_MODEL", "doubao-pro-32k"),
                        cost_per_1k_tokens=0.00014,  # ~¥0.001
                        max_tokens=32768,
                    )
                )
            )

        zhipu_key = os.getenv("ZHIPU_API_KEY", "")
        if zhipu_key:
            self._register_provider(
                ZhipuProvider(
                    config=ProviderConfig(
                        name="zhipu",
                        tier=ProviderTier.TIER_2_BUDGET,
                        capabilities=[
                            Capability.TEXT_GENERATION,
                            Capability.IMAGE_UNDERSTANDING,
                        ],
                        api_key=zhipu_key,
                        model=os.getenv("ZHIPU_MODEL", "glm-4"),
                        cost_per_1k_tokens=0.0014,  # ¥0.01
                        max_tokens=8192,
                    )
                )
            )

        kimi_key = os.getenv("KIMI_API_KEY", "")
        if kimi_key:
            self._register_provider(
                KimiProvider(
                    config=ProviderConfig(
                        name="kimi",
                        tier=ProviderTier.TIER_2_BUDGET,
                        capabilities=[Capability.TEXT_GENERATION],
                        api_key=kimi_key,
                        model=os.getenv("KIMI_MODEL", "moonshot-v1-128k"),
                        cost_per_1k_tokens=0.0014,
                        max_tokens=128000,
                    )
                )
            )

        # ─── Tier 3: 企业级 ───
        aliyun_key = os.getenv("ALIYUN_API_KEY", "")
        if aliyun_key:
            self._register_provider(
                AliyunProvider(
                    config=ProviderConfig(
                        name="aliyun",
                        tier=ProviderTier.TIER_3_ENTERPRISE,
                        capabilities=[
                            Capability.TEXT_GENERATION,
                            Capability.IMAGE_UNDERSTANDING,
                        ],
                        api_key=aliyun_key,
                        model=os.getenv("ALIYUN_MODEL", "qwen-vl-max"),
                        cost_per_1k_tokens=0.0028,  # ¥0.02
                    )
                )
            )

        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self._register_provider(
                OpenAIProvider(
                    config=ProviderConfig(
                        name="openai",
                        tier=ProviderTier.TIER_3_ENTERPRISE,
                        capabilities=[
                            Capability.TEXT_GENERATION,
                            Capability.IMAGE_UNDERSTANDING,
                            Capability.EMBEDDING,
                        ],
                        api_key=openai_key,
                        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                        cost_per_1k_tokens=0.005,
                        supports_streaming=True,
                    )
                )
            )

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            self._register_provider(
                AnthropicProvider(
                    config=ProviderConfig(
                        name="anthropic",
                        tier=ProviderTier.TIER_3_ENTERPRISE,
                        capabilities=[
                            Capability.TEXT_GENERATION,
                            Capability.IMAGE_UNDERSTANDING,
                        ],
                        api_key=anthropic_key,
                        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                        cost_per_1k_tokens=0.015,
                        max_tokens=200000,
                    )
                )
            )

    def _register_provider(self, provider: BaseProvider):
        """注册单个 Provider"""
        self._providers[provider.name] = provider
        caps = [c.value for c in provider.capabilities]
        tier_name = provider.tier.value
        logger.info(f"[ProviderManager] Registered: {provider.name} (Tier: {tier_name}, Caps: {caps})")

    # ──────────────────────────────────────────────────────────
    # 自动检测与选择
    # ──────────────────────────────────────────────────────────

    def _auto_detect_and_select(self):
        """自动检测可用 Provider 并选择最优"""

        import asyncio

        # 初始化所有 Provider
        for provider in self._providers.values():
            try:
                if asyncio.get_event_loop().is_running():
                    # 在已有事件循环中异步初始化
                    asyncio.create_task(self._init_provider(provider))
                else:
                    asyncio.run(self._init_provider(provider))
            except Exception as e:
                logger.warning(f"[ProviderManager] {provider.name} init error: {e}")

        # 等待初始化完成
        try:
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self._wait_and_select())
            else:
                asyncio.run(self._wait_and_select())
        except Exception as e:
            logger.warning(f"[ProviderManager] Auto-select error: {e}")
            # 回退：按配置选择
            self._select_by_config()

    async def _init_provider(self, provider: BaseProvider):
        """初始化单个 Provider"""
        try:
            ok = await provider.initialize()
            status = "OK" if ok else "FAIL"
            logger.info(f"[ProviderManager] {provider.name} initialize: {status}")
        except Exception as e:
            logger.warning(f"[ProviderManager] {provider.name} init exception: {e}")

    async def _wait_and_select(self):
        """等待初始化完成后选择"""
        import asyncio

        await asyncio.sleep(2)  # 等待初始化
        self._do_select()

    def _do_select(self):
        """执行 Provider 选择逻辑"""
        for capability in Capability:
            candidates = []

            for name, provider in self._providers.items():
                if provider.supports(capability) and provider.is_available():
                    candidates.append((name, provider))

            if not candidates:
                continue

            # 按 Tier 排序: Tier1 > Tier2 > Tier3
            candidates.sort(key=lambda x: x[1].tier._tier_order)

            # 如果配置了默认 Tier，优先选择该 Tier
            if self._default_tier is not None:
                tier_candidates = [c for c in candidates if c[1].tier == self._default_tier]
                if tier_candidates:
                    candidates = tier_candidates

            best_name = candidates[0][0]
            self._capability_routes[capability] = best_name

            tier_label = candidates[0][1].tier.value
            logger.info(
                f"[ProviderManager] Selected for {capability.value}: "
                f"{best_name} (Tier: {tier_label})"
            )

    def _select_by_config(self):
        """按环境变量配置选择 Provider"""
        for capability in Capability:
            if self._default_tier:
                for name, provider in self._providers.items():
                    if provider.supports(capability) and provider.tier == self._default_tier:
                        self._capability_routes[capability] = name
                        break

    # ──────────────────────────────────────────────────────────
    # Provider 获取
    # ──────────────────────────────────────────────────────────

    def get_provider(
        self,
        capability: Capability,
        tier: ProviderTier | str | None = None,
    ) -> BaseProvider | None:
        """
        获取指定能力的 Provider

        Args:
            capability: 能力类型
            tier: 强制使用指定层级 (覆盖自动选择)

        Returns:
            BaseProvider | None: 可用的 Provider
        """
        if tier:
            if isinstance(tier, str):
                tier = ProviderTier(tier)
            # 按 Tier 找
            candidates = [
                (n, p)
                for n, p in self._providers.items()
                if p.supports(capability) and p.tier == tier and p.is_available()
            ]
            if candidates:
                return candidates[0][1]
            return None

        # 使用路由表
        provider_name = self._capability_routes.get(capability)
        if provider_name and provider_name in self._providers:
            return self._providers[provider_name]

        # 降级: 找任何可用的
        for provider in self._providers.values():
            if provider.supports(capability) and provider.is_available():
                return provider

        return None

    def get_text_provider(self, tier: ProviderTier | str | None = None) -> BaseProvider | None:
        """快捷方法: 获取文本生成 Provider"""
        return self.get_provider(Capability.TEXT_GENERATION, tier)

    def get_vision_provider(self, tier: ProviderTier | str | None = None) -> BaseProvider | None:
        """快捷方法: 获取图片理解 Provider"""
        return self.get_provider(Capability.IMAGE_UNDERSTANDING, tier)

    def get_embed_provider(self, tier: ProviderTier | str | None = None) -> BaseProvider | None:
        """快捷方法: 获取向量嵌入 Provider"""
        return self.get_provider(Capability.EMBEDDING, tier)

    # ──────────────────────────────────────────────────────────
    # Tier 控制
    # ──────────────────────────────────────────────────────────

    def set_tier(
        self,
        tier: ProviderTier | str,
        capability: Capability | None = None,
    ):
        """
        设置使用的 Tier 层级

        用法:
            manager.set_tier("tier1_local")           # 全局使用本地
            manager.set_tier("tier2_budget")          # 全局使用低成本云
            manager.set_tier("tier3_enterprise")       # 全局使用企业级
            manager.set_tier("tier1_local", Capability.IMAGE_UNDERSTANDING)  # 仅图片用本地
        """
        if isinstance(tier, str):
            tier = ProviderTier(tier)

        self._default_tier = tier

        if capability:
            provider = self.get_provider(capability, tier)
            if provider:
                self._capability_routes[capability] = provider.name
        else:
            self._do_select()

    # ──────────────────────────────────────────────────────────
    # 成本追踪
    # ──────────────────────────────────────────────────────────

    def record_call(
        self,
        provider_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        """记录一次 API 调用"""
        if provider_name not in self._providers:
            return

        provider = self._providers[provider_name]
        cost = provider.get_cost_estimate(input_tokens, output_tokens)

        self._total_cost_usd += cost
        self._call_counts[provider_name] = self._call_counts.get(provider_name, 0) + 1
        self._token_counts[provider_name] = (
            self._token_counts.get(provider_name, 0) + input_tokens + output_tokens
        )

    def get_cost_summary(self) -> dict:
        """获取成本汇总"""
        # 转换为人民币 (假设汇率 7.2)
        cny_rate = float(os.getenv("USD_TO_CNY_RATE", "7.2"))

        return {
            "total_cost_usd": round(self._total_cost_usd, 6),
            "total_cost_cny": round(self._total_cost_usd * cny_rate, 4),
            "call_counts": dict(self._call_counts),
            "token_counts": dict(self._token_counts),
            "active_routes": {
                cap.value: name for cap, name in self._capability_routes.items()
            },
        }

    # ──────────────────────────────────────────────────────────
    # 状态查询
    # ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """获取所有 Provider 的状态"""
        status = {}
        for name, provider in self._providers.items():
            is_active = name in self._capability_routes.values()
            status[name] = {
                "tier": provider.tier.value,
                "capabilities": [c.value for c in provider.capabilities],
                "available": provider.is_available(),
                "active": is_active,
                "model": provider.config.model,
                "cost_per_1k": provider.config.cost_per_1k_tokens,
                "initialized": provider._initialized,
            }
        return status

    def list_capabilities(self) -> list[str]:
        """列出所有可用的能力"""
        return [cap.value for cap in Capability]

    def __repr__(self) -> str:
        routes = {c.value: n for c, n in self._capability_routes.items()}
        return f"<ProviderManager(active_routes={routes})>"
