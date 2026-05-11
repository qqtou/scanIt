import { useState, useEffect } from "react";
import { resultsApi, type DetectionResult, type RiskSummary } from "../api/client";

function Reports() {
  const [results, setResults] = useState<DetectionResult[]>([]);
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [riskFilter, setRiskFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const pageSize = 10;

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
    const tid = params.get("task_id");
    if (tid) {
      setTaskId(Number(tid));
    }
  }, []);

  useEffect(() => {
    if (taskId) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [page, taskId, riskFilter, reviewFilter]);

  const loadData = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const [resultsRes, summaryRes] = await Promise.all([
        resultsApi.list({
          page,
          page_size: pageSize,
          task_id: taskId,
          risk_level: riskFilter || undefined,
          review_status: reviewFilter || undefined,
        }),
        resultsApi.getByTask(taskId),
      ]);
      setResults(resultsRes.items);
      setTotal(resultsRes.total);
      setSummary(summaryRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (
    id: number,
    status: "reviewed" | "ignored" | "confirmed"
  ) => {
    try {
      const notes = prompt("请输入审核备注（可选）:");
      await resultsApi.review(id, status, notes || undefined);
      loadData();
    } catch (e) {
      alert("审核失败: " + (e as Error).message);
    }
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case "high":
        return <span className="badge badge-danger">🚨 高风险</span>;
      case "medium":
        return <span className="badge badge-warning">⚠️ 中风险</span>;
      case "low":
        return <span className="badge badge-success">✅ 低风险</span>;
      default:
        return <span className="badge badge-gray">{level}</span>;
    }
  };

  const getReviewBadge = (status: string) => {
    switch (status) {
      case "reviewed":
        return <span className="badge badge-success">已审核</span>;
      case "confirmed":
        return <span className="badge badge-danger">确认侵权</span>;
      case "ignored":
        return <span className="badge badge-gray">已忽略</span>;
      default:
        return <span className="badge badge-warning">待审核</span>;
    }
  };

  return (
    <div>
      {/* 任务 ID 输入 */}
      <div className="card">
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">任务 ID</label>
            <input
              type="number"
              className="form-input"
              value={taskId || ""}
              onChange={(e) => {
                const v = e.target.value;
                setTaskId(v ? Number(v) : null);
                setPage(1);
              }}
              placeholder="输入任务 ID 查看结果"
            />
          </div>
        </div>
      </div>

      {taskId && (
        <>
          {/* 统计卡片 */}
          {summary && (
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-number">{summary.total}</div>
                <div className="stat-label">结果总数</div>
              </div>
              <div className="stat-card">
                <div className="stat-number high">{summary.high}</div>
                <div className="stat-label">高风险</div>
              </div>
              <div className="stat-card">
                <div className="stat-number medium">{summary.medium}</div>
                <div className="stat-label">中风险</div>
              </div>
              <div className="stat-card">
                <div className="stat-number low">{summary.low}</div>
                <div className="stat-label">低风险</div>
              </div>
            </div>
          )}

          {/* 导出按钮 */}
          <div className="card">
            <div className="flex justify-between items-center">
              <h2 className="card-title">📋 检测结果</h2>
              <div className="flex gap-2">
                <select
                  className="form-select"
                  style={{ width: "auto" }}
                  value={riskFilter}
                  onChange={(e) => {
                    setRiskFilter(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">全部风险</option>
                  <option value="high">高风险</option>
                  <option value="medium">中风险</option>
                  <option value="low">低风险</option>
                </select>
                <select
                  className="form-select"
                  style={{ width: "auto" }}
                  value={reviewFilter}
                  onChange={(e) => {
                    setReviewFilter(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">全部状态</option>
                  <option value="pending">待审核</option>
                  <option value="reviewed">已审核</option>
                  <option value="confirmed">确认侵权</option>
                  <option value="ignored">已忽略</option>
                </select>
                <a
                  href={resultsApi.exportCsv(taskId)}
                  className="btn btn-secondary"
                  download
                >
                  📥 导出 CSV
                </a>
              </div>
            </div>
          </div>

          {/* 结果列表 */}
          <div className="card">
            {loading ? (
              <div className="loading">
                <div className="spinner" />
              </div>
            ) : results.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <div className="empty-state-title">暂无结果</div>
              </div>
            ) : (
              <>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>风险</th>
                        <th>相似度</th>
                        <th>标题</th>
                        <th>URL</th>
                        <th>来源</th>
                        <th>审核状态</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((result) => (
                        <tr key={result.id}>
                          <td>{getRiskBadge(result.risk_level)}</td>
                          <td>
                            <span
                              className={`stat-number ${
                                result.risk_level === "high"
                                  ? "high"
                                  : result.risk_level === "medium"
                                  ? "medium"
                                  : "low"
                              }`}
                              style={{ fontSize: "16px" }}
                            >
                              {(result.similarity_score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td style={{ maxWidth: "200px" }}>
                            <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {result.source_title || "-"}
                            </div>
                          </td>
                          <td style={{ maxWidth: "200px" }}>
                            <a
                              href={result.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: "#667eea", overflow: "hidden", textOverflow: "ellipsis", display: "block" }}
                            >
                              {result.source_url}
                            </a>
                          </td>
                          <td>
                            <span className="badge badge-info">
                              {result.search_engine}
                            </span>
                          </td>
                          <td>{getReviewBadge(result.review_status)}</td>
                          <td>
                            <div className="flex gap-2">
                              <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => handleReview(result.id, "reviewed")}
                              >
                                已审核
                              </button>
                              <button
                                className="btn btn-sm btn-danger"
                                onClick={() => handleReview(result.id, "confirmed")}
                              >
                                确认
                              </button>
                              <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => handleReview(result.id, "ignored")}
                              >
                                忽略
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="pagination">
                  <button
                    className="pagination-btn"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    上一页
                  </button>
                  <span className="text-sm text-gray">
                    第 {page} / {Math.ceil(total / pageSize) || 1} 页
                  </span>
                  <button
                    className="pagination-btn"
                    disabled={page >= Math.ceil(total / pageSize)}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    下一页
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default Reports;
