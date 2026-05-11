"""
云端 AI Provider 实现

Tier 2 (低成本):
    - DouyinProvider: 字节豆包 ¥0.001/K tokens
    - ZhipuProvider: 智谱 GLM-4 ¥0.01/K tokens
    - KimiProvider: 月之暗面 ¥0.01/K tokens

Tier 3 (企业级):
    - AliyunProvider: 阿里通义千问 ¥0.02/K tokens
    - OpenAIProvider: OpenAI GPT-4o
    - AnthropicProvider: Claude
"""

import base64
import json
import logging
from io import BytesIO
from typing import Any

import httpx

from .base import BaseProvider, Capability, ProviderConfig

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tier 2: 低成本云
# ─────────────────────────────────────────────────────────────────────────────


class DouyinProvider(BaseProvider):
    """
    字节跳动豆包 API

    文档: https://www.volcengine.com/docs/82379/1263482
    定价: ¥0.001 / 1K tokens (doubao-pro-32k) ≈ $0.00014
    优势: 成本最低，中文优化
    """

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DEFAULT_MODEL = "doubao-pro-32k"

    async def initialize(self) -> bool:
        if not self.config.api_key:
            logger.warning("[Douyin] No API key configured")
            return False
        # 简单的连通性检查
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if r.status_code in (200, 401):
                    self._initialized = True
                    return True
        except Exception as e:
            logger.warning(f"[Douyin] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        model = self.config.model or self.DEFAULT_MODEL
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens or self.config.max_tokens,
                },
            )
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Douyin API error: {result['error']}")
            return result["choices"][0]["message"]["content"]

    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError(
            f"{self.name} does not support embedding. "
            "Use a local Ollama embedding model or switch to Zhipu/OpenAI."
        )

    async def understand_image(
        self, image_url: str | bytes, prompt: str, **kwargs
    ) -> dict:
        raise NotImplementedError(
            f"{self.name} does not support image understanding. "
            "Use Zhipu (glm-4v) or Aliyun (qwen-vl-max)."
        )


class ZhipuProvider(BaseProvider):
    """
    智谱 GLM-4 API

    文档: https://open.bigmodel.cn/dev/api
    定价: ¥0.01 / 1K tokens (glm-4)
    优势: 同时支持文本和图片理解 (glm-4v)
    """

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "glm-4"
    DEFAULT_VISION_MODEL = "glm-4v"

    async def initialize(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if r.status_code in (200, 401):
                    self._initialized = True
                    return True
        except Exception as e:
            logger.warning(f"[Zhipu] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.config.model or self.DEFAULT_MODEL,
                    "messages": messages,
                },
            )
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Zhipu API error: {result['error']}")
            return result["choices"][0]["message"]["content"]

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """智谱图片理解 (GLM-4V)"""
        image_data = self._prepare_image_data(image_url)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.DEFAULT_VISION_MODEL,
                    "messages": messages,
                },
            )
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._parse_response(content)

    def _prepare_image_data(self, image_url: str | bytes) -> str:
        if isinstance(image_url, str):
            return image_url
        else:
            b64 = base64.b64encode(image_url).decode()
            return f"data:image/jpeg;base64,{b64}"

    def _parse_response(self, content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
                lines = content.split("\n")
                if lines and lines[0].strip() in ("json",):
                    content = "\n".join(lines[1:])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}

    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError(
            f"{self.name} does not support embedding. "
            "Use a local Ollama embedding model or switch to OpenAI."
        )


class KimiProvider(BaseProvider):
    """
    月之暗面 Kimi API

    文档: https://platform.moonshot.cn/docs
    定价: ¥0.01 / 1K tokens
    优势: 128K 超长上下文，适合长文本分析
    """

    BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_MODEL = "moonshot-v1-128k"

    async def initialize(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if r.status_code in (200, 401):
                    self._initialized = True
                    return True
        except Exception as e:
            logger.warning(f"[Kimi] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.config.model or self.DEFAULT_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Kimi API error: {result['error']}")
            return result["choices"][0]["message"]["content"]

    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError(
            f"{self.name} does not support embedding. "
            "Use a local Ollama embedding model or switch to Zhipu/OpenAI."
        )

    async def understand_image(
        self, image_url: str | bytes, prompt: str, **kwargs
    ) -> dict:
        raise NotImplementedError(
            f"{self.name} does not support image understanding. "
            "Use Zhipu (glm-4v) or Aliyun (qwen-vl-max)."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3: 企业级
# ─────────────────────────────────────────────────────────────────────────────


class AliyunProvider(BaseProvider):
    """
    阿里云通义千问 API

    文档: https://help.aliyun.com/zh/model-studio
    定价: ¥0.02 / 1K tokens
    优势: qwen-vl-max 图片理解强，支持多模态
    """

    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    DEFAULT_TEXT_MODEL = "qwen-max"
    DEFAULT_VISION_MODEL = "qwen-vl-max"

    async def initialize(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/services",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if r.status_code in (200, 401):
                    self._initialized = True
                    return True
        except Exception as e:
            logger.warning(f"[Aliyun] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model or self.DEFAULT_TEXT_MODEL,
                    "input": {"messages": messages},
                },
            )
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Aliyun API error: {result['error']}")
            return result["output"]["text"]

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """通义千问图片理解"""
        image_data = self._prepare_image_data(image_url)
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_data},
                    {"text": prompt},
                ],
            }
        ]

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.DEFAULT_VISION_MODEL,
                    "input": {"messages": messages},
                },
            )
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Aliyun Vision API error: {result['error']}")
            content = result["output"]["choices"][0]["message"]["content"]
            return self._parse_response(content)

    def _prepare_image_data(self, image_url: str | bytes) -> str:
        if isinstance(image_url, str):
            return image_url
        else:
            b64 = base64.b64encode(image_url).decode()
            return f"data:image/jpeg;base64,{b64}"

    def _parse_response(self, content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
                lines = content.split("\n")
                if lines and lines[0].strip() in ("json",):
                    content = "\n".join(lines[1:])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}


class OpenAIProvider(BaseProvider):
    """
    OpenAI API (Tier 3 企业级备选)
    """

    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            import openai

            self._openai = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
            # 简单验证
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if r.status_code in (200, 401):
                    self._initialized = True
                    return True
        except ImportError:
            logger.warning("[OpenAI] openai package not installed")
        except Exception as e:
            logger.warning(f"[OpenAI] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        import openai

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._openai.chat.completions.create(
            model=self.config.model or self.DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        if isinstance(image_url, bytes):
            b64 = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64}"
        else:
            image_data = image_url

        import openai

        response = await self._openai.chat.completions.create(
            model=self.config.model or self.DEFAULT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            max_tokens=1024,
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}

    async def embed_text(self, text: str) -> list[float]:
        import openai

        response = await self._openai.embeddings.create(
            model=self.config.model.replace("gpt", "text-embedding")
            if "gpt" in self.config.model
            else "text-embedding-3-large",
            input=text,
        )
        return response.data[0].embedding


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude (Tier 3 企业级)
    """

    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            import anthropic

            self._anthropic = anthropic.AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
            self._initialized = True
            return True
        except ImportError:
            logger.warning("[Anthropic] anthropic package not installed")
        except Exception as e:
            logger.warning(f"[Anthropic] Init failed: {e}")
        return False

    async def health_check(self) -> bool:
        return self._initialized

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        import anthropic

        response = await self._anthropic.messages.create(
            model=self.config.model or self.DEFAULT_MODEL,
            max_tokens=max_tokens or self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        import anthropic

        if isinstance(image_url, bytes):
            b64 = base64.b64encode(image_url).decode()
            media = {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            }
        else:
            media = {"type": "url", "source": {"type": "url", "url": image_url}}

        response = await self._anthropic.messages.create(
            model=self.config.model or self.DEFAULT_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [media, {"type": "text", "text": prompt}],
                }
            ],
        )
        content = response.content[0].text
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}
