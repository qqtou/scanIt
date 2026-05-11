#!/usr/bin/env python3
"""
ScanIt LLM Demo - 不同 Tier 效果对比演示

用法:
    # Tier 1 (本地 Ollama)
    $env:OLLAMA_BASE_URL="http://localhost:11434"
    $env:OLLAMA_MODEL="llama3.2"
    python demo_tiers.py

    # Tier 2 (云端)
    $env:AI_TIER="budget"
    $env:ZHIPU_API_KEY="your_key_here"
    python demo_tiers.py

    # Tier 3 (企业级)
    $env:AI_TIER="enterprise"
    $env:OPENAI_API_KEY="your_key_here"
    python demo_tiers.py

依赖:
    pip install -e backend/
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

# ── ANSI 颜色 ────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"""
{CYAN}{'='*60}
  ScanIt LLM Demo - Tier 效果对比演示
{'='*60}{RESET}
""".strip())


def print_header(text: str):
    print(f"\n{BOLD}{'─'*60}\n  {text}\n{'─'*60}{RESET}")


def print_ok(text: str):
    print(f"  {GREEN}✓{RESET} {text}")


def print_warn(text: str):
    print(f"  {YELLOW}⚠{RESET} {text}")


def print_err(text: str):
    print(f"  {RED}✗{RESET} {text}")


def print_info(text: str):
    print(f"  {CYAN}ℹ{RESET} {text}")


def print_result(label: str, value: str | dict | list):
    print(f"  {BOLD}{label}:{RESET}")
    if isinstance(value, dict):
        for k, v in value.items():
            print(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    elif isinstance(value, list):
        for item in value:
            print(f"    - {item}")
    else:
        print(f"    {value}")


# ── Demo 样本数据 ─────────────────────────────────────────────────────────────

DEMO_TEXT = (
    "原创文章：如何利用人工智能提升内容创作效率。"
    "本文介绍了使用大语言模型进行文章撰写、校对和优化的方法，"
    "包括提示词工程、上下文管理和多模态内容生成的实践技巧。"
)

DEMO_IMAGE_URL = "https://via.placeholder.com/800x600.png?text=Sample+Image"

DEMO_RESULTS = [
    {
        "url": "https://example.com/article1",
        "title": "AI写作技巧完全指南",
        "snippet": "利用人工智能提升内容创作效率的详细教程",
        "similarity_score": 0.82,
        "risk_level": "high",
        "search_engine": "google",
    },
    {
        "url": "https://example.com/article2",
        "title": "人工智能写作工具评测",
        "snippet": "主流AI写作工具横向对比",
        "similarity_score": 0.71,
        "risk_level": "medium",
        "search_engine": "baidu",
    },
    {
        "url": "https://example.com/article3",
        "title": "内容创作的未来趋势",
        "snippet": "探讨AI如何改变内容创作行业",
        "similarity_score": 0.45,
        "risk_level": "low",
        "search_engine": "bing",
    },
]


# ── Demo 函数 ────────────────────────────────────────────────────────────────

async def demo_provider_status(service):
    """Demo 1: 检查所有 Provider 状态"""
    print_header("Demo 1: Provider 状态检测")

    from app.engines.llm_provider import get_provider_manager
    manager = get_provider_manager()

    status = manager.get_status()
    current_tier = manager.get_tier()
    print_info(f"当前 Tier: {current_tier.name}")
    print(f"  已注册 Provider 数: {len(status)}")

    for name, info in status.items():
        available = info.get("available", False)
        initialized = info.get("initialized", False)
        marker = f"{GREEN}可用{RESET}" if available else f"{RED}离线{RESET}"
        print(f"  [{marker}] {BOLD}{name}{RESET}")
        print(f"       Tier: {info.get('tier')} | Model: {info.get('model')}")
        print(f"       Capabilities: {', '.join(info.get('capabilities', []))}")
        print(f"       初始化: {'是' if initialized else '否'}")
    return status


async def demo_keyword_generation(service):
    """Demo 2: 关键词生成对比"""
    print_header("Demo 2: 关键词生成（LLM vs 规则提取）")

    # 规则提取（兜底）
    from app.engines.detector import DetectionService
    ds = DetectionService()
    rule_keywords = ds._extract_keywords(DEMO_TEXT, "text")

    print(f"\n  {BOLD}【规则提取结果】{RESET}")
    print(f"  关键词: {', '.join(rule_keywords)}")

    # LLM 生成
    try:
        llm_keywords = await service.generate_keywords_llm(
            content=DEMO_TEXT,
            content_type="text",
        )
        print(f"\n  {BOLD}【LLM 生成结果】{RESET} (via {service._llm_provider_name})")
        print(f"  关键词: {', '.join(llm_keywords)}")

        print_warn("LLM 关键词通常更全面，能捕捉语义层面的侵权特征")
        return {"rule": rule_keywords, "llm": llm_keywords}
    except Exception as e:
        print_err(f"LLM 关键词生成失败: {e}")
        return {"rule": rule_keywords, "llm": None}


async def demo_image_analysis(service):
    """Demo 3: 图片深度分析"""
    print_header("Demo 3: 图片侵权分析")

    # 检查是否支持视觉
    from app.engines.llm_provider.base import Capability
    if not service._provider or Capability.VISION not in service._provider.capabilities:
        print_warn("当前 Provider 不支持视觉分析，跳过图片演示")
        return None

    try:
        analysis = await service.analyze_image_llm(
            image_url=DEMO_IMAGE_URL,
            task="infringement_detection",
        )
        print(f"\n  {BOLD}【LLM 图片分析结果】{RESET} (via {service._llm_provider_name})")
        print(f"  {analysis}")
        return analysis
    except Exception as e:
        print_err(f"图片分析失败: {e}")
        return None


async def demo_report_generation(service):
    """Demo 4: 侵权报告生成"""
    print_header("Demo 4: LLM 侵权报告生成")

    try:
        report = await service.generate_report(
            content=DEMO_TEXT,
            content_type="text",
            results=DEMO_RESULTS,
            threshold=0.7,
        )
        print(f"\n  {BOLD}【侵权分析报告】{RESET} (via {service._llm_provider_name})")
        print(f"  {report}")
        return report
    except Exception as e:
        print_err(f"报告生成失败: {e}")
        return None


async def demo_embedding_similarity(service):
    """Demo 5: Embedding 语义相似度"""
    print_header("Demo 5: Embedding 语义相似度计算")

    from app.engines.llm_provider.base import Capability
    if not service._provider or Capability.EMBEDDING not in service._provider.capabilities:
        print_warn("当前 Provider 不支持 Embedding，跳过语义相似度演示")
        return None

    original = DEMO_TEXT
    # 构造一个近似改写版本
    plagiarized = (
        "原创文章：怎样使用人工智能提高内容创作效率。"
        "本文讲解了利用大语言模型进行文章撰写、校对和优化的技巧，"
        "涵盖提示词工程、上下文管理与多模态内容生成的实战经验。"
    )

    try:
        sim = await service.compute_similarity_embedding(original, plagiarized)
        print(f"\n  原文与改写版本的语义相似度: {sim:.4f}")
        if sim > 0.85:
            print_warn("相似度 > 0.85，判定为高度相似（疑似侵权）")
        elif sim > 0.70:
            print_info("相似度 0.70-0.85，判定为中度相似（需人工复核）")
        else:
            print_ok("相似度 < 0.70，判定为低相似（正常）")
        return sim
    except Exception as e:
        print_err(f"Embedding 相似度计算失败: {e}")
        return None


# ── 主流程 ───────────────────────────────────────────────────────────────────

async def run_demo():
    print_banner()
    print_info(f"时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print_info(f"Python: {sys.version.split()[0]}")
    print_info(f"后端: {os.getcwd()}")

    # 导入检测
    try:
        from app.engines.detector_llm import LLMDetectionService
    except ImportError as e:
        print_err(f"无法导入 LLMDetectionService: {e}")
        print_info("请确保已安装后端依赖: pip install -e backend/")
        sys.exit(1)

    # 初始化服务
    print_header("初始化 LLMDetectionService")
    service = LLMDetectionService()
    print_info(f"Provider: {service._llm_provider_name}")
    print_info(f"Tier: {service._llm_provider_tier}")

    # 运行所有 Demo
    start = time.time()

    await demo_provider_status(service)

    kw_result = await demo_keyword_generation(service)
    if kw_result and kw_result["llm"]:
        extra = len(kw_result["llm"]) - len(kw_result["rule"])
        if extra > 0:
            print_ok(f"LLM 比规则多提取了 {extra} 个关键词")

    img_result = await demo_image_analysis(service)

    report_result = await demo_report_generation(service)

    emb_result = await demo_embedding_similarity(service)

    elapsed = time.time() - start

    # 总结
    print_header("Demo 完成")
    print_info(f"总耗时: {elapsed:.2f}s")
    print_info(f"使用的 Provider: {service._llm_provider_name}")
    print_ok("所有 Demo 演示完成！")

    # Tier 对比总结
    print(f"""
{BOLD}╔══════════════════════════════════════════════════════════════╗
║                     Tier 效果对比总结                           ║
╠══════════════════════════════════════════════════════════════════╣
║  Tier 1 (本地 Ollama)                                           ║
║  ✅ 完全免费，数据不外传                                         ║
║  ⚠️ 需要 GPU，模型质量依赖本地模型能力                           ║
║  ⚠️ Embedding 可能不可用                                        ║
║                                                                  ║
║  Tier 2 (低成本云: 豆包/智谱/Kimi)                               ║
║  ✅ ¥0.001-0.01/K tokens，成本极低                               ║
║  ✅ 中文优化，支持 Vision/Embedding                              ║
║  ⚠️ 额度有限，大规模使用需付费                                   ║
║                                                                  ║
║  Tier 3 (企业级: GPT-4o/Claude)                                ║
║  ✅ 最强模型质量，报告生成最专业                                  ║
║  ✅ 支持多模态，Embedding 精度最高                               ║
║  ⚠️ 成本最高（¥500+/月）                                        ║
╚══════════════════════════════════════════════════════════════════╝{RESET}
""".strip())


def main():
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
