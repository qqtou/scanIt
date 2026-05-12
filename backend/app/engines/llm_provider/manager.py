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

import asyncio
import logging
import os
import time
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


# Provider 名称 → 类 的映射（用于 select_provider）
_PROVIDER_CLASSES = {
    "ollama": OllamaProvider,
    "douyin": DouyinProvider,
    "zhipu": ZhipuProvider,
    "kimi": KimiProvider,
    "aliyun": AliyunProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


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

    # 启动时间（用于日志）
    _start_time: float = field(default_factory=time.monotonic, repr=False)

    def __post_init__(self):
        tier_config = os.getenv("AI_TIER", "auto").lower()
        tier_map = {
            "tier1": ProviderTier.TIER_1_LOCAL,
            "tier1_local": ProviderTier.TIER_1_LOCAL,
            "local": ProviderTier.TIER_1_LOCAL,
            "tier2": ProviderTier.TIER_2_BUDGET,
            "tier2_budget": ProviderTier.TIER_2_BUDGET,
            "budget": ProviderTier.TIER_2_BUDGET,
            "tier3": ProviderTier.TIER_3_ENTERPRISE,
            "tier3_enterprise": ProviderTier.TIER_3_ENTERPRISE,
            "enterprise": ProviderTier.TIER_3_ENTERPRISE,
        }
        self._default_tier = tier_map.get(tier_config)

        logger.info(
            f"[ProviderManager] Initializing | AI_TIER={os.getenv('AI_TIER', 'auto')} "
            f"-> tier={self._default_tier.value if self._default_tier else 'auto'}"
        )

        self._register_all_providers()
        self._auto_detect_and_select()

        elapsed = time.monotonic() - self._start_time
        available = sum(1 for p in self._providers.values() if p.is_available())
        logger.info(
            f"[ProviderManager] Ready | registered={len(self._providers)} "
            f"available={available} elapsed={elapsed:.2f}s"
        )

    # ──────────────────────────────────────────────────────────
    # Provider 注册
    # ──────────────────────────────────────────────────────────

    def _register_all_providers(self):
        """注册所有可能的 Provider（仅注册，实际可用性在 init 时检测）"""
        # ─── Tier 1: 本地免费 ─────────────────────────────────
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

        # ─── Tier 2: 低成本云 ─────────────────────────────────
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
                        cost_per_1k_tokens=0.00014,
                        max_tokens=32768,
                    )
                )
            )
        else:
            logger.info("[ProviderManager] DouyinProvider skipped (no DOUYIN_API_KEY)")

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
                        cost_per_1k_tokens=0.0014,
                        max_tokens=8192,
                    )
                )
            )
        else:
            logger.info("[ProviderManager] ZhipuProvider skipped (no ZHIPU_API_KEY)")

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
        else:
            logger.info("[ProviderManager] KimiProvider skipped (no KIMI_API_KEY)")

        # ─── Tier 3: 企业级 ──────────────────────────────────
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
                        cost_per_1k_tokens=0.0028,
                    )
                )
            )
        else:
            logger.info("[ProviderManager] AliyunProvider skipped (no ALIYUN_API_KEY)")

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
        else:
            logger.info("[ProviderManager] OpenAIProvider skipped (no OPENAI_API_KEY)")

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
        else:
            logger.info("[ProviderManager] AnthropicProvider skipped (no ANTHROPIC_API_KEY)")

    def _register_provider(self, provider: BaseProvider):
        """注册单个 Provider 并记录日志"""
        self._providers[provider.name] = provider
        caps = [c.value for c in provider.capabilities]
        tier_name = provider.tier.value
        logger.info(
            f"[ProviderManager] Registered: {provider.name} | "
            f"Tier: {tier_name} | Caps: {caps}"
        )

    # ──────────────────────────────────────────────────────────
    # 自动检测与选择
    # ──────────────────────────────────────────────────────────

    def _auto_detect_and_select(self):
        """自动检测可用 Provider 并选择最优

        初始化策略：尝试异步并发初始化所有 Provider（检测连通性），
        如果已在事件循环中则用 create_task，否则用 run_until_complete。
        异步初始化失败时回退到同步配置选择（_select_by_config）。
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环中异步执行（不阻塞）
                asyncio.create_task(self._init_all_async())
            else:
                loop.run_until_complete(self._init_all_async())
        except Exception as e:
            logger.warning(
                f"[ProviderManager] Async init error: {e}, "
                f"falling back to sync select"
            )
            self._select_by_config()

    async def _init_all_async(self):
        """异步初始化所有 Provider 并选择"""
        init_tasks = [
            self._init_provider(p)
            for p in self._providers.values()
        ]
        results = await asyncio.gather(*init_tasks, return_exceptions=True)

        # 汇总初始化结果
        ok_count = sum(1 for r in results if r is True)
        fail_count = len(results) - ok_count
        logger.info(
            f"[ProviderManager] Init complete | ok={ok_count} fail={fail_count}"
        )

        # 选择最优 Provider
        self._do_select()

    async def _init_provider(self, provider: BaseProvider):
        """初始化单个 Provider（验证连通性）"""
        try:
            start = time.monotonic()
            ok = await provider.initialize()
            elapsed = time.monotonic() - start
            if ok:
                logger.info(
                    f"[ProviderManager] {provider.name} initialized OK "
                    f"| model={provider.config.model} elapsed={elapsed:.2f}s"
                )
            else:
                logger.warning(
                    f"[ProviderManager] {provider.name} initialized FAIL "
                    f"| model={provider.config.model}"
                )
            return ok
        except Exception as e:
            logger.warning(f"[ProviderManager] {provider.name} init exception: {e}")
            return False

    def _do_select(self):
        """执行 Provider 选择逻辑（按 Tier 优先级 + 配置偏好）

        选择规则：
        1. 筛选支持该能力且可用的 Provider
        2. 按 Tier 排序（Tier1 本地优先 → Tier2 低成本 → Tier3 企业级）
        3. 如果配置了默认 Tier（AI_TIER 环境变量），优先选该 Tier 的 Provider
        4. 选排序后第一个作为该能力的默认 Provider
        """
        logger.info(
            f"[ProviderManager] Selecting providers | default_tier="
            f"{self._default_tier.value if self._default_tier else 'auto'}"
        )

        for capability in Capability:
            candidates = [
                (name, provider)
                for name, provider in self._providers.items()
                if provider.supports(capability) and provider.is_available()
            ]

            if not candidates:
                logger.warning(
                    f"[ProviderManager] No available provider for {capability.value}"
                )
                continue

            # 按 Tier 排序（数字越小 = 越优先）
            candidates.sort(key=lambda x: x[1].tier._tier_order)

            # 如果配置了默认 Tier，优先选该 Tier
            if self._default_tier is not None:
                tier_candidates = [
                    c for c in candidates
                    if c[1].tier == self._default_tier
                ]
                if tier_candidates:
                    candidates = tier_candidates

            best_name = candidates[0][0]
            best_provider = candidates[0][1]
            self._capability_routes[capability] = best_name

            # 打印所有候选者（调试用）
            all_candidates = ", ".join(
                f"{n}({p.tier.value})" for n, p in candidates
            )
            logger.info(
                f"[ProviderManager] Selected for {capability.value}: "
                f"{best_name} (Tier: {best_provider.tier.value}) | "
                f"candidates=[{all_candidates}]"
            )

    def _select_by_config(self):
        """按环境变量配置选择 Provider（同步回退）"""
        logger.info("[ProviderManager] Falling back to config-based selection")
        for capability in Capability:
            if self._default_tier:
                for name, provider in self._providers.items():
                    if (provider.supports(capability)
                            and provider.is_available()
                            and provider.tier == self._default_tier):
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
        """获取指定能力的 Provider

        降级策略（逐级尝试）：
        1. 指定 Tier → 找该 Tier 下可用的 Provider
        2. 指定 Tier 不可用 → 降级到任何可用的 Provider
        3. 未指定 Tier → 从路由表查找自动选择的 Provider
        4. 路由表也没有 → 找任何可用的 Provider

        Args:
            capability: 能力类型
            tier: 强制使用指定层级 (覆盖自动选择)

        Returns:
            BaseProvider | None: 可用的 Provider
        """
        if tier:
            if isinstance(tier, str):
                tier = ProviderTier(tier)
            candidates = [
                (n, p)
                for n, p in self._providers.items()
                if p.supports(capability)
                and p.tier == tier
                and p.is_available()
            ]
            if candidates:
                return candidates[0][1]
            # 降级策略 2：指定 Tier 不可用，回退到任何可用的 Provider
            for n, p in self._providers.items():
                if p.supports(capability) and p.is_available():
                    logger.warning(
                        f"[ProviderManager] Requested tier={tier.value} for "
                        f"{capability.value} unavailable, falling back to {p.name}"
                    )
                    return p
            logger.warning(
                f"[ProviderManager] No provider for {capability.value} "
                f"with tier={tier.value}"
            )
            return None

        # 降级策略 3：使用路由表（_do_select 自动选择的结果）
        provider_name = self._capability_routes.get(capability)
        if provider_name and provider_name in self._providers:
            return self._providers[provider_name]

        # 降级策略 4：路由表也没有，找任何可用的 Provider
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

    def select_provider(self, name: str) -> BaseProvider | None:
        """
        手动选择指定名称的 Provider（API 路由使用）

        Args:
            name: Provider 名称（如 'ollama', 'douyin', 'openai'）

        Returns:
            BaseProvider | None
        """
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")

        provider = self._providers[name]
        if not provider.is_available():
            raise ValueError(f"Provider {name} is not available")

        # 更新所有 capability 的路由指向此 provider
        for cap in provider.capabilities:
            if provider.supports(cap):
                self._capability_routes[cap] = name

        logger.info(f"[ProviderManager] Manual provider selection: {name}")
        return provider

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
        logger.info(f"[ProviderManager] set_tier: {tier.value} | capability={capability}")

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
        """记录一次 API 调用（用于成本追踪）"""
        if provider_name not in self._providers:
            return

        provider = self._providers[provider_name]
        cost = provider.get_cost_estimate(input_tokens, output_tokens)

        self._total_cost_usd += cost
        self._call_counts[provider_name] = self._call_counts.get(provider_name, 0) + 1
        self._token_counts[provider_name] = (
            self._token_counts.get(provider_name, 0) + input_tokens + output_tokens
        )

        logger.debug(
            f"[ProviderManager] Call recorded | provider={provider_name} "
            f"input_tokens={input_tokens} output_tokens={output_tokens} "
            f"cost=${cost:.6f} total=${self._total_cost_usd:.6f}"
        )

    def get_cost_summary(self) -> dict:
        """获取成本汇总"""
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

    def get_tier(self) -> ProviderTier | None:
        """获取当前配置的默认 Tier"""
        return self._default_tier

    def list_capabilities(self) -> list[str]:
        """列出所有可用的能力"""
        return [cap.value for cap in Capability]

    def __repr__(self) -> str:
        routes = {c.value: n for c, n in self._capability_routes.items()}
        return f"<ProviderManager(active_routes={routes})>"
