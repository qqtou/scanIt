import { useState, useEffect } from "react";
import { authApi, llmApi, type User, type LLMProviderStatus, type LLMCostSummary } from "../api/client";

function Settings() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.getMe().then(setUser).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div>
      {/* 用户信息 */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">👤 账户信息</h2>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">用户名</label>
            <input
              type="text"
              className="form-input"
              value={user?.username || ""}
              disabled
            />
          </div>
          <div className="form-group">
            <label className="form-label">邮箱</label>
            <input
              type="email"
              className="form-input"
              value={user?.email || ""}
              disabled
            />
          </div>
          <div className="form-group">
            <label className="form-label">角色</label>
            <input
              type="text"
              className="form-input"
              value={user?.role || ""}
              disabled
            />
          </div>
        </div>
      </div>

      {/* API 配额 */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">📊 API 配额</h2>
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">{user?.api_quota || 0}</div>
            <div className="stat-label">总配额</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{user?.api_quota_used || 0}</div>
            <div className="stat-label">已使用</div>
          </div>
          <div className="stat-card">
            <div className="stat-number" style={{ color: "#27ae60" }}>
              {(user?.api_quota || 0) - (user?.api_quota_used || 0)}
            </div>
            <div className="stat-label">剩余</div>
          </div>
        </div>
      </div>

      {/* LLM AI 设置 */}
      <LLMSettings />

      {/* 关于 */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">ℹ️ 关于 ScanIt</h2>
        </div>
        <div style={{ color: "#6b7280", lineHeight: 1.8 }}>
          <p><strong>ScanIt</strong> - 智能侵权检测系统</p>
          <p>版本: 1.0.0</p>
          <p>功能: 支持文本、图片、视频等多种内容的侵权检测</p>
          <p className="mt-4">
            集成多个搜索引擎，实时监测互联网上的侵权内容，保护您的知识产权。
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── LLM AI 设置面板 ───────────────────────────────────────────────────────

function LLMSettings() {
  const [providers, setProviders] = useState<LLMProviderStatus[]>([]);
  const [cost, setCost] = useState<LLMCostSummary | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>("local");
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [status, costData] = await Promise.all([
        llmApi.getProvidersStatus(),
        llmApi.getCostSummary(),
      ]);
      setProviders(status);
      setCost(costData);
      // 从 available=true 的 provider 反推当前 tier
      const active = status.find((p) => p.available);
      if (active) {
        if (active.tier === "tier1_local") setSelectedTier("local");
        else if (active.tier === "tier2_budget") setSelectedTier("budget");
        else setSelectedTier("enterprise");
      }
    } catch {
      setMessage("⚠️ 无法连接后端服务，请确保后端已启动。");
    } finally {
      setLoading(false);
    }
  }

  async function handleSwitchTier(tier: string) {
    setSwitching(true);
    setMessage(null);
    try {
      const res = await llmApi.switchProvider({ tier });
      setMessage(`✅ ${res.message}`);
      await loadData();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setMessage(`❌ 切换失败: ${e.detail || String(err)}`);
    } finally {
      setSwitching(false);
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">🤖 AI 设置</h2>
        </div>
        <div className="loading">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">🤖 AI 增强检测</h2>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          style={{
            padding: "10px 14px",
            marginBottom: 16,
            borderRadius: 6,
            background: message.startsWith("✅") ? "#d4edda" : "#f8d7da",
            color: message.startsWith("✅") ? "#155724" : "#721c24",
          }}
        >
          {message}
        </div>
      )}

      {/* Tier 选择 */}
      <div style={{ marginBottom: 20 }}>
        <label className="form-label">AI 模式</label>
        <div style={{ display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
          {[
            { value: "local", label: "🏠 本地（免费）", desc: "Ollama 本地运行" },
            { value: "budget", label: "💰 低成本", desc: "豆包/智谱/Claude" },
            { value: "enterprise", label: "🏢 企业级", desc: "GPT-4o / 通义千问" },
          ].map((t) => (
            <button
              key={t.value}
              onClick={() => handleSwitchTier(t.value)}
              disabled={switching}
              style={{
                flex: "1 1 160px",
                padding: "10px 14px",
                borderRadius: 8,
                border: selectedTier === t.value
                  ? "2px solid #3b82f6"
                  : "2px solid #e5e7eb",
                background: selectedTier === t.value ? "#eff6ff" : "#fff",
                cursor: switching ? "not-allowed" : "pointer",
                textAlign: "left",
                transition: "all 0.2s",
              }}
            >
              <div style={{ fontWeight: 600, color: "#1f2937" }}>{t.label}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{t.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Provider 状态列表 */}
      <div style={{ marginBottom: 16 }}>
        <label className="form-label">已配置的 Provider</label>
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
          {providers.length === 0 && (
            <div style={{ color: "#9ca3af", fontSize: 14 }}>暂无可用 Provider</div>
          )}
          {providers.map((p) => (
            <div
              key={p.name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 12px",
                borderRadius: 6,
                background: p.available ? "#d4edda" : "#f3f4f6",
                border: p.available ? "1px solid #c3e6cb" : "1px solid #e5e7eb",
              }}
            >
              <span style={{ fontSize: 16 }}>
                {p.available ? "✅" : "⚪"}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: "#1f2937" }}>
                  {p.name}
                  {p.model && (
                    <span style={{ fontWeight: 400, color: "#6b7280", marginLeft: 6, fontSize: 12 }}>
                      ({p.model})
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>
                  {p.tier} · {p.capabilities.join(", ")}
                </div>
              </div>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 12,
                  background: p.available ? "#28a745" : "#9ca3af",
                  color: "#fff",
                }}
              >
                {p.available ? "使用中" : "离线"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 费用汇总 */}
      {cost && cost.total_cost_usd > 0 && (
        <div style={{
          padding: "12px",
          borderRadius: 8,
          background: "#fffbeb",
          border: "1px solid #fcd34d",
          marginBottom: 12,
        }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: "#92400e" }}>
            💸 AI 调用费用
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
            <div>累计费用 (USD): <strong>${cost.total_cost_usd.toFixed(4)}</strong></div>
            <div>累计费用 (CNY): <strong>¥{cost.total_cost_cny.toFixed(4)}</strong></div>
          </div>
        </div>
      )}

      {/* 说明 */}
      <div style={{ fontSize: 12, color: "#9ca3af", lineHeight: 1.7, marginTop: 8 }}>
        <strong>模式说明：</strong><br />
        · <strong>本地（免费）</strong>：需本地安装 Ollama，适合有 GPU 的开发者<br />
        · <strong>低成本</strong>：豆包 ¥0.001/K tokens、智谱 ¥0.01/K tokens，适合个人用户<br />
        · <strong>企业级</strong>：GPT-4o / 通义千问，适合专业版权机构
      </div>
    </div>
  );
}

export default Settings;
