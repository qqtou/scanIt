/**
 * Sentry 前端错误追踪配置
 */
import * as Sentry from '@sentry/react';

// 简化初始化 - Sentry v7+ 需要 @sentry-integration 包
// 先禁用详细配置，使用默认设置
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  
  if (!dsn) {
    // Sentry DSN 未配置，跳过初始化
    return;
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE || 'development',
    release: import.meta.env.VITE_APP_VERSION || '0.1.0',
    // 使用默认集成
    integrations: [],
    tracesSampleRate: 0.1,
  });
}

export function setUserContext(user: { id: string; email?: string; tenant_id?: string; role?: string }) {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    tenant_id: user.tenant_id,
    role: user.role,
  });
}

export function clearUserContext() {
  Sentry.setUser(null);
}

export function captureException(exception: any, context?: Record<string, any>) {
  Sentry.captureException(exception, { contexts: { context } });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  Sentry.captureMessage(message, level);
}

export function setTag(key: string, value: string) {
  Sentry.setTag(key, value);
}