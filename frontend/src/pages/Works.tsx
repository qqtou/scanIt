import { useState, useEffect } from "react";
import { worksApi, type Work } from "../api/client";

function Works() {
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    content_type: "text" as "text" | "image" | "video",
    content_url: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const pageSize = 10;

  useEffect(() => {
    loadWorks();
  }, [page]);

  const loadWorks = async () => {
    setLoading(true);
    try {
      const res = await worksApi.list({ page, page_size: pageSize });
      setWorks(res.items);
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
      await worksApi.create(formData);
      setShowModal(false);
      setFormData({ title: "", content_type: "text", content_url: "" });
      loadWorks();
    } catch (e) {
      alert("创建失败: " + (e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除这个作品吗？")) return;
    try {
      await worksApi.delete(id);
      loadWorks();
    } catch (e) {
      alert("删除失败: " + (e as Error).message);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <span className="badge badge-success">活跃</span>;
      case "pending":
        return <span className="badge badge-warning">待处理</span>;
      case "inactive":
        return <span className="badge badge-gray">已停用</span>;
      default:
        return <span className="badge badge-gray">{status}</span>;
    }
  };

  const getContentTypeBadge = (type: string) => {
    switch (type) {
      case "text":
        return <span className="badge badge-info">文本</span>;
      case "image":
        return <span className="badge badge-info">图片</span>;
      case "video":
        return <span className="badge badge-info">视频</span>;
      default:
        return <span className="badge badge-gray">{type}</span>;
    }
  };

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">📚 我的作品</h2>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            ➕ 创建作品
          </button>
        </div>

        {loading ? (
          <div className="loading">
            <div className="spinner" />
          </div>
        ) : works.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <div className="empty-state-title">暂无作品</div>
            <p>点击上方按钮创建第一个作品</p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>标题</th>
                    <th>类型</th>
                    <th>任务数</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {works.map((work) => (
                    <tr key={work.id}>
                      <td>{work.id}</td>
                      <td>{work.title}</td>
                      <td>{getContentTypeBadge(work.content_type)}</td>
                      <td>{work.task_count}</td>
                      <td>{getStatusBadge(work.status)}</td>
                      <td className="text-sm text-gray">
                        {new Date(work.created_at).toLocaleDateString("zh-CN")}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() =>
                              window.location.hash = `#tasks?work_id=${work.id}`
                            }
                          >
                            检测
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleDelete(work.id)}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 分页 */}
            <div className="pagination">
              <button
                className="pagination-btn"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一页
              </button>
              <span className="text-sm text-gray">
                第 {page} / {Math.ceil(total / pageSize)} 页
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

      {/* 创建作品弹窗 */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">创建新作品</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">作品标题 *</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  required
                  placeholder="请输入作品标题"
                />
              </div>
              <div className="form-group">
                <label className="form-label">内容类型 *</label>
                <select
                  className="form-select"
                  value={formData.content_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      content_type: e.target.value as "text" | "image" | "video",
                    })
                  }
                >
                  <option value="text">文本</option>
                  <option value="image">图片</option>
                  <option value="video">视频</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">内容 URL</label>
                <input
                  type="url"
                  className="form-input"
                  value={formData.content_url}
                  onChange={(e) =>
                    setFormData({ ...formData, content_url: e.target.value })
                  }
                  placeholder={
                    formData.content_type === "text"
                      ? "请输入文本内容"
                      : "请输入图片或视频 URL"
                  }
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

export default Works;
