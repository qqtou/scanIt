import { useState, useEffect } from "react";
import { tasksApi, worksApi, type DetectionTask, type Work } from "../api/client";

function Tasks() {
  const [tasks, setTasks] = useState<DetectionTask[]>([]);
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    work_id: 0,
    keywords: "",
    search_engines: ["google", "bing", "baidu"],
    max_results: 50,
  });
  const [submitting, setSubmitting] = useState(false);

  const pageSize = 10;

  useEffect(() => {
    loadTasks();
  }, [page, statusFilter]);

  useEffect(() => {
    worksApi.list({ page_size: 100, status: "active" }).then((res) => {
      setWorks(res.items);
      if (res.items.length > 0) {
        setFormData((f) => ({ ...f, work_id: res.items[0].id }));
      }
    });
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const res = await tasksApi.list({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      });
      setTasks(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const keywords = formData.keywords
        .split("\n")
        .map((k) => k.trim())
        .filter(Boolean);
      await tasksApi.create({
        work_id: formData.work_id,
        keywords,
        search_engines: formData.search_engines,
        max_results: formData.max_results,
      });
      setShowModal(false);
      setFormData({
        work_id: works[0]?.id || 0,
        keywords: "",
        search_engines: ["google", "bing", "baidu"],
        max_results: 50,
      });
      loadTasks();
    } catch (e) {
      alert("创建失败: " + (e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id: number) => {
    if (!confirm("确定要取消这个任务吗？")) return;
    try {
      await tasksApi.cancel(id);
      loadTasks();
    } catch (e) {
      alert("取消失败: " + (e as Error).message);
    }
  };

  const handleRetry = async (id: number) => {
    try {
      await tasksApi.retry(id);
      loadTasks();
    } catch (e) {
      alert("重试失败: " + (e as Error).message);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="badge badge-success">已完成</span>;
      case "running":
        return <span className="badge badge-info">进行中</span>;
      case "pending":
        return <span className="badge badge-warning">等待中</span>;
      case "failed":
        return <span className="badge badge-danger">失败</span>;
      default:
        return <span className="badge badge-gray">{status}</span>;
    }
  };

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">🔍 检测任务</h2>
          <div className="flex gap-2">
            <select
              className="form-select"
              style={{ width: "auto" }}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">全部状态</option>
              <option value="pending">等待中</option>
              <option value="running">进行中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
            </select>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              ➕ 创建任务
            </button>
          </div>
        </div>

        {loading ? (
          <div className="loading">
            <div className="spinner" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-title">暂无任务</div>
            <p>点击上方按钮创建第一个检测任务</p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>作品 ID</th>
                    <th>关键词数</th>
                    <th>状态</th>
                    <th>进度</th>
                    <th>结果数</th>
                    <th>高风险</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.work_id}</td>
                      <td>{task.keywords?.length || 0}</td>
                      <td>{getStatusBadge(task.status)}</td>
                      <td style={{ width: "150px" }}>
                        {task.status === "running" || task.status === "pending" ? (
                          <>
                            <div className="progress-bar mb-4">
                              <div
                                className="progress-fill"
                                style={{ width: `${task.progress}%` }}
                              />
                            </div>
                            <span className="text-sm text-gray">{task.progress}%</span>
                          </>
                        ) : (
                          <span className="text-sm text-gray">{task.progress}%</span>
                        )}
                      </td>
                      <td>{task.result_count}</td>
                      <td>
                        {task.high_risk_count > 0 ? (
                          <span className="stat-number high" style={{ fontSize: "16px" }}>
                            {task.high_risk_count}
                          </span>
                        ) : (
                          <span className="text-gray">{task.high_risk_count}</span>
                        )}
                      </td>
                      <td className="text-sm text-gray">
                        {new Date(task.created_at).toLocaleDateString("zh-CN")}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          {task.status === "failed" && (
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() => handleRetry(task.id)}
                            >
                              重试
                            </button>
                          )}
                          {(task.status === "pending" || task.status === "running") && (
                            <button
                              className="btn btn-sm btn-danger"
                              onClick={() => handleCancel(task.id)}
                            >
                              取消
                            </button>
                          )}
                          {task.status === "completed" && (
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() =>
                                window.location.hash = `#reports?task_id=${task.id}`
                              }
                            >
                              查看
                            </button>
                          )}
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

      {/* 创建任务弹窗 */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">创建检测任务</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">选择作品 *</label>
                <select
                  className="form-select"
                  value={formData.work_id}
                  onChange={(e) =>
                    setFormData({ ...formData, work_id: Number(e.target.value) })
                  }
                  required
                >
                  {works.map((work) => (
                    <option key={work.id} value={work.id}>
                      #{work.id} - {work.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">搜索关键词 * (每行一个)</label>
                <textarea
                  className="form-textarea"
                  value={formData.keywords}
                  onChange={(e) =>
                    setFormData({ ...formData, keywords: e.target.value })
                  }
                  required
                  placeholder={"keyword1&#10;keyword2&#10;keyword3"}
                  rows={5}
                />
              </div>
              <div className="form-group">
                <label className="form-label">搜索引擎</label>
                <div className="flex gap-4">
                  {["google", "bing", "baidu"].map((engine) => (
                    <label key={engine} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.search_engines.includes(engine)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              search_engines: [...formData.search_engines, engine],
                            });
                          } else {
                            setFormData({
                              ...formData,
                              search_engines: formData.search_engines.filter(
                                (s) => s !== engine
                              ),
                            });
                          }
                        }}
                      />
                      {engine}
                    </label>
                  ))}
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">最大结果数</label>
                <input
                  type="number"
                  className="form-input"
                  value={formData.max_results}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      max_results: Number(e.target.value),
                    })
                  }
                  min={1}
                  max={100}
                />
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submitting}
                >
                  {submitting ? "创建中..." : "创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Tasks;
