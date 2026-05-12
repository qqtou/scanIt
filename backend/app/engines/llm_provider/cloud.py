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
import time
from io import BytesIO
from typing import Any

import httpx

from .base import BaseProvider, Capability, ProviderConfig

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 通用 HTTP 客户端工厂（统一超时和错误处理）
# ─────────────────────────────────────────────────────────────────────────────

async def _http_post(
    url: str,
    headers: dict,
    json_body: dict,
    timeout: int = 60,
) -> httpx.Response:
    """统一的 POST 请求封装

    所有云端 Provider 共用此函数发送 API 请求，统一处理：
    - 超时控制：默认 60s，避免 LLM 长请求无限挂起
    - 日志记录：请求 URL 和模型名
    - 异常分类：TimeoutException 和 RequestError 分别记录
    """
    model = json_body.get("model", "unknown")
    logger.debug(f"[HTTP-POST] {url} | model={model}")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, headers=headers, json=json_body)
    except httpx.TimeoutException:
        logger.warning(f"[HTTP-POST] Timeout | url={url} | model={model} | timeout={timeout}s")
        raise
    except httpx.RequestError as e:
        logger.warning(f"[HTTP-POST] RequestError | url={url} | model={model} | error={e}")
        raise


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
        """初始化: 验证 API Key 连通性"""
        if not self.config.api_key:
            logger.warning("[Douyin] No API key configured")
            return False
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                elapsed = time.monotonic() - start
                logger.info(
                    f"[Douyin] Init | status={r.status_code} "
                    f"elapsed={elapsed:.2f}s"
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
        """文本生成: 调用豆包 Chat Completions API"""
        model = self.config.model or self.DEFAULT_MODEL
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
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
            elapsed = time.monotonic() - start

            logger.info(
                f"[Douyin] generate_text | model={model} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Douyin] API error: {result['error']}")
                raise RuntimeError(f"Douyin API error: {result['error']}")

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            logger.info(
                f"[Douyin] Response | content_len={len(content)} "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} "
                f"completion_tokens={usage.get('completion_tokens', '?')}"
            )
            return content

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
        """初始化: 验证 API Key 连通性"""
        if not self.config.api_key:
            logger.warning("[Zhipu] No API key configured")
            return False
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                elapsed = time.monotonic() - start
                logger.info(
                    f"[Zhipu] Init | status={r.status_code} elapsed={elapsed:.2f}s"
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
        """文本生成: 调用智谱 Chat Completions API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                },
            )
            elapsed = time.monotonic() - start

            logger.info(
                f"[Zhipu] generate_text | model={model} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Zhipu] API error: {result['error']}")
                raise RuntimeError(f"Zhipu API error: {result['error']}")

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            logger.info(
                f"[Zhipu] Response | content_len={len(content)} "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} "
                f"completion_tokens={usage.get('completion_tokens', '?')}"
            )
            return content

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """图片理解: 调用 GLM-4V"""
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

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.DEFAULT_VISION_MODEL,
                    "messages": messages,
                },
            )
            elapsed = time.monotonic() - start

            logger.info(
                f"[Zhipu] understand_image | model={self.DEFAULT_VISION_MODEL} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Zhipu] Vision API error: {result['error']}")
                raise RuntimeError(f"Zhipu Vision API error: {result['error']}")

            content = result["choices"][0]["message"]["content"]
            parsed = self._parse_response(content)
            logger.info(
                f"[Zhipu] Vision response | parsed_keys={list(parsed.keys())} "
                f"elapsed={elapsed:.2f}s"
            )
            return parsed

    def _prepare_image_data(self, image_url: str | bytes) -> str:
        if isinstance(image_url, str):
            return image_url
        else:
            b64 = base64.b64encode(image_url).decode()
            return f"data:image/jpeg;base64,{b64}"

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 返回内容，支持 JSON / 代码块 / 纯文本"""
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
        """初始化: 验证 API Key 连通性"""
        if not self.config.api_key:
            logger.warning("[Kimi] No API key configured")
            return False
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                elapsed = time.monotonic() - start
                logger.info(
                    f"[Kimi] Init | status={r.status_code} elapsed={elapsed:.2f}s"
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
        """文本生成: 调用 Kimi Chat Completions API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            elapsed = time.monotonic() - start

            logger.info(
                f"[Kimi] generate_text | model={model} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Kimi] API error: {result['error']}")
                raise RuntimeError(f"Kimi API error: {result['error']}")

            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            logger.info(
                f"[Kimi] Response | content_len={len(content)} "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} "
                f"completion_tokens={usage.get('completion_tokens', '?')}"
            )
            return content

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
        """初始化: 验证 API Key 连通性"""
        if not self.config.api_key:
            logger.warning("[Aliyun] No API key configured")
            return False
        try:
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/services",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                elapsed = time.monotonic() - start
                logger.info(
                    f"[Aliyun] Init | status={r.status_code} elapsed={elapsed:.2f}s"
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
        """文本生成: 调用通义千问 API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = self.config.model or self.DEFAULT_TEXT_MODEL
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": {"messages": messages},
                },
            )
            elapsed = time.monotonic() - start

            logger.info(
                f"[Aliyun] generate_text | model={model} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Aliyun] API error: {result['error']}")
                raise RuntimeError(f"Aliyun API error: {result['error']}")

            content = result["output"]["text"]
            usage = result.get("usage", {})
            logger.info(
                f"[Aliyun] Response | content_len={len(content)} "
                f"elapsed={elapsed:.2f}s"
            )
            return content

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """图片理解: 调用 qwen-vl-max"""
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

        start = time.monotonic()
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
            elapsed = time.monotonic() - start

            logger.info(
                f"[Aliyun] understand_image | model={self.DEFAULT_VISION_MODEL} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s status={response.status_code}"
            )

            result = response.json()
            if "error" in result:
                logger.warning(f"[Aliyun] Vision API error: {result['error']}")
                raise RuntimeError(f"Aliyun Vision API error: {result['error']}")

            content = result["output"]["choices"][0]["message"]["content"]
            parsed = self._parse_response(content)
            logger.info(
                f"[Aliyun] Vision response | parsed_keys={list(parsed.keys())} "
                f"elapsed={elapsed:.2f}s"
            )
            return parsed

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
    OpenAI API (Tier 3 企业级)

    支持: GPT-4o (文本+图片+多模态)、Embedding
    """

    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._openai = None

    async def initialize(self) -> bool:
        """初始化: 验证 API Key 并创建客户端"""
        if not self.config.api_key:
            logger.warning("[OpenAI] No API key configured")
            return False
        try:
            import openai

            self._openai = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                elapsed = time.monotonic() - start
                logger.info(
                    f"[OpenAI] Init | status={r.status_code} elapsed={elapsed:.2f}s"
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
        """文本生成: 调用 OpenAI Chat Completions API"""
        import openai

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()

        try:
            response = await self._openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = time.monotonic() - start

            logger.info(
                f"[OpenAI] generate_text | model={model} "
                f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s"
            )

            content = response.choices[0].message.content
            usage = response.usage
            logger.info(
                f"[OpenAI] Response | content_len={len(content)} "
                f"prompt_tokens={usage.prompt_tokens if usage else '?'} "
                f"completion_tokens={usage.completion_tokens if usage else '?'}"
            )
            return content

        except openai.RateLimitError as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[OpenAI] RateLimit | model={model} "
                f"elapsed={elapsed:.2f}s error={e}"
            )
            raise
        except openai.APIError as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[OpenAI] APIError | model={model} "
                f"elapsed={elapsed:.2f}s error={e}"
            )
            raise

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """图片理解: 调用 GPT-4o Vision"""
        import openai

        if isinstance(image_url, bytes):
            b64 = base64.b64encode(image_url).decode()
            image_data = f"data:image/jpeg;base64,{b64}"
        else:
            image_data = image_url

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()

        response = await self._openai.chat.completions.create(
            model=model,
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
        elapsed = time.monotonic() - start

        logger.info(
            f"[OpenAI] understand_image | model={model} "
            f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s"
        )

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
            logger.info(
                f"[OpenAI] Vision response | parsed_keys={list(parsed.keys())} "
                f"elapsed={elapsed:.2f}s"
            )
            return parsed
        except json.JSONDecodeError:
            return {"raw_response": content}

    async def embed_text(self, text: str) -> list[float]:
        """文本向量化: 调用 OpenAI Embeddings API"""
        import openai

        model = (
            self.config.model.replace("gpt", "text-embedding")
            if "gpt" in self.config.model
            else "text-embedding-3-large"
        )
        start = time.monotonic()

        response = await self._openai.embeddings.create(
            model=model,
            input=text,
        )
        elapsed = time.monotonic() - start

        logger.info(
            f"[OpenAI] embed_text | model={model} "
            f"text_len={len(text)} elapsed={elapsed:.2f}s"
        )

        return response.data[0].embedding


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude API (Tier 3 企业级)

    支持: Claude 3.5 Sonnet (文本+图片+多模态)
    优势: 200K 超长上下文，分析深度强
    """

    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._anthropic = None

    async def initialize(self) -> bool:
        """初始化: 验证 API Key 并创建客户端"""
        if not self.config.api_key:
            logger.warning("[Anthropic] No API key configured")
            return False
        try:
            import anthropic

            self._anthropic = anthropic.AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
            self._initialized = True
            logger.info("[Anthropic] Init OK | client created")
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
        """文本生成: 调用 Claude Messages API"""
        import anthropic

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()

        response = await self._anthropic.messages.create(
            model=model,
            max_tokens=max_tokens or self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.monotonic() - start

        logger.info(
            f"[Anthropic] generate_text | model={model} "
            f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s"
        )

        content = response.content[0].text
        usage = response.usage
        logger.info(
            f"[Anthropic] Response | content_len={len(content)} "
            f"input_tokens={usage.input_tokens if usage else '?'} "
            f"output_tokens={usage.output_tokens if usage else '?'}"
        )
        return content

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        **kwargs,
    ) -> dict:
        """图片理解: 调用 Claude Vision"""
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

        model = self.config.model or self.DEFAULT_MODEL
        start = time.monotonic()

        response = await self._anthropic.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [media, {"type": "text", "text": prompt}],
                }
            ],
        )
        elapsed = time.monotonic() - start

        logger.info(
            f"[Anthropic] understand_image | model={model} "
            f"prompt_len={len(prompt)} elapsed={elapsed:.2f}s"
        )

        content = response.content[0].text
        try:
            parsed = json.loads(content)
            logger.info(
                f"[Anthropic] Vision response | parsed_keys={list(parsed.keys())} "
                f"elapsed={elapsed:.2f}s"
            )
            return parsed
        except json.JSONDecodeError:
            return {"raw_response": content}
