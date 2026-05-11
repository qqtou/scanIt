"""
Ollama 本地推理 Provider

通过 Ollama 统一接口访问本地大模型：
- 文本生成: qwen2.5:7b, qwen2.5:14b, glm4:9b, llama3.2
- 图片理解: qwen-vl:7b, llava:7b
- 向量嵌入: nomic-embed-text, bge-large

安装: https://ollama.com
"""

import base64
import logging
from io import BytesIO
from typing import Any

import httpx
from PIL import Image

from .base import BaseProvider, Capability, ProviderConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """
    Ollama 本地推理 Provider

    通过 Ollama REST API 访问本地模型，支持文本生成、图片理解和向量嵌入。

    环境变量:
        OLLAMA_BASE_URL: Ollama 服务地址 (默认 http://localhost:11434)
        OLLAMA_TEXT_MODEL: 文本模型 (默认 qwen2.5:7b)
        OLLAMA_VISION_MODEL: Vision 模型 (默认 qwen-vl:7b)
        OLLAMA_EMBED_MODEL: Embedding 模型 (默认 nomic-embed-text)
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TEXT_MODEL = "qwen2.5:7b"
    DEFAULT_VISION_MODEL = "qwen-vl:7b"
    DEFAULT_EMBED_MODEL = "nomic-embed-text"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = self.config.base_url or self.DEFAULT_BASE_URL
        self._client: httpx.AsyncClient | None = None
        # 模型映射
        self._text_model = self.config.model or self.DEFAULT_TEXT_MODEL
        self._vision_model = self.DEFAULT_VISION_MODEL
        self._embed_model = self.DEFAULT_EMBED_MODEL

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.config.timeout or 120),
            )
        return self._client

    async def initialize(self) -> bool:
        """检测 Ollama 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    logger.info(
                        f"[Ollama] Connected. Available models: {model_names}"
                    )
                    # 记录实际可用的模型
                    self._available_models = model_names
                    self._initialized = True
                    return True
        except httpx.ConnectError:
            logger.debug(f"[Ollama] Not running at {self.base_url}")
        except Exception as e:
            logger.warning(f"[Ollama] Init failed: {e}")
        self._initialized = False
        return False

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.client.get("/")
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────
    # 文本生成
    # ──────────────────────────────────────────────────────────

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        model: str | None = None,
        **kwargs,
    ) -> str:
        """
        调用本地模型生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 随机性 (0.0-2.0)
            max_tokens: 最大输出 token
            model: 指定模型 (默认用 text_model)
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model_name = model or self._text_model
        max_tokens = max_tokens or self.config.max_tokens

        response = await self.client.post(
            "/api/chat",
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        result = response.json()
        return result["message"]["content"]

    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        **kwargs,
    ):
        """流式文本生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with self.client.stream(
            "POST",
            "/api/chat",
            json={
                "model": self._text_model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature},
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    data = response.__class__.model_validate_json(line) if hasattr(response.__class__, 'model_validate_json') else None
                    # 简单解析
                    import json
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        pass

    # ──────────────────────────────────────────────────────────
    # 图片理解
    # ──────────────────────────────────────────────────────────

    async def understand_image(
        self,
        image_url: str | bytes,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> dict:
        """
        使用 Vision 模型理解图片

        Args:
            image_url: 图片 URL 或字节数据
            prompt: 提问
            model: 指定模型 (默认用 vision_model)
        """
        model_name = model or self._vision_model
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

        response = await self.client.post(
            "/api/chat",
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
            },
        )
        result = response.json()
        content = result["message"]["content"]

        return self._parse_response(content)

    def _prepare_image_data(self, image_url: str | bytes) -> str:
        """将图片数据转换为 Ollama API 格式"""
        if isinstance(image_url, str):
            # URL 格式，直接使用（需可访问）
            return image_url
        else:
            # bytes → base64
            b64 = base64.b64encode(image_url).decode()
            # 检测图片格式
            try:
                img = Image.open(BytesIO(image_url))
                media_type = f"image/{img.format.lower()}"
            except Exception:
                media_type = "image/jpeg"
            return f"data:{media_type};base64,{b64}"

    def _parse_response(self, content: str) -> dict:
        """尝试解析 JSON 响应"""
        import json

        content = content.strip()
        # 处理 markdown 代码块
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
                # 去掉第一行的 json 标记
                lines = content.split("\n")
                if lines and lines[0].strip() in ("json",):
                    content = "\n".join(lines[1:])

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}

    # ──────────────────────────────────────────────────────────
    # 向量嵌入
    # ──────────────────────────────────────────────────────────

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """
        使用 Embedding 模型向量化文本

        Args:
            text: 待向量化的文本
            model: 指定模型 (默认用 embed_model)
        """
        model_name = model or self._embed_model

        response = await self.client.post(
            "/api/embeddings",
            json={
                "model": model_name,
                "prompt": text,
            },
        )
        result = response.json()
        return result["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化"""
        model_name = self._embed_model

        async def embed_one(text: str) -> list[float]:
            response = await self.client.post(
                "/api/embeddings",
                json={"model": model_name, "prompt": text},
            )
            return response.json()["embedding"]

        import asyncio
        results = await asyncio.gather(*[embed_one(t) for t in texts])
        return list(results)

    # ──────────────────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────────────────

    def get_model_info(self) -> dict:
        info = super().get_model_info()
        info.update(
            {
                "base_url": self.base_url,
                "text_model": self._text_model,
                "vision_model": self._vision_model,
                "embed_model": self._embed_model,
            }
        )
        return info

    async def close(self):
        """关闭客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
