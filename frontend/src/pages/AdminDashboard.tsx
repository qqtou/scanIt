/**
 * Admin Dashboard - 租户管理仪表盘
 */
import { useState, useEffect } from "react";
import { tenantsApi, type Tenant, type TenantUser } from "../api/client";

type Tab = "tenants" | "users" | "quota" | "settings";

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>("tenants");
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (tab === "tenants") {
      setLoading(true);
      tenantsApi.list()
        .then(setTenants)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  }, [tab]);

  useEffect(() => {
    if (tab === "users") {
      setLoading(true);
      tenantsApi.listUsers()
        .then(setUsers)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  }, [tab]);

  // 配额统计数据
  const totalQuota = tenants.reduce((sum, t) => sum + (t.quota_monthly || 0), 0);
  const totalUsed = tenants.reduce((sum, t) => sum + (t.quota_used || 0), 0);

  const renderTenants = () => (
    <div className="admin-table-container">
      <div className="admin-toolbar">
        <span style={{ fontSize: "14px", color: "#6b7280" }}>
          共 {tenants.length} 个租户
        </span>
        <button className="btn-primary">+ 新建租户</button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>Slug</th>
            <th>套餐</th>
            <th>配额</th>
            <th>已用</th>
            <th>使用率</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {tenants.length === 0 && !loading && (
            <tr>
              <td colSpan={8} style={{ textAlign: "center", color: "#9ca3af", padding: "40px" }}>
                暂无租户数据
              </td>
            </tr>
          )}
          {tenants.map((t) => {
            const usageRate = t.quota_monthly ? Math.round((t.quota_used / t.quota_monthly) * 100) : 0;
            return (
              <tr key={t.id}>
                <td style={{ fontWeight: 500 }}>{t.name}</td>
                <td><code>{t.slug}</code></td>
                <td>
                  <span style={{
                    background: "#ede9fe",
                    color: "#5b21b6",
                    padding: "2px 10px",
                    borderRadius: "20px",
                    fontSize: "12px",
                    fontWeight: 500,
                  }}>
                    {t.plan}
                  </span>
                </td>
                <td>{t.quota_monthly?.toLocaleString() || 0}</td>
                <td>{t.quota_used?.toLocaleString() || 0}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{
                      width: "60px",
                      height: "6px",
                      background: "#f3f4f6",
                      borderRadius: "3px",
                      overflow: "hidden",
                    }}>
                      <div style={{
                        width: `${Math.min(usageRate, 100)}%`,
                        height: "100%",
                        background: usageRate > 90 ? "#ef4444" : usageRate > 70 ? "#f59e0b" : "#10b981",
                        borderRadius: "3px",
                      }} />
                    </div>
                    <span style={{ fontSize: "12px", color: "#6b7280" }}>{usageRate}%</span>
                  </div>
                </td>
                <td>
                  <span className={`status-badge ${t.is_active ? "active" : "inactive"}`}>
                    {t.is_active ? "活跃" : "禁用"}
                  </span>
                </td>
                <td>
                  <button className="btn-sm btn-secondary">编辑</button>
                  <button className="btn-sm btn-danger">删除</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const renderUsers = () => (
    <div className="admin-table-container">
      <div className="admin-toolbar">
        <span style={{ fontSize: "14px", color: "#6b7280" }}>
          共 {users.length} 个用户
        </span>
        <button className="btn-primary">+ 新建用户</button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>租户</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.length === 0 && !loading && (
            <tr>
              <td colSpan={6} style={{ textAlign: "center", color: "#9ca3af", padding: "40px" }}>
                暂无用户数据
              </td>
            </tr>
          )}
          {users.map((u) => (
            <tr key={u.id}>
              <td style={{ fontWeight: 500 }}>{u.username}</td>
              <td style={{ color: "#6b7280" }}>{u.email}</td>
              <td>
                <span className={`role-badge role-${u.role}`}>{u.role}</span>
              </td>
              <td style={{ color: "#6b7280" }}>—</td>
              <td>
                <span className={`status-badge ${u.is_active ? "active" : "inactive"}`}>
                  {u.is_active ? "活跃" : "禁用"}
                </span>
              </td>
              <td>
                <button className="btn-sm btn-secondary">编辑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderQuota = () => (
    <>
      <div className="admin-stats-grid">
        <div className="admin-stat-card">
          <div className="stat-label">总配额</div>
          <div className="stat-value" style={{ color: "#667eea" }}>{totalQuota.toLocaleString()}</div>
          <div className="stat-sub">本月所有租户</div>
        </div>
        <div className="admin-stat-card">
          <div className="stat-label">已使用</div>
          <div className="stat-value" style={{ color: totalUsed / totalQuota > 0.8 ? "#f59e0b" : "#10b981" }}>
            {totalUsed.toLocaleString()}
          </div>
          <div className="stat-sub">{totalQuota > 0 ? Math.round(totalUsed / totalQuota * 100) : 0}% 使用率</div>
        </div>
        <div className="admin-stat-card">
          <div className="stat-label">剩余配额</div>
          <div className="stat-value" style={{ color: "#6b7280" }}>
            {Math.max(0, totalQuota - totalUsed).toLocaleString()}
          </div>
          <div className="stat-sub">可用额度</div>
        </div>
        <div className="admin-stat-card">
          <div className="stat-label">租户数量</div>
          <div className="stat-value">{tenants.length}</div>
          <div className="stat-sub">活跃 {tenants.filter(t => t.is_active).length} 个</div>
        </div>
      </div>

      <div className="admin-card">
        <h3>📊 配额使用明细</h3>
        {tenants.length === 0 ? (
          <p>暂无租户数据</p>
        ) : (
          <div style={{ marginTop: "16px" }}>
            {tenants.map(t => {
              const rate = t.quota_monthly ? (t.quota_used / t.quota_monthly) * 100 : 0;
              return (
                <div key={t.id} style={{ marginBottom: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ fontSize: "14px", fontWeight: 500 }}>{t.name}</span>
                    <span style={{ fontSize: "13px", color: "#6b7280" }}>
                      {t.quota_used.toLocaleString()} / {t.quota_monthly?.toLocaleString() || 0}
                    </span>
                  </div>
                  <div style={{
                    width: "100%",
                    height: "8px",
                    background: "#f3f4f6",
                    borderRadius: "4px",
                    overflow: "hidden",
                  }}>
                    <div style={{
                      width: `${Math.min(rate, 100)}%`,
                      height: "100%",
                      background: rate > 90 ? "#ef4444" : rate > 70 ? "#f59e0b" : "linear-gradient(90deg, #667eea, #764ba2)",
                      borderRadius: "4px",
                      transition: "width 0.3s",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );

  const renderSettings = () => (
    <>
      <div className="settings-section">
        <h3>🤖 LLM 配置</h3>
        <div className="settings-row">
          <div>
            <div className="setting-label">默认 LLM Tier</div>
            <div className="setting-desc">任务使用的默认 LLM 层级</div>
          </div>
          <select className="form-select" style={{ width: "160px" }}>
            <option value="TIER_1_LOCAL">Tier 1 - 本地（免费）</option>
            <option value="TIER_2_BUDGET">Tier 2 - 低价 API</option>
            <option value="TIER_3_ENTERPRISE">Tier 3 - 企业级</option>
          </select>
        </div>
        <div className="settings-row">
          <div>
            <div className="setting-label">关键词增强</div>
            <div className="setting-desc">使用 LLM 辅助关键词提取，提升召回率</div>
          </div>
          <div className="toggle-switch active" onClick={() => {}} />
        </div>
        <div className="settings-row">
          <div>
            <div className="setting-label">多模态分析</div>
            <div className="setting-desc">对图片/视频内容进行深度语义分析</div>
          </div>
          <div className="toggle-switch active" onClick={() => {}} />
        </div>
      </div>

      <div className="settings-section">
        <h3>🔔 通知配置</h3>
        <div className="settings-row">
          <div>
            <div className="setting-label">任务完成通知</div>
            <div className="setting-desc">检测任务完成时发送邮件通知</div>
          </div>
          <div className="toggle-switch active" onClick={() => {}} />
        </div>
        <div className="settings-row">
          <div>
            <div className="setting-label">配额预警</div>
            <div className="setting-desc">配额使用超过 80% 时发送预警</div>
          </div>
          <div className="toggle-switch active" onClick={() => {}} />
        </div>
        <div className="settings-row">
          <div>
            <div className="setting-label">高风险结果告警</div>
            <div className="setting-desc">检测到高风险侵权时立即通知</div>
          </div>
          <div className="toggle-switch" onClick={() => {}} />
        </div>
      </div>

      <div className="settings-section">
        <h3>🛡️ 安全设置</h3>
        <div className="settings-row">
          <div>
            <div className="setting-label">双因素认证</div>
            <div className="setting-desc">要求用户启用双因素认证（OTP）</div>
          </div>
          <div className="toggle-switch" onClick={() => {}} />
        </div>
        <div className="settings-row">
          <div>
            <div className="setting-label">IP 白名单</div>
            <div className="setting-desc">仅允许指定 IP 访问 API</div>
          </div>
          <div className="toggle-switch" onClick={() => {}} />
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
        <button className="btn-primary">💾 保存设置</button>
      </div>
    </>
  );

  return (
    <div className="admin-dashboard">
      <div className="admin-tabs">
        <button className={tab === "tenants" ? "active" : ""} onClick={() => setTab("tenants")}>
          🏢 租户管理
        </button>
        <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>
          👥 用户管理
        </button>
        <button className={tab === "quota" ? "active" : ""} onClick={() => setTab("quota")}>
          📊 配额
        </button>
        <button className={tab === "settings" ? "active" : ""} onClick={() => setTab("settings")}>
          ⚙️ 设置
        </button>
      </div>

      <div className="admin-content">
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "60px", color: "#9ca3af" }}>
            加载中...
          </div>
        )}
        {error && <div className="error-message">{error}</div>}
        {!loading && !error && (
          <>
            {tab === "tenants" && renderTenants()}
            {tab === "users" && renderUsers()}
            {tab === "quota" && renderQuota()}
            {tab === "settings" && renderSettings()}
          </>
        )}
      </div>
    </div>
  );
}
