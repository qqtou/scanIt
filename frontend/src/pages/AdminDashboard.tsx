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

  // 加载租户列表
  useEffect(() => {
    if (tab === "tenants") {
      setLoading(true);
      tenantsApi.list()
        .then(setTenants)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  }, [tab]);

  // 加载用户列表
  useEffect(() => {
    if (tab === "users") {
      setLoading(true);
      tenantsApi.listUsers()
        .then(setUsers)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  }, [tab]);

  const renderTenants = () => (
    <div className="admin-table-container">
      <div className="admin-toolbar">
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
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {tenants.map((t) => (
            <tr key={t.id}>
              <td>{t.name}</td>
              <td><code>{t.slug}</code></td>
              <td>{t.plan}</td>
              <td>{t.quota_monthly}</td>
              <td>{t.quota_used}</td>
              <td>
                <span className={`status-badge ${t.is_active ? "active" : "inactive"}`}>
                  {t.is_active ? "活跃" : "禁用"}
                </span>
              </td>
              <td>
                <button className="btn-sm">编辑</button>
                <button className="btn-sm btn-danger">删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderUsers = () => (
    <div className="admin-table-container">
      <div className="admin-toolbar">
        <button className="btn-primary">+ 新建用户</button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>
                <span className={`role-badge role-${u.role}`}>{u.role}</span>
              </td>
              <td>
                <span className={`status-badge ${u.is_active ? "active" : "inactive"}`}>
                  {u.is_active ? "活跃" : "禁用"}
                </span>
              </td>
              <td>
                <button className="btn-sm">编辑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderQuota = () => (
    <div className="admin-card">
      <h3>配额管理</h3>
      <p>查看当前租户配额使用情况</p>
      {/* 配额图表和统计 */}
    </div>
  );

  const renderSettings = () => (
    <div className="admin-card">
      <h3>租户设置</h3>
      <p>配置租户级别的参数（LLM Tier、通知等）</p>
      {/* 设置表单 */}
    </div>
  );

  return (
    <div className="admin-dashboard">
      <div className="admin-tabs">
        <button className={tab === "tenants" ? "active" : ""} onClick={() => setTab("tenants")}>
          租户管理
        </button>
        <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>
          用户管理
        </button>
        <button className={tab === "quota" ? "active" : ""} onClick={() => setTab("quota")}>
          配额
        </button>
        <button className={tab === "settings" ? "active" : ""} onClick={() => setTab("settings")}>
          设置
        </button>
      </div>

      <div className="admin-content">
        {loading && <div className="loading">加载中...</div>}
        {error && <div className="error">{error}</div>}
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
