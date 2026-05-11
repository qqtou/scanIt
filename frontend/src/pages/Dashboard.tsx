import { useState, useEffect } from "react";
import { dashboardApi, type DashboardStats } from "../api/client";

function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi.getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">❌</div>
        <div className="empty-state-title">加载失败</div>
        <p>{error}</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div>
      {/* 统计卡片 */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{stats.total_works}</div>
          <div className="stat-label">作品总数</div>
        </div>
        <div className="stat-card">
          <div className="stat-number" style={{ color: "#27ae60" }}>
            {stats.active_works}
          </div>
          <div className="stat-label">活跃作品</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.total_tasks}</div>
          <div className="stat-label">检测任务</div>
        </div>
        <div className="stat-card">
          <div className="stat-number" style={{ color: "#667eea" }}>
            {stats.completed_tasks}
          </div>
          <div className="stat-label">已完成</div>
        </div>
      </div>

      {/* 风险统计 */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">📊 检测结果概览</h2>
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">{stats.total_results}</div>
            <div className="stat-label">检测结果总数</div>
          </div>
          <div className="stat-card">
            <div className="stat-number high">{stats.high_risk_results}</div>
            <div className="stat-label">🚨 高风险</div>
          </div>
          <div className="stat-card">
            <div className="stat-number medium">{stats.medium_risk_results}</div>
            <div className="stat-label">⚠️ 中风险</div>
          </div>
          <div className="stat-card">
            <div className="stat-number low">{stats.low_risk_results}</div>
            <div className="stat-label">✅ 低风险</div>
          </div>
        </div>
      </div>

      {/* 快捷操作 */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">🚀 快捷操作</h2>
        </div>
        <div className="flex gap-4">
          <button
            className="btn btn-primary"
            onClick={() => window.location.hash = "#works"}
          >
            ➕ 创建新作品
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => window.location.hash = "#tasks"}
          >
            🔍 创建检测任务
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => window.location.hash = "#reports"}
          >
            📄 查看报告
          </button>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
