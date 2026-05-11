import { useState, useEffect } from "react";
import { authApi, type User } from "../api/client";

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

export default Settings;
