"""
Sentry 错误追踪配置
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from app.core.config import settings


def init_sentry():
    """初始化 Sentry SDK"""
    if not settings.sentry_dsn:
        # Sentry DSN 未配置，跳过初始化
        return
    
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.app_version,
        
        # 集成
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        
        # 采样率
        traces_sample_rate=0.1,  # 10% 性能采样
        profiles_sample_rate=0.1,  # 10% 性能profile
        
        # 错误处理
        send_default_pii=False,  # 不发送个人身份信息
        attach_stacktrace=True,
        
        # 标签
        before_send=filter_sensitive_data,
    )


def filter_sensitive_data(event, hint):
    """过滤敏感数据（JWT token、密码等）"""
    # 移除 authorization header
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        if 'Authorization' in headers:
            headers['Authorization'] = '[Filtered]'
        if 'Cookie' in headers:
            headers['Cookie'] = '[Filtered]'
    
    return event


def capture_exception(exc: Exception, **kwargs):
    """手动捕获异常"""
    sentry_sdk.capture_exception(exc, **kwargs)


def capture_message(message: str, level: str = "info", **kwargs):
    """手动捕获消息"""
    sentry_sdk.capture_message(message, level=level, **kwargs)


def set_user_context(user_id: str, tenant_id: str = None, role: str = None):
    """设置用户上下文"""
    sentry_sdk.set_user({
        "id": user_id,
        "tenant_id": tenant_id,
        "role": role,
    })


def set_tags(tags: dict):
    """设置标签"""
    for key, value in tags.items():
        sentry_sdk.set_tag(key, value)
