/**
 * API 客户端
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

// 通用响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// HTTP 工具函数
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token 过期，尝试刷新
    const refreshed = await refreshToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${localStorage.getItem("access_token")}`;
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
      if (!retryResponse.ok) {
        throw new Error(await retryResponse.text());
      }
      return retryResponse.json();
    }
    // 刷新失败，跳转登录
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }

  // 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Token 刷新
async function refreshToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    localStorage.setItem("access_token", data.access_token);
    return true;
  } catch {
    return false;
  }
}

// ============ 认证相关 ============

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  role: string;
  api_quota: number;
  api_quota_used: number;
  created_at: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  register: (data: RegisterRequest) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMe: () => request<User>("/auth/me"),

  refresh: (refreshToken: string) =>
    request<AuthResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// ============ 作品相关 ============

export interface Work {
  id: number;
  user_id: number;
  title: string;
  content_type: "text" | "image" | "video";
  content_url: string | null;
  content_hash: string | null;
  status: "pending" | "active" | "inactive";
  task_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkCreate {
  title: string;
  content_type: "text" | "image" | "video";
  content_url?: string;
  content_hash?: string;
}

export interface WorkUpdate {
  title?: string;
  content_url?: string;
  status?: "pending" | "active" | "inactive";
}

export const worksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    if (params?.status) searchParams.set("status", params.status);
    return request<PaginatedResponse<Work>>(`/works/?${searchParams}`);
  },

  get: (id: number) => request<Work>(`/works/${id}`),

  create: (data: WorkCreate) =>
    request<Work>("/works/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: WorkUpdate) =>
    request<Work>(`/works/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/works/${id}`, { method: "DELETE" }),
};

// ============ LLM 相关 ============

export interface LLMProviderStatus {
  name: string;
  tier: string;
  model: string | null;
  capabilities: string[];
  initialized: boolean;
  available: boolean;
  cost_per_1k: number | null;
}

export interface LLMCostSummary {
  total_cost_usd: number;
  total_cost_cny: number;
  call_counts: Record<string, number>;
  token_counts: Record<string, number>;
  active_routes: Record<string, string>;
}

export interface LLMDetectRequest {
  content_type: "text" | "image" | "video";
  content: string;
  content_url?: string;
  threshold?: number;
  use_llm_keywords?: boolean;
  generate_report?: boolean;
  search_engines?: string[];
  max_results?: number;
}

export interface LLMDetectResponse {
  keywords: string[];
  keyword_source: "llm" | "rule";
  results: Array<{
    url: string;
    title: string;
    snippet: string;
    similarity_score: number;
    risk_level: string;
    search_engine: string;
  }>;
  llm_report: string | null;
  provider: string | null;
  task_id: string | null;
}

export interface LLMReportRequest {
  content_type: "text" | "image" | "video";
  content: string;
  results: Array<{
    url: string;
    title: string;
    snippet: string;
    similarity_score: number;
  }>;
  threshold?: number;
}

export const llmApi = {
  /** 获取所有 Provider 状态 */
  getProvidersStatus: () =>
    request<LLMProviderStatus[]>("/llm/providers/status"),

  /** 切换 Provider 或 Tier */
  switchProvider: (data: { provider_name?: string; tier?: string }) =>
    request<{ success: boolean; message: string; current_tier?: string }>(
      "/llm/providers/switch",
      { method: "POST", body: JSON.stringify(data) }
    ),

  /** 获取费用汇总 */
  getCostSummary: () => request<LLMCostSummary>("/llm/providers/cost"),

  /** LLM 增强侵权检测 */
  detect: (data: LLMDetectRequest) =>
    request<LLMDetectResponse>("/llm/detect", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 生成 LLM 侵权报告 */
  generateReport: (data: LLMReportRequest) =>
    request<{ report: string; provider: string | null }>("/llm/report", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ============ 任务相关 ============

export interface DetectionTask {
  id: number;
  work_id: number;
  keywords: string[];
  search_engines: string[];
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  result_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  error_message: string | null;
  celery_task_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TaskCreate {
  work_id: number;
  keywords: string[];
  search_engines?: string[];
  max_results?: number;
}

export const tasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; work_id?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    if (params?.status) searchParams.set("status", params.status);
    if (params?.work_id) searchParams.set("work_id", String(params.work_id));
    return request<PaginatedResponse<DetectionTask>>(`/tasks/?${searchParams}`);
  },

  get: (id: number) => request<DetectionTask>(`/tasks/${id}`),

  create: (data: TaskCreate) =>
    request<DetectionTask>("/tasks/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  cancel: (id: number) =>
    request<DetectionTask>(`/tasks/${id}/cancel`, { method: "POST" }),

  retry: (id: number) =>
    request<DetectionTask>(`/tasks/${id}/retry`, { method: "POST" }),
};

// ============ 结果相关 ============

export interface DetectionResult {
  id: number;
  task_id: number;
  source_url: string;
  source_title: string | null;
  source_snippet: string | null;
  source_domain: string | null;
  similarity_score: number;
  risk_level: "high" | "medium" | "low";
  search_engine: string;
  search_keyword: string;
  review_status: "pending" | "reviewed" | "ignored" | "confirmed";
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface RiskSummary {
  total: number;
  high: number;
  medium: number;
  low: number;
  avg_similarity: number;
}

export const resultsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    task_id?: number;
    risk_level?: string;
    review_status?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    if (params?.task_id) searchParams.set("task_id", String(params.task_id));
    if (params?.risk_level) searchParams.set("risk_level", params.risk_level);
    if (params?.review_status) searchParams.set("review_status", params.review_status);
    return request<PaginatedResponse<DetectionResult>>(`/results/?${searchParams}`);
  },

  get: (id: number) => request<DetectionResult>(`/results/${id}`),

  getByTask: (taskId: number) => request<RiskSummary>(`/results/task/${taskId}/summary`),

  review: (id: number, status: string, notes?: string) =>
    request<DetectionResult>(`/results/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ review_status: status, review_notes: notes }),
    }),

  exportCsv: (taskId: number) =>
    `${API_BASE_URL}/results/export/csv?task_id=${taskId}`,
};

// ============ 仪表盘 ============

export interface DashboardStats {
  total_works: number;
  active_works: number;
  total_tasks: number;
  completed_tasks: number;
  total_results: number;
  high_risk_results: number;
  medium_risk_results: number;
  low_risk_results: number;
}

export const dashboardApi = {
  getStats: () => request<DashboardStats>("/dashboard/stats"),
};

// ============ 租户相关（Admin） ============

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: "basic" | "pro" | "enterprise";
  quota_monthly: number;
  quota_used: number;
  quota_period_start: string;
  is_active: boolean;
  settings: Record<string, unknown>;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
}

export interface TenantCreate {
  name: string;
  slug: string;
  plan?: "basic" | "pro" | "enterprise";
  quota_monthly?: number;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface TenantUpdate {
  name?: string;
  plan?: "basic" | "pro" | "enterprise";
  quota_monthly?: number;
  is_active?: boolean;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface TenantUser {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export const tenantsApi = {
  // System Admin: 租户 CRUD
  list: (params?: { skip?: number; limit?: number; is_active?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.skip) sp.set("skip", String(params.skip));
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.is_active !== undefined) sp.set("is_active", String(params.is_active));
    return request<Tenant[]>(`/system/tenants?${sp}`);
  },

  get: (id: string) => request<Tenant>(`/system/tenants/${id}`),

  create: (data: TenantCreate) =>
    request<Tenant>("/system/tenants", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: TenantUpdate) =>
    request<Tenant>(`/system/tenants/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) =>
    request<void>(`/system/tenants/${id}`, { method: "DELETE" }),

  // Tenant Admin: 配额 & 设置
  getQuota: () => request<{ tenant_id: string; quota_monthly: number; quota_used: number; quota_period_start: string }>("/admin/quota"),

  getSettings: () => request<{ tenant_id: string; settings: Record<string, unknown> }>("/admin/settings"),

  updateSettings: (data: Record<string, unknown>) =>
    request<{ tenant_id: string; settings: Record<string, unknown> }>("/admin/settings", { method: "PUT", body: JSON.stringify(data) }),

  // Tenant Admin: 用户管理
  listUsers: (params?: { skip?: number; limit?: number; role?: string }) => {
    const sp = new URLSearchParams();
    if (params?.skip) sp.set("skip", String(params.skip));
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.role) sp.set("role", params.role);
    return request<TenantUser[]>(`/admin/users?${sp}`);
  },

  createUser: (data: { email: string; username: string; password: string; role?: string; full_name?: string }) =>
    request<TenantUser>("/admin/users", { method: "POST", body: JSON.stringify(data) }),

  updateUser: (id: string, data: { role?: string; is_active?: boolean }) =>
    request<TenantUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};
