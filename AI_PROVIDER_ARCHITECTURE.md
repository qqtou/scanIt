# ScanIt AI 能力分层方案

> 版本：v1.0
> 日期：2026-05-11
> 目标：零成本到全云端，按需切换，弹性适配

---

## 一、分层架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ScanIt AI Provider 分层                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Tier 0: 自动检测层 (AutoDetect)               │  │
│  │                                                                  │  │
│  │    启动时扫描：                                                  │  │
│  │    ✅ Ollama 是否运行 → 本地模型列表                             │  │
│  │    ✅ API Key 配置   → 云端服务                                 │  │
│  │    ✅ GPU 显存大小   → 选合适模型尺寸                            │  │
│  │    ✅ 内存大小       → 决定是否跑大模型                          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Tier 1: 本地免费层 (Free)                     │  │
│  │                                                                  │  │
│  │   Ollama 推理引擎 (统一本地推理接口)                            │  │
│  │   ┌──────────┬──────────┬──────────┬──────────┐                │  │
│  │   │ Qwen2.5  │ Qwen-VL  │ BGE-Large │ GLM4     │                │  │
│  │   │  7B/14B  │   7B     │  -zh-v1.5 │  9B      │                │  │
│  │   │ 文本生成 │ 图片理解 │  向量嵌入 │  备选    │                │  │
│  │   └──────────┴──────────┴──────────┴──────────┘                │  │
│  │                                                                  │  │
│  │   成本：¥0 (电费另算)                                          │  │
│  │   适用：个人开发者 / 小团队 / 隐私敏感场景                      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Tier 2: 低成本云层 (Budget)                  │  │
│  │                                                                  │  │
│  │   ┌──────────────┬──────────────┬──────────────┐              │  │
│  │   │ 豆包 (字节)   │ 智谱 GLM-4   │ Kimi (长文)  │              │  │
│  │   │ ¥0.001/K tok │ ¥0.01/K tok  │ ¥0.01/K tok  │              │  │
│  │   │ 文本生成首选  │ 多模态备选   │ 长文本分析   │              │  │
│  │   └──────────────┴──────────────┴──────────────┘              │  │
│  │                                                                  │  │
│  │   Embedding 可继续用本地 BGE（大头在 Vision）                   │  │
│  │   成本：¥1-10/月（1000次任务）                                 │  │
│  │   适用：中小企业 / 有一定预算的商业场景                         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Tier 3: 全功能云层 (Enterprise)              │  │
│  │                                                                  │  │
│  │   ┌──────────────┬──────────────┬──────────────┐              │  │
│  │   │ 阿里通义千问  │ GPT-4o      │ Claude       │              │  │
│  │   │ ¥0.02/K tok  │ $0.005/K tok│ ¥0.1/K tok   │              │  │
│  │   │ 图片+文本    │ 全能        │ 长上下文     │              │  │
│  │   └──────────────┴──────────────┴──────────────┘              │  │
│  │                                                                  │  │
│  │   成本：¥500-2000/月（重度使用）                               │  │
│  │   适用：大企业 / 高端定制 / 对准确率要求极高                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、场景匹配矩阵

| 场景 | 用户画像 | 推荐 Tier | 月成本估算 | 理由 |
|------|---------|---------|-----------|------|
| **个人练手** | 开发者学习、玩一玩 | Tier 1 全本地 | ¥0 | 先跑起来再说 |
| **内容创作者** | 摄影师、博主、自媒体 | Tier 1 + Tier 2 | ¥5 | 图片多，豆包够用 |
| **版权机构** | 需检测量大、报告专业 | Tier 2 | ¥50-200 | 豆包+本地 Embedding |
| **中型企业** | 商业侵权检测 | Tier 2 + Tier 3 | ¥200-500 | 豆包文本 + 阿里 Vision |
| **大型企业** | 全平台监控、高准确率 | Tier 3 全云 | ¥1000+ | 全功能、高可用 |
| **政府/涉密** | 政务、军工、金融 | Tier 1 全本地 | ¥0 | 数据不出内网 |
| **出海业务** | 跨国侵权检测 | Tier 3 | ¥500+ | 需要多语言+国际搜索引擎 |

---

## 三、核心代码设计

### 3.1 Provider 抽象层

```python
# backend/app/engines/llm_provider/__init__.py

"""
AI Provider 统一抽象层

支持多 Provider 自动检测和切换：
- Tier 1: 本地 Ollama (免费)
- Tier 2: 豆包/智谱/Kimi (低成本云)
- Tier 3: 阿里/腾讯/GPT/Claude (企业级)
"""

from .manager import ProviderManager
from .base import BaseProvider, ProviderConfig
from .local import OllamaProvider
from .cloud import (
    DouyinProvider,      # 豆包
    ZhipuProvider,        # 智谱 GLM
    KimiProvider,         # 月之暗面 Kimi
    AliyunProvider,       # 阿里通义
    OpenAIProvider,       # OpenAI
    AnthropicProvider,    # Claude
)

__all__ = [
    "ProviderManager",
    "BaseProvider",
    "ProviderConfig",
    "OllamaProvider",
    "DouyinProvider",
    "ZhipuProvider",
    "KimiProvider",
    "AliyunProvider",
    "OpenAIProvider",
    "AnthropicProvider",
]
```

### 3.2 Provider 基类

```python
# backend/app/engines/llm_provider/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProviderTier(Enum):
    """Provider 层级"""
    TIER_1_LOCAL = "tier1_local"      # 本地免费
    TIER_2_BUDGET = "tier2_budget"    # 低成本云
    TIER_3_ENTERPRISE = "tier3_enterprise"  # 企业级


class Capability(Enum):
    """能力类型"""
    TEXT_GENERATION = "text_generation"       # 文本生成
    IMAGE_UNDERSTANDING = "image_understanding"  # 图片理解
    EMBEDDING = "embedding"                   # 向量嵌入
    IMAGE_GENERATION = "image_generation"     # 图片生成


@dataclass
class ProviderConfig:
    """Provider 配置"""
    name: str
    tier: ProviderTier
    capabilities: list[Capability]
    api_key: str | None = None
    base_url: str | None = None
    model: str = ""
    local: bool = False
    cost_per_1k_tokens: float = 0.0  # USD
    max_tokens: int = 4096
    supports_streaming: bool = False


class BaseProvider(ABC):
    """Provider 抽象基类"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.tier = config.tier
        self.capabilities = config.capabilities

    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化 Provider
        
        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """文本生成"""
        pass

    @abstractmethod
    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """图片理解"""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """文本向量化"""
        pass

    def supports(self, capability: Capability) -> bool:
        """检查是否支持某能力"""
        return capability in self.capabilities

    def get_cost_estimate(self, tokens: int) -> float:
        """估算成本（USD）"""
        return (tokens / 1000) * self.config.cost_per_1k_tokens
```

### 3.3 Provider 管理器（核心）

```python
# backend/app/engines/llm_provider/manager.py

import os
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings

from .base import (
    BaseProvider, ProviderConfig, ProviderTier, Capability
)
from .local import OllamaProvider
from .cloud import (
    DouyinProvider, ZhipuProvider, KimiProvider,
    AliyunProvider, OpenAIProvider, AnthropicProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderManager:
    """
    AI Provider 管理器
    
    核心职责:
    1. 自动检测可用 Provider（本地 + 云端）
    2. 根据配置和 Tier 选择最优 Provider
    3. 能力路由（不同任务用不同 Provider）
    4. 自动降级（Provider 不可用时切换）
    5. 成本追踪
    """

    # 可用 Provider 列表
    providers: dict[str, BaseProvider] = field(default_factory=dict)

    # 能力路由表：capability → provider_name
    capability_routes: dict[Capability, str] = field(default_factory=dict)

    # 当前激活的 Provider（按能力）
    active_providers: dict[Capability, str] = field(default_factory=dict)

    # 成本追踪
    total_cost_usd: float = 0.0
    call_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self._register_all_providers()
        self._auto_detect_and_select()

    def _register_all_providers(self):
        """注册所有可能的 Provider"""

        # ========== Tier 1: 本地免费 ==========

        # Ollama (统一本地推理接口)
        self._register_provider(OllamaProvider(
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
            )
        ))

        # ========== Tier 2: 低成本云 ==========

        # 豆包 (字节跳动) - 文本首选
        douyin_key = os.getenv("DOUYIN_API_KEY", "")
        if douyin_key:
            self._register_provider(DouyinProvider(
                config=ProviderConfig(
                    name="douyin",
                    tier=ProviderTier.TIER_2_BUDGET,
                    capabilities=[Capability.TEXT_GENERATION],
                    api_key=douyin_key,
                    model=os.getenv("DOUYIN_MODEL", "doubao-pro-32k"),
                    cost_per_1k_tokens=0.00014,  # ~¥0.001
                )
            ))

        # 智谱 GLM-4
        zhipu_key = os.getenv("ZHIPU_API_KEY", "")
        if zhipu_key:
            self._register_provider(ZhipuProvider(
                config=ProviderConfig(
                    name="zhipu",
                    tier=ProviderTier.TIER_2_BUDGET,
                    capabilities=[
                        Capability.TEXT_GENERATION,
                        Capability.IMAGE_UNDERSTANDING,
                        Capability.EMBEDDING,
                    ],
                    api_key=zhipu_key,
                    model=os.getenv("ZHIPU_MODEL", "glm-4"),
                    cost_per_1k_tokens=0.0014,  # ¥0.01
                )
            ))

        # Kimi (月之暗面)
        kimi_key = os.getenv("KIMI_API_KEY", "")
        if kimi_key:
            self._register_provider(KimiProvider(
                config=ProviderConfig(
                    name="kimi",
                    tier=ProviderTier.TIER_2_BUDGET,
                    capabilities=[Capability.TEXT_GENERATION],
                    api_key=kimi_key,
                    model=os.getenv("KIMI_MODEL", "moonshot-v1-128k"),
                    cost_per_1k_tokens=0.0014,
                    max_tokens=128000,
                )
            ))

        # ========== Tier 3: 企业级 ==========

        # 阿里通义千问
        aliyun_key = os.getenv("ALIYUN_API_KEY", "")
        if aliyun_key:
            self._register_provider(AliyunProvider(
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
            ))

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self._register_provider(OpenAIProvider(
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
            ))

        # Anthropic Claude
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            self._register_provider(AnthropicProvider(
                config=ProviderConfig(
                    name="anthropic",
                    tier=ProviderTier.TIER_3_ENTERPRISE,
                    capabilities=[
                        Capability.TEXT_GENERATION,
                        Capability.IMAGE_UNDERSTANDING,
                    ],
                    api_key=anthropic_key,
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus"),
                    cost_per_1k_tokens=0.015,
                    max_tokens=200000,
                )
            ))

    def _register_provider(self, provider: BaseProvider):
        """注册 Provider"""
        self.providers[provider.name] = provider
        logger.info(f"[ProviderManager] Registered provider: {provider.name} "
                   f"(Tier: {provider.tier.value}, "
                   f"Caps: {[c.value for c in provider.capabilities]})")

    def _auto_detect_and_select(self):
        """
        自动检测可用 Provider 并选择最优
        
        选择策略:
        1. 优先使用本地（零成本）
        2. 根据 Tier 配置选择
        3. 每个 Capability 选择一个最优 Provider
        """

        # 检测每个 Capability 的可用 Provider
        for capability in Capability:
            available = []
            for name, provider in self.providers.items():
                if provider.supports(capability):
                    # 尝试初始化
                    try:
                        import asyncio
                        if asyncio.get_event_loop().is_running():
                            # 在已有事件循环中初始化
                            initialized = asyncio.create_task(
                                provider.initialize()
                            )
                        else:
                            initialized = asyncio.run(provider.initialize())

                        if initialized:
                            available.append((name, provider))
                            logger.info(f"[ProviderManager] {name} initialized for {capability.value}")
                    except Exception as e:
                        logger.warning(f"[ProviderManager] {name} init failed: {e}")

            if available:
                # 按 Tier 排序：Tier1 > Tier2 > Tier3
                available.sort(key=lambda x: x[1].tier.value)
                best = available[0][0]
                self.active_providers[capability] = best
                self.capability_routes[capability] = best
                logger.info(f"[ProviderManager] Selected for {capability.value}: {best}")

    def get_provider(
        self,
        capability: Capability,
        tier_preference: ProviderTier | None = None,
    ) -> BaseProvider | None:
        """
        获取指定能力的 Provider
        
        Args:
            capability: 能力类型
            tier_preference: 偏好层级（用于覆盖自动选择）
        
        Returns:
            BaseProvider | None
        """

        # 如果指定了 Tier，按 Tier 选
        if tier_preference:
            candidates = []
            for name, provider in self.providers.items():
                if provider.supports(capability) and provider.tier == tier_preference:
                    candidates.append(provider)
            if candidates:
                return candidates[0]

        # 否则用默认路由
        provider_name = self.active_providers.get(capability)
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]

        # 降级：找任何支持该能力的 Provider
        for provider in self.providers.values():
            if provider.supports(capability):
                return provider

        return None

    def set_provider_tier(
        self,
        tier: ProviderTier | str,
        capability: Capability | None = None,
    ):
        """
        手动设置 Provider 层级
        
        用法示例:
        manager.set_provider_tier("tier1_local")  # 全局使用本地
        manager.set_provider_tier("tier2_budget", Capability.TEXT_GENERATION)
        """
        if isinstance(tier, str):
            tier = ProviderTier(tier)

        if capability:
            # 只设置某个能力
            provider = self.get_provider(capability, tier)
            if provider:
                self.active_providers[capability] = provider.name
        else:
            # 设置所有能力
            for cap in Capability:
                provider = self.get_provider(cap, tier)
                if provider:
                    self.active_providers[cap] = provider.name

    def report_cost(self, provider_name: str, tokens: int):
        """记录成本"""
        if provider_name in self.providers:
            cost = self.providers[provider_name].get_cost_estimate(tokens)
            self.total_cost_usd += cost
            self.call_counts[provider_name] = self.call_counts.get(provider_name, 0) + 1

    def get_cost_summary(self) -> dict:
        """获取成本汇总"""
        return {
            "total_cost_usd": self.total_cost_usd,
            "total_cost_cny": self.total_cost_usd * 7.2,  # 假设汇率
            "call_counts": dict(self.call_counts),
            "active_providers": {
                cap.value: name
                for cap, name in self.active_providers.items()
            },
        }

    def get_status(self) -> dict:
        """获取所有 Provider 状态"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "tier": provider.tier.value,
                "capabilities": [c.value for c in provider.capabilities],
                "active": name in self.active_providers.values(),
                "model": provider.config.model,
                "cost_per_1k": provider.config.cost_per_1k_tokens,
            }
        return status
```

### 3.4 Tier 1 本地 Provider（Ollama）

```python
# backend/app/engines/llm_provider/local.py

import httpx
from typing import Any

from .base import BaseProvider, ProviderConfig, Capability


class OllamaProvider(BaseProvider):
    """
    Ollama 本地推理 Provider
    
    通过 Ollama 统一接口访问本地大模型：
    - 文本生成: qwen2.5:7b, qwen2.5:14b, glm4:9b
    - 图片理解: llava:7b, qwen-vl:7b
    - 向量嵌入: nomic-embed-text, bge-large
    """

    async def initialize(self) -> bool:
        """检测 Ollama 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    logger.info(f"[Ollama] Found {len(models)} models: "
                              f"{[m['name'] for m in models]}")
                    return True
        except Exception as e:
            logger.debug(f"[Ollama] Not available: {e}")
        return False

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """调用本地模型生成文本"""
        model = self.config.model or "qwen2.5:7b"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.config.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.3),
                        "num_predict": kwargs.get("max_tokens", 4096),
                    }
                }
            )
            result = response.json()
            return result["message"]["content"]

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """使用 Vision 模型理解图片"""
        import base64
        from io import BytesIO

        model = "qwen-vl:7b"  # 或 llava:7b

        # 处理图片数据
        if isinstance(image_url, bytes):
            b64_data = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64_data}"
        else:
            image_data = image_url

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}},
                    {"type": "text", "text": prompt},
                ]
            }
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.config.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                }
            )
            result = response.json()
            content = result["message"]["content"]

            # 解析 JSON 返回
            import json
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                return json.loads(content.strip())
            except:
                return {"raw_response": content}

    async def embed_text(self, text: str) -> list[float]:
        """使用 Embedding 模型向量化"""
        model = "nomic-embed-text"  # 或 bge-large:latest

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.config.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                }
            )
            result = response.json()
            return result["embedding"]
```

### 3.5 Tier 2/3 云 Provider

```python
# backend/app/engines/llm_provider/cloud.py

import httpx
import json
from typing import Any

from .base import BaseProvider, ProviderConfig, Capability


class DouyinProvider(BaseProvider):
    """
    字节豆包 API
    
    文档: https://www.volcengine.com/docs/82379/1263482
    定价: ¥0.001 / 1K tokens (doubao-pro-32k)
    """

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                }
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]


class ZhipuProvider(BaseProvider):
    """
    智谱 GLM-4 API
    
    文档: https://open.bigmodel.cn/dev/api
    定价: ¥0.01 / 1K tokens
    """

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                json={
                    "model": self.config.model,
                    "messages": messages,
                }
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """智谱图片理解 (GLM-4V)"""
        import base64
        from io import BytesIO

        if isinstance(image_url, bytes):
            b64_data = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64_data}"
        else:
            image_data = image_url

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}},
                    {"type": "text", "text": prompt},
                ]
            }
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": "glm-4v",  # 专用 Vision 模型
                    "messages": messages,
                }
            )
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            try:
                return json.loads(content)
            except:
                return {"raw_response": content}


class KimiProvider(BaseProvider):
    """
    月之暗面 Kimi API
    
    文档: https://platform.moonshot.cn/docs
    定价: ¥0.01 / 1K tokens
    优势: 128K 超长上下文
    """

    BASE_URL = "https://api.moonshot.cn/v1"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                json={
                    "model": self.config.model,
                    "messages": messages,
                }
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]


class AliyunProvider(BaseProvider):
    """
    阿里云通义千问 API
    
    文档: https://help.aliyun.com/zh/model-studio
    支持: qwen-vl-max (图片理解), qwen-max (文本)
    """

    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "input": {"messages": messages},
                }
            )
            result = response.json()
            return result["output"]["text"]

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """通义千问图片理解"""
        import base64
        from io import BytesIO

        if isinstance(image_url, bytes):
            b64_data = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64_data}"
        else:
            image_data = image_url

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_data},
                    {"text": prompt},
                ]
            }
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/services/aigc/multimodal-generation/generation",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.config.model,
                    "input": {"messages": messages},
                }
            )
            result = response.json()
            content = result["output"]["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except:
                return {"raw_response": content}


class OpenAIProvider(BaseProvider):
    """OpenAI (Tier 3 企业级备选)"""
    BASE_URL = "https://api.openai.com/v1"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.config.api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=messages,
        )
        return response.choices[0].message.content

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        import base64
        from openai import AsyncOpenAI

        if isinstance(image_url, bytes):
            b64 = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64}"
        else:
            image_data = image_url

        client = AsyncOpenAI(api_key=self.config.api_key)
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}},
                    {"type": "text", "text": prompt},
                ]
            }]
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except:
            return {"raw_response": content}

    async def embed_text(self, text: str) -> list[float]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.config.api_key)
        response = await client.embeddings.create(
            model=self.config.model,
            input=text,
        )
        return response.data[0].embedding


class AnthropicProvider(BaseProvider):
    """Anthropic Claude (Tier 3 企业级)"""

    BASE_URL = "https://api.anthropic.com/v1"

    async def initialize(self) -> bool:
        return bool(self.config.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.config.api_key)

        response = await client.messages.create(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        from anthropic import AsyncAnthropic

        if isinstance(image_url, bytes):
            import base64
            b64 = base64.b64encode(image_url).decode()
            media = {"type": "base64", "media_type": "image/jpeg", "data": b64}
        else:
            media = {"type": "url", "source": {"type": "url", "url": image_url}}

        client = AsyncAnthropic(api_key=self.config.api_key)
        response = await client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [media, {"type": "text", "text": prompt}]
            }]
        )
        content = response.content[0].text
        try:
            return json.loads(content)
        except:
            return {"raw_response": content}
```

---

## 四、配置方式

### 4.1 环境变量配置

```bash
# ========== Tier 1: 本地 (零成本) ==========
# Ollama 推理服务
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEXT_MODEL=qwen2.5:7b
OLLAMA_VISION_MODEL=qwen-vl:7b
OLLAMA_EMBED_MODEL=nomic-embed-text

# ========== Tier 2: 低成本云 ==========
# 豆包 (字节跳动) - ¥0.001/K tokens
DOUYIN_API_KEY=your-douyin-key
DOUYIN_MODEL=doubao-pro-32k

# 智谱 GLM-4 - ¥0.01/K tokens
ZHIPU_API_KEY=your-zhipu-key
ZHIPU_MODEL=glm-4

# Kimi - ¥0.01/K tokens
KIMI_API_KEY=your-kimi-key
KIMI_MODEL=moonshot-v1-128k

# ========== Tier 3: 企业级 ==========
# 阿里通义千问
ALIYUN_API_KEY=your-aliyun-key
ALIYUN_MODEL=qwen-vl-max

# OpenAI (备选)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o

# Anthropic Claude (备选)
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-3-opus-20240229
```

### 4.2 用户配置界面

```yaml
# PUT /api/v1/settings/ai-tier

# 方案A: 零成本
{
  "tier": "tier1_local",
  "description": "全部使用本地模型，无任何费用"
}

# 方案B: 低成本
{
  "tier": "tier2_budget",
  "capabilities": {
    "text_generation": "douyin",    # 豆包
    "embedding": "ollama",           # 本地 BGE
    "image_understanding": "zhipu"    # 智谱 GLM-4V
  },
  "description": "Embedding 本地，其余云端，月成本 ¥1-10"
}

# 方案C: 企业全功能
{
  "tier": "tier3_enterprise",
  "capabilities": {
    "text_generation": "aliyun",
    "image_understanding": "aliyun",
    "embedding": "openai"
  },
  "description": "全云端企业级，月成本 ¥500-2000"
}
```

---

## 五、Ollama 本地部署指南

### 5.1 安装 Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows: 下载安装包
# https://ollama.com/download

# 验证
ollama --version
```

### 5.2 下载模型

```bash
# 文本生成模型 (Tier 1 首选)
ollama pull qwen2.5:7b        # 4.9GB, 中文优化
ollama pull qwen2.5:14b       # 9GB, 效果更好
ollama pull glm4:9b           # 智谱, 5.2GB

# Vision 模型 (图片理解)
ollama pull qwen-vl:7b       # 4.7GB, 支持图片
ollama pull llava:7b          # 4.7GB, 支持图片

# Embedding 模型
ollama pull nomic-embed-text  # 支持中文
```

### 5.3 启动服务

```bash
# 启动 Ollama 服务 (后台运行)
ollama serve

# 测试文本生成
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [{"role": "user", "content": "你好"}]
}'

# 测试图片理解
curl http://localhost:11434/api/chat -d '{
  "model": "qwen-vl:7b",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
      {"type": "text", "text": "描述这张图片"}
    ]
  }]
}'
```

### 5.4 显存需求

| 模型 | 参数量 | 量化精度 | 显存需求 | 推荐硬件 |
|------|--------|---------|---------|---------|
| qwen2.5:7b | 7B | Q4 | 6-8GB | RTX 3060+ |
| qwen2.5:14b | 14B | Q4 | 12-16GB | RTX 4090 / A5000 |
| qwen-vl:7b | 7B | Q4 | 8-10GB | RTX 3060+ |
| nomic-embed-text | 137M | FP16 | 1GB | 任意 |

---

## 六、成本汇总对比

| 场景 | 方案 | 月成本 (1000任务) | 准确率 | 适用场景 |
|------|------|------------------|--------|---------|
| 个人学习 | Tier1 全本地 | ¥0 | 75% | 隐私/离线 |
| 内容创作者 | Tier1+Tier2 | ¥5 | 85% | 日常侵权检测 |
| 小企业 | Tier2 为主 | ¥50-200 | 88% | 商业使用 |
| 中企业 | Tier2+Tier3 | ¥200-500 | 92% | 专业检测 |
| 大企业 | Tier3 全云 | ¥1000+ | 95% | 最高准确率 |

---

## 七、快速启动命令

```bash
# ========== 一键安装 (零成本方案) ==========

# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 下载所需模型 (~15GB 总计)
ollama pull qwen2.5:7b
ollama pull qwen-vl:7b
ollama pull nomic-embed-text

# 3. 启动服务
ollama serve

# 4. 配置环境变量
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_TEXT_MODEL=qwen2.5:7b
export OLLAMA_VISION_MODEL=qwen-vl:7b

# 完成！零成本，AI 增强功能全部可用
```

```bash
# ========== 升级到低成本方案 ==========

# 1. 获取豆包 API Key (¥0.001/1K tokens)
# https://console.volcengine.com/ark

# 2. 配置
export DOUYIN_API_KEY=your-key
export DOUYIN_MODEL=doubao-pro-32k

# 3. (可选) 继续用本地 Embedding
export OLLAMA_EMBED_MODEL=nomic-embed-text

# 完成！月成本 ¥1-10
```

---

*文档版本: v1.0 | 最后更新: 2026-05-11*