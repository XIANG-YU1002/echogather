import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getMyGroupBuys } from "../../api/groupLeaderGroupBuys.js";
import {
  createAnnouncement,
  deleteAnnouncement,
  getMyAnnouncements,
  updateAnnouncement,
} from "../../api/groupLeaderAnnouncements.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  });
}

const EMPTY_FORM = {
  audience_scope: "leader_unfinished",
  group_buy_id: "",
  title: "",
  content: "",
  is_public: true,
};

export default function AnnouncementListPage() {
  const { token } = useAuth();
  // 從圖 22 的「團購公告」分頁進來時只顯示該團的公告
  const [searchParams, setSearchParams] = useSearchParams();
  const filterGroupBuyId = searchParams.get("group_buy_id") ?? undefined;
  const [page, setPage] = useState(1);
  const [announcements, setAnnouncements] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

  const [groupBuys, setGroupBuys] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  function load() {
    setError(false);
    setAnnouncements(null);
    getMyAnnouncements(token, { groupBuyId: filterGroupBuyId, page })
      .then((response) => {
        setAnnouncements(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filterGroupBuyId]);

  useEffect(() => {
    getMyGroupBuys(token, { pageSize: 50 }).then((response) => setGroupBuys(response.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setSubmitError(null);
    setShowForm(true);
  }

  function openEditForm(announcement) {
    setEditingId(announcement.id);
    setForm({
      audience_scope: announcement.audience_scope,
      group_buy_id: announcement.group_buy_id ?? "",
      title: announcement.title,
      content: announcement.content,
      is_public: announcement.is_public,
    });
    setSubmitError(null);
    setShowForm(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (editingId) {
        await updateAnnouncement(
          editingId,
          { title: form.title, content: form.content, is_public: form.is_public },
          token,
        );
      } else {
        await createAnnouncement(
          {
            audience_scope: form.audience_scope,
            group_buy_id: form.audience_scope === "group_buy_unfinished" ? form.group_buy_id : null,
            title: form.title,
            content: form.content,
            is_public: form.is_public,
          },
          token,
        );
      }
      setShowForm(false);
      load();
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "發布公告時發生錯誤，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteAnnouncement(deleteTarget, token);
      setDeleteTarget(null);
      load();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="group-buy-card-row">
        <div>
          <h1>公告管理</h1>
          <p className="helper-text">管理團主整體公告與特定開團公告。</p>
        </div>
        <Button onClick={openCreateForm}>+ 新增公告</Button>
      </div>

      {/* 篩選中要讓團主看得出來現在不是全部公告，否則會以為公告不見了 */}
      {filterGroupBuyId && (
        <div className="ann-filter-bar">
          <span>
            目前只顯示
            <strong>
              {groupBuys.find((groupBuy) => groupBuy.id === filterGroupBuyId)?.activity.name ??
                "指定開團"}
            </strong>
            的公告
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setSearchParams({});
              setPage(1);
            }}
          >
            顯示全部公告
          </button>
        </div>
      )}

      <div className="two-col-section">
        <div>
          {error ? (
            <ErrorState onRetry={load} />
          ) : announcements === null ? (
            <PageLoader />
          ) : announcements.length === 0 ? (
            <EmptyState title="尚未發布任何公告。" />
          ) : (
            <>
              {announcements.map((announcement) => (
                <div key={announcement.id} className="group-buy-card">
                  <div className="group-buy-card-row">
                    <span className="status-badge status-badge-info">
                      {announcement.audience_scope === "leader_unfinished" ? "團主整體公告" : "特定開團公告"}
                    </span>
                    <span className={`status-badge ${announcement.is_public ? "status-badge-success" : "status-badge-warning"}`}>
                      {announcement.is_public ? "公開" : "僅通知相關會員"}
                    </span>
                    <span className="helper-text" style={{ marginLeft: "auto" }}>
                      {formatDateTime(announcement.published_at)}
                    </span>
                  </div>
                  <h3 style={{ margin: "0.4rem 0" }}>{announcement.title}</h3>
                  <p style={{ margin: 0 }}>{announcement.content}</p>
                  <p className="helper-text">通知對象人數：{announcement.recipient_count}</p>
                  <div className="group-buy-card-row">
                    <Button variant="secondary" onClick={() => openEditForm(announcement)}>
                      編輯
                    </Button>
                    <Button variant="danger" onClick={() => setDeleteTarget(announcement.id)}>
                      刪除
                    </Button>
                  </div>
                </div>
              ))}
              <Pagination page={pagination.page} totalPages={pagination.total_pages} onPageChange={setPage} />
            </>
          )}
        </div>

        {showForm && (
          <div className="group-buy-card">
            <div className="group-buy-card-row">
              <h2 className="section-title" style={{ marginBottom: 0 }}>
                {editingId ? "編輯公告" : "新增公告"}
              </h2>
              <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-field">
                <label>公告標題</label>
                <input
                  value={form.title}
                  onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                  required
                />
              </div>

              {!editingId && (
                <>
                  <div className="form-field">
                    <label>公告類型</label>
                    <label style={{ display: "block" }}>
                      <input
                        type="radio"
                        checked={form.audience_scope === "leader_unfinished"}
                        onChange={() => setForm((prev) => ({ ...prev, audience_scope: "leader_unfinished" }))}
                      />{" "}
                      團主整體公告
                    </label>
                    <label style={{ display: "block" }}>
                      <input
                        type="radio"
                        checked={form.audience_scope === "group_buy_unfinished"}
                        onChange={() => setForm((prev) => ({ ...prev, audience_scope: "group_buy_unfinished" }))}
                      />{" "}
                      特定開團公告
                    </label>
                  </div>

                  {form.audience_scope === "group_buy_unfinished" && (
                    <div className="form-field">
                      <label>指定開團</label>
                      <select
                        value={form.group_buy_id}
                        onChange={(event) => setForm((prev) => ({ ...prev, group_buy_id: event.target.value }))}
                        required
                      >
                        <option value="">請選擇開團</option>
                        {groupBuys.map((groupBuy) => (
                          <option key={groupBuy.id} value={groupBuy.id}>
                            {groupBuy.activity.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </>
              )}

              <div className="form-field">
                <label>公開狀態</label>
                <label style={{ display: "block" }}>
                  <input
                    type="radio"
                    checked={form.is_public}
                    onChange={() => setForm((prev) => ({ ...prev, is_public: true }))}
                  />{" "}
                  公開顯示並通知相關會員
                </label>
                <label style={{ display: "block" }}>
                  <input
                    type="radio"
                    checked={!form.is_public}
                    onChange={() => setForm((prev) => ({ ...prev, is_public: false }))}
                  />{" "}
                  僅通知相關會員
                </label>
              </div>

              <div className="form-field">
                <label>公告內容</label>
                <textarea
                  rows={6}
                  maxLength={1000}
                  value={form.content}
                  onChange={(event) => setForm((prev) => ({ ...prev, content: event.target.value }))}
                  required
                />
              </div>

              {submitError && <Alert type="error">{submitError}</Alert>}

              <div className="group-buy-card-row">
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  取消
                </Button>
                <Button type="submit" loading={submitting}>
                  {editingId ? "儲存變更" : "發布公告"}
                </Button>
              </div>
            </form>
          </div>
        )}
      </div>

      {deleteTarget && (
        <ConfirmModal
          title="刪除公告"
          message="確定要刪除此公告嗎？相關通知也會一併移除，此操作無法復原。"
          confirmLabel="確定刪除"
          danger
          loading={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </>
  );
}
