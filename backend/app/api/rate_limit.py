"""
API 限流中间件
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """自定义限流响应"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "retry_after": exc.detail,
        },
    )
