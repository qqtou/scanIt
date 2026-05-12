"""
LLM 增强版侵权检测服务

基于 DetectionService，整合 AI Provider 分层能力：

LLM 增强功能:
1. 智能关键词生成 (LLM 生成高质量搜索词)
2. 图片深度理解 (Vision LLM 分析图片内容)
3. 侵权报告生成 (LLM 生成专业检测报告)
4. 语义相似度分析 (Embedding 向量化语义匹配)

使用方式:
    detector = LLMDetectionService()

    # 使用 LLM 生成关键词
    keywords = await detector.generate_keywords_llm(content, content_type)

    # 使用 Vision LLM 分析图片
    analysis = await detector.analyze_image_llm(image_bytes, prompt)

    # 生成侵权报告
    report = await detector.generate_report(detection_results, content_info)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Union

from app.engines.detector import DetectionResult, DetectionService
from app.engines.llm_provider import (
    Capability,
    ProviderManager,
    get_embed_provider,
    get_manager,
    get_text_provider,
    get_vision_provider,
)
from app.engines.llm_provider.base import BaseProvider, ProviderTier

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 系统提示词
# ─────────────────────────────────────────────────────────────────────────────

KEYWORD_GENERATION_PROMPT = """你是一个专业的版权检测专家，擅长从作品中提取最具侵权检索价值的关键词。

任务：根据以下{content_type}内容，生成 5-10 个高效的搜索关键词，用于在搜索引擎中查找疑似侵权内容。

要求：
1. 关键词应独特、有辨识度，避免过于通用的词
2. 优先选择：作品名称、人名、独特口号、版权标识语
3. 兼顾品牌词 + 内容特征词的组合
4. 中英文混合或纯英文关键词有时效果更好
5. 只输出关键词列表，每行一个，不要解释

输出格式：
```json
[
  "关键词1",
  "关键词2",
  ...
]
```

{content_type}内容：
{content}
"""


IMAGE_ANALYSIS_PROMPT = """你是一个专业的图片版权分析专家。

任务：分析这张图片，提取可用于侵权检测的关键信息。

请从以下维度分析：
1. **图片内容**：描述图片的主要内容、主题、场景
2. **文字信息**：图片中的文字（logo、文字水印、标语等）
3. **版权标识**：版权声明、来源水印、平台标识（如有）
4. **品牌元素**：商标、品牌名称、人物面孔
5. **侵权风险点**：最容易被盗用的元素

输出格式（JSON）：
```json
{{
  "description": "图片内容描述",
  "texts": ["文字1", "文字2"],
  "copyright_marks": ["版权标识1"],
  "brands": ["品牌1"],
  "risk_elements": ["风险点1"],
  "search_keywords": ["建议搜索词1"],
  "infringement_likelihood": "high/medium/low",
  "notes": "补充说明"
}}
```
"""


VIDEO_KEYFRAME_ANALYSIS_PROMPT = """你是一个专业的视频版权分析专家。

任务：分析这段视频截帧，识别关键画面。

请从以下维度分析：
1. **场景识别**：这是什么类型的视频（宣传片、教程、影视片段等）
2. **核心内容**：视频的核心画面是什么
3. **独特元素**：哪些画面具有独特性，可能被侵权
4. **文字信息**：画面中的文字内容
5. **侵权风险评估**：整体侵权风险等级

输出格式（JSON）：
```json
{{
  "scene_type": "场景类型",
  "core_content": "核心内容",
  "unique_elements": ["独特元素1"],
  "texts": ["文字1"],
  "risk_level": "high/medium/low",
  "risk_reason": "风险原因",
  "search_keywords": ["搜索关键词"]
}}
```
"""


REPORT_GENERATION_PROMPT = """你是一个专业的版权侵权检测报告撰写专家。

任务：根据以下检测结果，撰写一份专业、客观的侵权检测报告。

检测信息：
- 被检测作品类型：{content_type}
- 检测时间：{detection_time}
- 使用的搜索引擎：{engines}
- 关键词：{keywords}
- 检测到的疑似侵权结果数：{result_count}

检测结果详情：
{results_detail}

请撰写报告，包含：
1. **检测概述**：简要说明检测的背景和范围
2. **检测结果统计**：高/中/低风险数量
3. **高风险侵权详情**：逐一描述每个高风险结果，包括：
   - 来源平台和 URL
   - 侵权类型判定
   - 相似度依据
   - 建议处置方式
4. **证据保全建议**：截图、录屏、公证等建议
5. **下一步行动建议**：投诉渠道、律师函、平台申诉等

报告要求：
- 语言专业、客观
- 数据准确、引用清晰
- 建议具体可操作
- 总字数控制在 500-1500 字

输出格式：纯文本报告，直接输出，不要 markdown 代码块包裹。
"""


# ─────────────────────────────────────────────────────────────────────────────
# LLM 增强检测服务
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class LLMDetectionConfig:
    """LLM 检测配置"""

    # 关键词生成
    keyword_llm_enabled: bool = True  # 是否用 LLM 生成关键词
    keyword_llm_tier: ProviderTier = ProviderTier.TIER_1_LOCAL  # 关键词生成的 Tier
    keyword_count: int = 8  # 生成关键词数量

    # 图片分析
    image_analysis_enabled: bool = True  # 是否用 Vision LLM 分析图片
    image_analysis_tier: ProviderTier = ProviderTier.TIER_1_LOCAL  # Vision 的 Tier

    # 报告生成
    report_enabled: bool = True  # 是否生成报告
    report_tier: ProviderTier = ProviderTier.TIER_2_BUDGET  # 报告生成的 Tier

    # 向量化搜索（备选）
    embedding_enabled: bool = True  # 是否启用语义向量化


class LLMDetectionService:
    """
    LLM 增强版侵权检测服务

    继承 DetectionService 全部能力，额外提供：
    - LLM 生成关键词（比规则提取更智能）
    - Vision LLM 图片分析（深度理解图片内容）
    - LLM 生成专业侵权报告
    - Embedding 语义相似度（补充传统比对）

    用法:
        detector = LLMDetectionService()

        # 关键词生成（自动 Tier）
        keywords = await detector.generate_keywords_llm(content, "image")

        # 指定 Tier
        keywords = await detector.generate_keywords_llm(content, "text", tier="tier2_budget")

        # 图片分析
        analysis = await detector.analyze_image_llm(image_bytes)

        # 生成报告
        report = await detector.generate_report(detection_results, content_info)
    """

    def __init__(self, config: LLMDetectionConfig | None = None):
        # 复用 DetectionService 的搜索引擎和比对器
        self._base = DetectionService()

        # LLM 配置
        self.config = config or LLMDetectionConfig()

        # Provider 管理器
        self._manager: ProviderManager | None = None

        # 缓存最近使用的 Provider（避免频繁切换）
        # 格式: capability_tier -> provider
        self._provider_cache: dict[str, BaseProvider | None] = {}

        # 当前使用的 Provider 名称（用于日志）
        self._llm_provider_name: str | None = None
        self._llm_provider_tier: str | None = None

        logger.debug(f"[LLMDetection] Service initialized | config={self.config}")

    # ─────────────────────────────────────────────────────────────────────────
    # 初始化
    # ─────────────────────────────────────────────────────────────────────────

    def _get_manager(self) -> ProviderManager:
        if self._manager is None:
            self._manager = get_manager()
        return self._manager

    def _get_provider(
        self,
        capability: Capability,
        tier: ProviderTier | str | None = None,
    ) -> BaseProvider | None:
        """获取 Provider（带缓存，避免每次调用都重新查找）"""
        tier_str = tier.value if isinstance(tier, ProviderTier) else (tier or "auto")
        cache_key = f"{capability.value}_{tier_str}"

        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

        manager = self._get_manager()
        provider = manager.get_provider(capability, tier) if tier else manager.get_provider(capability)

        # 记录当前使用的 Provider（用于日志）
        if provider:
            self._llm_provider_name = provider.name
            self._llm_provider_tier = provider.tier.value

        self._provider_cache[cache_key] = provider
        return provider

    # ─────────────────────────────────────────────────────────────────────────
    # LLM 关键词生成
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_keywords_llm(
        self,
        content: str,
        content_type: str,
        num_keywords: int | None = None,
        tier: ProviderTier | str | None = None,
    ) -> list[str]:
        """
        使用 LLM 生成侵权检测关键词

        比传统规则提取更智能，能识别：
        - 图片中的文字、logo、品牌
        - 视频的标题、口号、人物
        - 文本的核心概念和独特表述

        Args:
            content: 内容（文本、URL 或描述）
            content_type: 内容类型 (text, image, video)
            num_keywords: 关键词数量（默认 8 个）
            tier: 强制使用的 Tier（默认按配置）

        Returns:
            list[str]: 关键词列表
        """
        tier = tier or self.config.keyword_llm_tier
        num = num_keywords or self.config.keyword_count
        start = time.monotonic()

        logger.info(
            f"[LLM-Detect] generate_keywords_llm | type={content_type} "
            f"tier={tier.value if isinstance(tier, ProviderTier) else tier}"
        )

        provider = self._get_provider(Capability.TEXT_GENERATION, tier)
        if not provider:
            logger.warning(
                f"[LLM-Detect] No text provider for keyword generation, "
                f"falling back to rule-based"
            )
            return self._base.generate_keywords(content, content_type, num)

        content_type_display = {
            "text": "文本",
            "image": "图片",
            "video": "视频",
        }.get(content_type, content_type)

        prompt = KEYWORD_GENERATION_PROMPT.format(
            content_type=content_type_display,
            content=content[:2000],  # 截断：大多数 LLM 单次输入上限 ~4k token，2000 字符约占 1k token，留余量给 prompt 模板
        )

        try:
            result = await provider.generate_text(
                prompt=prompt,
                system_prompt="你是一个专业的版权检测关键词生成助手，只输出 JSON 数组，不要任何解释。",
                temperature=0.3,
                max_tokens=512,
            )

            elapsed = time.monotonic() - start
            keywords = self._parse_json_list(result)
            if keywords:
                logger.info(
                    f"[LLM-Detect] Keywords generated | provider={provider.name} "
                    f"count={len(keywords)} elapsed={elapsed:.2f}s"
                )
                return keywords[:num]
            else:
                logger.warning(
                    f"[LLM-Detect] Keyword parsing failed, falling back to rules | "
                    f"provider={provider.name} elapsed={elapsed:.2f}s"
                )

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[LLM-Detect] Keyword generation failed: {e} | "
                f"provider={provider.name} elapsed={elapsed:.2f}s, "
                f"falling back to rule-based"
            )

        # 降级：使用规则提取
        return self._base.generate_keywords(content, content_type, num)

    def _parse_json_list(self, text: str) -> list[str]:
        """从 LLM 输出中解析 JSON 列表，处理各种格式变体

        LLM 输出不稳定，可能返回以下任一格式：
        1. ```json ["a", "b"] ``` — markdown 代码块包裹
        2. ["a", "b"] — 直接 JSON
        3. "a" "b" — 纯引号包裹（最差情况）

        按优先级逐级降级解析，确保总能提取出关键词。
        """
        text = text.strip()

        # 策略 1：提取 ```json ``` 包裹的代码块
        if "```json" in text:
            parts = text.split("```json")
            if len(parts) >= 2:
                text = parts[1].split("```")[0]
        elif "```" in text:
            # 无语言标记的代码块（LLM 有时不加 json 标记）
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]

        text = text.strip()

        # 策略 2：尝试直接 JSON 解析
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

        # 策略 3：正则兜底 — 提取所有双引号中的字符串（LLM 输出格式混乱时的最后手段）
        import re
        matches = re.findall(r'"([^"]+)"', text)
        if matches:
            return matches

        return []

    # ─────────────────────────────────────────────────────────────────────────
    # Vision LLM 图片分析
    # ─────────────────────────────────────────────────────────────────────────

    async def analyze_image_llm(
        self,
        image: str | bytes,
        prompt: str | None = None,
        tier: ProviderTier | str | None = None,
    ) -> dict[str, Any]:
        """
        使用 Vision LLM 分析图片

        提供比传统 pHash/CNN 更深层的理解：
        - 识别图片中的文字内容（logo、水印、标语）
        - 理解场景和上下文
        - 判断侵权类型和风险

        Args:
            image: 图片 URL 或字节数据
            prompt: 自定义提问（默认用系统提示词）
            tier: 使用的 Tier

        Returns:
            dict: 解析后的分析结果
        """
        tier = tier or self.config.image_analysis_tier
        start = time.monotonic()

        logger.info(
            f"[LLM-Detect] analyze_image_llm | tier="
            f"{tier.value if isinstance(tier, ProviderTier) else tier}"
        )

        provider = self._get_provider(Capability.IMAGE_UNDERSTANDING, tier)
        if not provider:
            logger.warning("[LLM-Detect] No vision provider available for image analysis")
            return {"error": "No vision provider available"}

        try:
            result = await provider.understand_image(
                image_url=image,
                prompt=prompt or IMAGE_ANALYSIS_PROMPT,
            )

            elapsed = time.monotonic() - start
            logger.info(
                f"[LLM-Detect] Image analyzed | provider={provider.name} "
                f"elapsed={elapsed:.2f}s"
            )
            return result

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[LLM-Detect] Image analysis failed: {e} | "
                f"provider={provider.name} elapsed={elapsed:.2f}s"
            )
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Embedding 语义相似度
    # ─────────────────────────────────────────────────────────────────────────

    async def compute_similarity_embedding(
        self,
        text1: str,
        text2: str,
        tier: ProviderTier | str | None = None,
    ) -> float:
        """
        使用 Embedding 计算语义相似度

        补充传统 SimHash 的能力：
        - 能识别同义不同词的侵权（如改写文章）
        - 语义层面的深度匹配

        Args:
            text1: 文本1
            text2: 文本2
            tier: 使用的 Tier

        Returns:
            float: 相似度分数 0.0-1.0
        """
        start = time.monotonic()
        logger.info(f"[LLM-Detect] compute_similarity_embedding | tier={tier}")

        provider = self._get_provider(Capability.EMBEDDING, tier)
        if not provider:
            logger.warning("[LLM-Detect] No embedding provider available")
            return 0.0

        try:
            import numpy as np  # lazy import：numpy 体积大且仅此方法使用，避免启动时加载拖慢服务

            vec1 = await provider.embed_text(text1)
            vec2 = await provider.embed_text(text2)

            # 余弦相似度：衡量两个向量在方向上的接近程度，范围 [-1, 1]，1 = 完全相同
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            elapsed = time.monotonic() - start
            logger.info(
                f"[LLM-Detect] Embedding similarity | provider={provider.name} "
                f"score={similarity:.4f} elapsed={elapsed:.2f}s"
            )
            return float(similarity)

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[LLM-Detect] Embedding similarity failed: {e} | "
                f"elapsed={elapsed:.2f}s"
            )
            return 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # 侵权报告生成
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_report(
        self,
        content: str,
        content_type: str,
        results: Union[list[DetectionResult], list[dict]],
        keywords: list[str] | None = None,
        engines: list[str] | None = None,
        tier: ProviderTier | str | None = None,
    ) -> str:
        """
        使用 LLM 生成侵权检测报告

        支持两种结果格式：
        - list[DetectionResult]: 直接传入检测结果对象
        - list[dict]: API 传入的字典列表（需从 dict 中提取字段）

        Args:
            content: 被检测内容
            content_type: 内容类型
            results: 检测结果列表
            keywords: 使用的关键词（默认取前5个）
            engines: 使用的搜索引擎
            tier: 使用的 Tier

        Returns:
            str: 生成的报告文本
        """
        tier = tier or self.config.report_tier
        start = time.monotonic()

        logger.info(
            f"[LLM-Detect] generate_report | type={content_type} "
            f"results={len(results)} tier="
            f"{tier.value if isinstance(tier, ProviderTier) else tier}"
        )

        provider = self._get_provider(Capability.TEXT_GENERATION, tier)
        if not provider:
            logger.warning(
                f"[LLM-Detect] No text provider for report, using fallback"
            )
            return self._generate_fallback_report(results, content_type)

        from datetime import datetime

        # 统计风险分布
        # 同时支持两种格式：API 层传入 list[dict]，内部调用传入 list[DetectionResult]
        # 原因：/llm/detect 端点将 DetectionResult 序列化为 dict 后传给此方法，
        # 而 detect_with_keywords 可直接传 DetectionResult 对象
        high_count = medium_count = low_count = 0
        for r in results:
            # 同时支持 DetectionResult 对象和 dict
            risk = r.risk_level if hasattr(r, "risk_level") else r.get("risk_level", "low")
            if risk == "high":
                high_count += 1
            elif risk == "medium":
                medium_count += 1
            else:
                low_count += 1

        # 构建结果详情文本（同时支持 DetectionResult 和 dict）
        results_detail = []
        for i, r in enumerate(results[:10]):  # 最多 10 条
            if isinstance(r, dict):
                title = r.get("title", "N/A")
                url = r.get("url", "N/A")
                domain = r.get("domain") or self._extract_domain(url)
                similarity = r.get("similarity_score", 0.0)
                risk = r.get("risk_level", "low")
                engine = r.get("search_engine", "unknown")
                keyword = r.get("search_keyword", keywords[0] if keywords else "N/A")
            else:
                title = getattr(r, "title", "N/A")
                url = getattr(r, "url", "N/A")
                domain = getattr(r, "domain") or self._extract_domain(url)
                similarity = getattr(r, "similarity", 0.0)
                risk = getattr(r, "risk_level", "low")
                engine = getattr(r, "search_engine", "unknown")
                keyword = getattr(r, "search_keyword", keywords[0] if keywords else "N/A")

            results_detail.append(
                f"[{i + 1}] {title}\n"
                f"    URL: {url}\n"
                f"    平台: {domain}\n"
                f"    相似度: {similarity:.2%}\n"
                f"    风险等级: {risk.upper()}\n"
                f"    搜索引擎: {engine} / 关键词: {keyword}"
            )

        prompt = REPORT_GENERATION_PROMPT.format(
            content_type=content_type,
            detection_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            engines=", ".join(engines or []),
            keywords=", ".join((keywords or [])[:5]),
            result_count=len(results),
            results_detail="\n\n".join(results_detail) if results_detail else "无检测结果",
        )

        try:
            report = await provider.generate_text(
                prompt=prompt,
                system_prompt="你是一个专业的版权侵权检测报告撰写专家，报告要求客观、专业、可操作。",
                temperature=0.3,
                max_tokens=2048,
            )

            elapsed = time.monotonic() - start
            logger.info(
                f"[LLM-Detect] Report generated | provider={provider.name} "
                f"chars={len(report)} elapsed={elapsed:.2f}s"
            )
            return report.strip()

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning(
                f"[LLM-Detect] Report generation failed: {e} | "
                f"provider={provider.name} elapsed={elapsed:.2f}s, "
                f"using fallback"
            )
            return self._generate_fallback_report(results, content_type)

    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        if not url or url == "N/A":
            return "N/A"
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc or "N/A"
        except Exception:
            return "N/A"

    def _generate_fallback_report(
        self,
        results: Union[list[DetectionResult], list[dict]],
        content_type: str,
    ) -> str:
        """生成降级版纯文本报告（不调用 LLM，作为各步骤的兜底）"""
        high = []
        medium = []
        low = []
        for r in results:
            risk = r.risk_level if hasattr(r, "risk_level") else r.get("risk_level", "low")
            if risk == "high":
                high.append(r)
            elif risk == "medium":
                medium.append(r)
            else:
                low.append(r)

        lines = [
            f"侵权检测报告（降级模式，未调用 LLM）",
            f"=" * 50,
            f"",
            f"检测类型: {content_type}",
            f"检测到结果: {len(results)} 条",
            f"  - 高风险: {len(high)} 条",
            f"  - 中风险: {len(medium)} 条",
            f"  - 低风险: {len(low)} 条",
            f"",
        ]

        if high:
            lines.append("高风险侵权详情:")
            lines.append("-" * 30)
            for i, r in enumerate(high, 1):
                title = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "N/A")
                url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else "N/A")
                sim = getattr(r, "similarity", 0.0) or (r.get("similarity_score", 0.0) if isinstance(r, dict) else 0.0)
                domain = getattr(r, "domain", None) or (r.get("domain") if isinstance(r, dict) else self._extract_domain(url))
                lines.append(
                    f"{i}. {title or 'N/A'}\n"
                    f"   URL: {url or 'N/A'}\n"
                    f"   相似度: {sim:.2%}\n"
                    f"   平台: {domain or 'N/A'}"
                )

        lines.append("\n建议处置方式:")
        if high:
            lines.append("1. 截图/录屏保存证据")
            lines.append("2. 联系平台申请删帖/下架")
            lines.append("3. 发送侵权通知函")
            lines.append("4. 如情节严重，考虑法律途径")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 快捷方法：检测 + LLM 增强
    # ─────────────────────────────────────────────────────────────────────────

    async def detect_with_keywords(
        self,
        content: str | bytes,
        content_type: str,
        custom_keywords: list[str] | None = None,
        use_llm_keywords: bool = True,
        max_results: int = 50,
    ) -> list[DetectionResult]:
        """
        一步完成：关键词生成 + 侵权检测

        Args:
            content: 内容
            content_type: 内容类型
            custom_keywords: 自定义关键词（优先使用）
            use_llm_keywords: 是否用 LLM 生成关键词
            max_results: 最大结果数

        Returns:
            list[DetectionResult]: 检测结果列表
        """
        start = time.monotonic()
        logger.info(
            f"[LLM-Detect] detect_with_keywords | type={content_type} "
            f"custom_kw={bool(custom_keywords)} llm_kw={use_llm_keywords} "
            f"max_results={max_results}"
        )

        # Step 1: 生成关键词
        if custom_keywords:
            keywords = custom_keywords
        elif use_llm_keywords and self.config.keyword_llm_enabled:
            keywords = await self.generate_keywords_llm(content, content_type)
        else:
            keywords = self._base.generate_keywords(content, content_type)

        logger.info(f"[LLM-Detect] Keywords ready: {len(keywords)} | {keywords}")

        # Step 2: 执行检测
        results = []
        async for result in self._base.detect(
            content=content,
            content_type=content_type,
            keywords=keywords,
            max_results=max_results,
        ):
            results.append(result)

        elapsed = time.monotonic() - start
        high = sum(1 for r in results if r.risk_level == "high")
        medium = sum(1 for r in results if r.risk_level == "medium")
        logger.info(
            f"[LLM-Detect] Detection done | results={len(results)} "
            f"(high={high} medium={medium} low={len(results)-high-medium}) "
            f"elapsed={elapsed:.2f}s"
        )
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # 代理方法：透传 DetectionService 的方法
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def searchers(self):
        return self._base.searchers

    @property
    def comparators(self):
        return self._base.comparators

    def get_searcher(self, name: str):
        return self._base.get_searcher(name)

    def get_comparator(self, content_type: str):
        return self._base.get_comparator(content_type)

    async def detect(self, *args, **kwargs):
        """透传 DetectionService.detect()"""
        return self._base.detect(*args, **kwargs)

    async def quick_check(self, *args, **kwargs):
        """透传 DetectionService.quick_check()"""
        return self._base.quick_check(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# 全局单例（延迟初始化，避免启动时阻塞）
# ─────────────────────────────────────────────────────────────────────────────

_llm_detection_service: LLMDetectionService | None = None


def get_llm_detection_service() -> LLMDetectionService:
    """获取 LLM 增强检测服务单例"""
    global _llm_detection_service
    if _llm_detection_service is None:
        _llm_detection_service = LLMDetectionService()
    return _llm_detection_service
