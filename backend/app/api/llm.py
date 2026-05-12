"""
LLM API Routes - LLM 增强检测和报告生成

Endpoints:
    GET  /llm/providers/status      - 获取所有 Provider 状态
    POST /llm/providers/switch       - 切换 Provider 或 Tier
    GET  /llm/providers/cost         - 获取费用汇总
    POST /llm/detect                - LLM 增强检测（生成关键词 + 侵权检测）
    POST /llm/report                - 生成侵权报告
"""

import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_user, get_current_tenant
from app.engines.detector_llm import LLMDetectionService
from app.engines.llm_provider import get_provider_manager
from app.models import Tenant, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["LLM"])


# ─── 请求/响应 Models ─────────────────────────────────────────────────────────

class ProviderSwitchRequest(BaseModel):
    """切换 Provider 请求"""
    provider_name: str | None = Field(
        default=None,
        description="指定 Provider 名称，如 'ollama' / 'douyin' / 'openai'。"
        "如不填则按 Tier 自动选择。",
    )
    tier: Literal["local", "budget", "enterprise"] | None = Field(
        default=None,
        description="指定 Tier：local(Tier1) / budget(Tier2) / enterprise(Tier3)。",
    )


class LLMDetectRequest(BaseModel):
    """LLM 增强检测请求"""
    content_type: Literal["text", "image", "video"] = Field(
        default="text",
        description="内容类型",
    )
    content: str = Field(
        ...,
        description="内容（文本内容或图片/视频 URL）",
    )
    content_url: str | None = Field(
        default=None,
        description="图片或视频 URL（与 content 二选一）",
    )
    threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="相似度阈值",
    )
    use_llm_keywords: bool = Field(
        default=True,
        description="是否使用 LLM 生成关键词（True=智能生成，False=规则提取）",
    )
    generate_report: bool = Field(
        default=False,
        description="是否同时生成 LLM 侵权报告",
    )
    search_engines: list[str] = Field(
        default=["google", "baidu"],
        description="搜索引擎列表",
    )
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大搜索结果数",
    )


class LLMReportRequest(BaseModel):
    """LLM 报告生成请求"""
    content_type: Literal["text", "image", "video"] = Field(
        default="text",
        description="内容类型",
    )
    content: str = Field(..., description="内容或 URL")
    results: list[dict] = Field(
        default=[],
        description="检测结果列表，每项含 similarity_score / url / title / snippet",
    )
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


# ─── Provider 状态 ───────────────────────────────────────────────────────────

class ProviderStatusItem(BaseModel):
    name: str
    tier: str
    model: str | None
    capabilities: list[str]
    initialized: bool
    available: bool
    cost_per_1k: float | None


class ProviderCostSummary(BaseModel):
    total_cost_usd: float
    total_cost_cny: float
    call_counts: dict[str, int]
    token_counts: dict[str, int]
    active_routes: dict[str, str]


@router.get("/providers/status", response_model=list[ProviderStatusItem])
async def get_providers_status(
    current_user: User = Depends(get_current_active_user),
) -> list[ProviderStatusItem]:
    """获取所有已注册的 LLM Provider 状态"""
    user_id = getattr(current_user, "id", "?")
    logger.info(f"[LLM-API] GET /llm/providers/status | user={user_id}")

    manager = get_provider_manager()
    status_list = manager.get_status()
    result = [
        ProviderStatusItem(
            name=name,
            tier=info.get("tier", "unknown"),
            model=info.get("model"),
            capabilities=list(info.get("capabilities", [])),
            initialized=info.get("initialized", False),
            available=info.get("available", False),
            cost_per_1k=info.get("cost_per_1k"),
        )
        for name, info in status_list.items()
    ]

    available_count = sum(1 for r in result if r.available)
    logger.info(
        f"[LLM-API] GET /llm/providers/status | user={user_id} | "
        f"total={len(result)} available={available_count}"
    )
    return result


@router.post("/providers/switch")
async def switch_provider(
    req: ProviderSwitchRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """切换 LLM Provider 或 Tier"""
    user_id = getattr(current_user, "id", "?")
    logger.info(
        f"[LLM-API] POST /llm/providers/switch | user={user_id} | "
        f"tier={req.tier} provider={req.provider_name}"
    )

    manager = get_provider_manager()

    # 优先使用租户配置的 llm_tier
    tenant_llm_tier = None
    if current_user.tenant_id and not req.tier:
        # 从租户配置读取默认 llm_tier
        from sqlalchemy import select
        from app.models.base import get_db
        async for db_sess in get_db():
            t_result = await db_sess.execute(
                select(Tenant).where(Tenant.id == current_user.tenant_id)
            )
            t_obj = t_result.scalar_one_or_none()
            if t_obj and t_obj.settings:
                raw = t_obj.settings.get("llm_tier", "")
                # tier_1_local → local, tier_2_budget → budget
                for k, v in [("tier_1_local", "local"), ("tier_2_budget", "budget"), ("tier_3_enterprise", "enterprise")]:
                    if raw == k:
                        tenant_llm_tier = v
                        break
            break
    if tenant_llm_tier:
        req.tier = tenant_llm_tier

    try:
        if req.tier:
            from app.engines.llm_provider.base import ProviderTier
            tier_map = {
                "local": ProviderTier.TIER_1_LOCAL,
                "budget": ProviderTier.TIER_2_BUDGET,
                "enterprise": ProviderTier.TIER_3_ENTERPRISE,
            }
            manager.set_tier(tier_map[req.tier])
            logger.info(f"[LLM-API] Switched to tier={req.tier} by user={user_id}")
            return {
                "success": True,
                "message": f"Tier 已切换为 {req.tier}",
                "current_tier": req.tier,
            }
        elif req.provider_name:
            provider = manager.select_provider(req.provider_name)
            logger.info(
                f"[LLM-API] Switched to provider={req.provider_name} by user={user_id}"
            )
            return {
                "success": True,
                "message": f"已切换到 {req.provider_name}",
                "provider": provider.name if provider else None,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供 provider_name 或 tier",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[LLM-API] Switch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/providers/cost", response_model=ProviderCostSummary)
async def get_cost_summary(
    current_user: User = Depends(get_current_active_user),
) -> ProviderCostSummary:
    """获取 LLM 调用费用汇总"""
    user_id = getattr(current_user, "id", "?")
    logger.info(f"[LLM-API] GET /llm/providers/cost | user={user_id}")

    manager = get_provider_manager()
    summary = manager.get_cost_summary()
    logger.info(
        f"[LLM-API] GET /llm/providers/cost | user={user_id} | "
        f"total_usd={summary.get('total_cost_usd', 0):.6f}"
    )
    return ProviderCostSummary(**summary)


# ─── LLM 增强检测 ─────────────────────────────────────────────────────────────

class LLMDetectResponse(BaseModel):
    keywords: list[str]
    keyword_source: Literal["llm", "rule"]
    results: list[dict]
    llm_report: str | None = None
    provider: str | None = None
    task_id: str | None = None


@router.post("/detect", response_model=LLMDetectResponse)
async def llm_detect(
    req: LLMDetectRequest,
    current_user: User = Depends(get_current_active_user),
) -> LLMDetectResponse:
    """
    LLM 增强侵权检测

    流程:
    1. 如果 use_llm_keywords=True，用 LLM 生成关键词（更智能）
    2. 调用搜索引擎搜索
    3. 比对内容侵权相似度
    4. 如果 generate_report=True，生成 LLM 侵权报告
    """
    user_id = getattr(current_user, "id", "?")
    start_time = time.monotonic()
    logger.info(
        f"[LLM-API] POST /llm/detect | user={user_id} | "
        f"type={req.content_type} llm_kw={req.use_llm_keywords} "
        f"report={req.generate_report} engines={req.search_engines}"
    )

    service = LLMDetectionService()

    content = req.content
    if req.content_url:
        content = req.content_url

    try:
        # Step 1: 生成关键词（LLM 或规则）
        if req.use_llm_keywords:
            logger.info(f"[LLM-API] Generating keywords via LLM | user={user_id}")
            keywords = await service.generate_keywords_llm(
                content=content,
                content_type=req.content_type,
            )
            keyword_source: Literal["llm", "rule"] = "llm"
            logger.info(
                f"[LLM-API] LLM keywords generated: {len(keywords)} | "
                f"provider={service._llm_provider_name} | user={user_id}"
            )
        else:
            from app.engines.detector import DetectionService
            ds = DetectionService()
            keywords = ds._extract_keywords(req.content, req.content_type)
            keyword_source = "rule"
            logger.info(
                f"[LLM-API] Rule-based keywords: {len(keywords)} | user={user_id}"
            )

        # Step 2: 侵权检测
        logger.info(
            f"[LLM-API] Running detection | keywords={len(keywords)} "
            f"threshold={req.threshold} | user={user_id}"
        )
        detection_results = await service.detect_with_keywords(
            content=content,
            content_type=req.content_type,
            custom_keywords=keywords,
            use_llm_keywords=False,  # 关键词已生成，传 False 避免重复调用 LLM
            max_results=req.max_results,
        )
        raw_results = detection_results

        # Step 3: 序列化结果（DetectionResult → dict）
        serializable_results = []
        for r in raw_results:
            # 支持 dict 或 DetectionResult 两种格式
            if isinstance(r, dict):
                serializable_results.append({
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "snippet": r.get("snippet"),
                    "similarity_score": r.get("similarity_score"),
                    "risk_level": r.get("risk_level"),
                    "search_engine": r.get("search_engine"),
                })
            else:
                # DetectionResult 对象属性
                serializable_results.append({
                    "url": getattr(r, "url", None),
                    "title": getattr(r, "title", None),
                    "snippet": getattr(r, "snippet", None),
                    "similarity_score": getattr(r, "similarity_score", 0.0),
                    "risk_level": getattr(r, "risk_level", "low"),
                    "search_engine": getattr(r, "search_engine", "unknown"),
                })

        logger.info(
            f"[LLM-API] Detection done | results={len(serializable_results)} "
            f"provider={service._llm_provider_name} | user={user_id}"
        )

        # Step 4: 生成报告
        llm_report = None
        if req.generate_report and serializable_results:
            logger.info(
                f"[LLM-API] Generating LLM report | "
                f"results={len(serializable_results)} | user={user_id}"
            )
            llm_report = await service.generate_report(
                content=content,
                content_type=req.content_type,
                results=serializable_results,  # 传入 dict 列表
                threshold=req.threshold,
            )
            logger.info(
                f"[LLM-API] Report generated | chars={len(llm_report)} | "
                f"provider={service._llm_provider_name} | user={user_id}"
            )

        elapsed = time.monotonic() - start_time
        logger.info(
            f"[LLM-API] POST /llm/detect completed | user={user_id} | "
            f"elapsed={elapsed:.2f}s | keywords={len(keywords)} "
            f"results={len(serializable_results)} report={bool(llm_report)}"
        )

        return LLMDetectResponse(
            keywords=keywords,
            keyword_source=keyword_source,
            results=serializable_results,
            llm_report=llm_report,
            provider=service._llm_provider_name,
        )

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.exception(
            f"[LLM-API] POST /llm/detect FAILED | user={user_id} "
            f"elapsed={elapsed:.2f}s error={e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM 检测失败: {e}",
        ) from e


# ─── LLM 报告生成 ────────────────────────────────────────────────────────────

class LLMReportResponse(BaseModel):
    report: str
    provider: str | None = None


@router.post("/report", response_model=LLMReportResponse)
async def generate_llm_report(
    req: LLMReportRequest,
    current_user: User = Depends(get_current_active_user),
) -> LLMReportResponse:
    """基于检测结果生成 LLM 侵权分析报告"""
    user_id = getattr(current_user, "id", "?")
    start_time = time.monotonic()
    logger.info(
        f"[LLM-API] POST /llm/report | user={user_id} | "
        f"type={req.content_type} results={len(req.results)}"
    )

    service = LLMDetectionService()

    try:
        report = await service.generate_report(
            content=req.content,
            content_type=req.content_type,
            results=req.results,  # list[dict]
            threshold=req.threshold,
        )
        elapsed = time.monotonic() - start_time
        logger.info(
            f"[LLM-API] POST /llm/report completed | user={user_id} | "
            f"elapsed={elapsed:.2f}s | chars={len(report)} "
            f"provider={service._llm_provider_name}"
        )
        return LLMReportResponse(
            report=report,
            provider=service._llm_provider_name,
        )
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.exception(
            f"[LLM-API] POST /llm/report FAILED | user={user_id} "
            f"elapsed={elapsed:.2f}s error={e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报告生成失败: {e}",
        ) from e
