/**
 * Sentry 前端错误追踪配置
 */
import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import { Integrations } from '@sentry/integrations';

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  
  if (!dsn) {
    // Sentry DSN 未配置，跳过初始化
    console.warn('Sentry DSN 未配置，跳过前端错误追踪');
    return;
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE || 'development',
    release: import.meta.env.VITE_APP_VERSION || '0.1.0',
    
    // 集成
    integrations: [
      new BrowserTracing({
        // 自动追踪页面加载和导航
        traceFetch: true,
        traceXHR: true,
      }),
      new Integrations.GlobalErrors(),
      new Integrations.TryCatch(),
    ],
    
    // 采样率
    tracesSampleRate: 0.1, // 10% 性能采样
    
    // 错误处理
    beforeSend(event, hint) {
      // 过滤敏感数据
      if (event.request?.headers) {
        const headers = event.request.headers;
        if (headers['Authorization']) {
          headers['Authorization'] = '[Filtered]';
        }
        if (headers['Cookie']) {
          headers['Cookie'] = '[Filtered]';
        }
      }
      
      // 过滤开发环境错误
      if (import.meta.env.MODE === 'development') {
        return null;
      }
      
      return event;
    },
    
    // 调试模式（开发环境）
    debug: import.meta.env.MODE === 'development',
    
    // 最大面包屑数
    maxBreadcrumbs: 50,
    
    // 附加堆栈
    attachStacktrace: true,
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
