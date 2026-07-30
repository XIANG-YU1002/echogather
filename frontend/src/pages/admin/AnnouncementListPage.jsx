import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  createAdminAnnouncement,
  deleteAdminAnnouncement,
  getAdminAnnouncements,
  updateAdminAnnouncement,
} from "../../api/adminAnnouncements.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import ListFooter from "../../components/common/ListFooter.jsx";
import { MegaphoneIcon, SearchIcon } from "../../components/common/icons.jsx";

const TITLE_MAX = 80;
const CONTENT_MAX = 2000;
const EMPTY_FORM = { title: "", content: "" };

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  });
}

export default function AnnouncementListPage() {
  const { token } = useAuth();
  // 搜尋關鍵字以網址為單一來源（docs/03 §23a）：只存在元件狀態時，
  // 點側邊選單回到同一路由不會重新掛載元件，搜尋條件就會殘留。
  const [searchParams, setSearchParams] = useSearchParams();
  const keyword = searchParams.get("keyword") ?? "";

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [keywordInput, setKeywordInput] = useState(keyword);
  const [announcements, setAnnouncements] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

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
    getAdminAnnouncements(token, { keyword: keyword || undefined, page, pageSize })
      .then((response) => {
        setAnnouncements(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, page, pageSize]);

  // 網址的關鍵字被外部改掉時（點側邊選單、瀏覽器上一頁），搜尋框要跟著更新
  useEffect(() => {
    setKeywordInput(keyword);
  }, [keyword]);

  // 換關鍵字就回第一頁，否則可能停在超出範圍的頁碼而顯示空清單
  useEffect(() => {
    setPage(1);
  }, [keyword]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    const params = new URLSearchParams(searchParams);
    const next = keywordInput.trim();
    if (next) {
      params.set("keyword", next);
    } else {
      params.delete("keyword");
    }
    setSearchParams(params, { replace: true });
  }

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setSubmitError(null);
    setShowForm(true);
  }

  function openEditForm(announcement) {
    setEditingId(announcement.id);
    setForm({ title: announcement.title, content: announcement.content });
    setSubmitError(null);
    setShowForm(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (editingId) {
        await updateAdminAnnouncement(editingId, form, token);
      } else {
        await createAdminAnnouncement(form, token);
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
      await deleteAdminAnnouncement(deleteTarget, token);
      setDeleteTarget(null);
      load();
    } finally {
      setDeleting(false);
    }
  }

  const total = pagination?.total_items ?? 0;

  return (
    <div className="admin-page">
      <div className="page-header page-header--tight">
        <h1>平台公告管理</h1>
      </div>

      <div className={`announce-layout${showForm ? " with-form" : ""}`}>
        <div className="announce-main">
          <p className="helper-text announce-subtitle">管理平台公告內容，系統將對全部會員發送站內通知。</p>
          <div className="announce-toolbar">
            <Button onClick={openCreateForm}>+ 新增公告</Button>
            <span className="announce-count">
              公告列表　共 {total} 則公告
            </span>
            <form className="search-input admin-toolbar-search announce-search" onSubmit={handleSearchSubmit} role="search">
              <input
                type="search"
                placeholder="搜尋公告標題"
                value={keywordInput}
                onChange={(event) => setKeywordInput(event.target.value)}
                aria-label="搜尋公告標題"
              />
              <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
                <SearchIcon className="icon-search" />
              </button>
            </form>
          </div>

          {error ? (
            <ErrorState onRetry={load} />
          ) : announcements === null ? (
            <PageLoader />
          ) : announcements.length === 0 ? (
            <EmptyState title="尚未發布任何平台公告。" />
          ) : (
            <>
              <div className="announce-list">
                {announcements.map((announcement) => (
                  <article key={announcement.id} className="announce-card">
                    <span className="dash-icon purple announce-card-icon">
                      <MegaphoneIcon className="dash-icon-svg" />
                    </span>
                    <div className="announce-card-body">
                      <h3 className="announce-card-title">{announcement.title}</h3>
                      <p className="announce-card-content">{announcement.content}</p>
                      <div className="announce-card-meta">
                        <span className="announce-target">對象：全部會員</span>
                        <span>更新時間：{formatDateTime(announcement.updated_at)}</span>
                        <span>通知人數：{announcement.recipient_count}</span>
                      </div>
                    </div>
                    <div className="announce-card-actions">
                      <Button variant="secondary" onClick={() => openEditForm(announcement)}>
                        編輯
                      </Button>
                      <Button variant="danger" onClick={() => setDeleteTarget(announcement.id)}>
                        刪除
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
              <ListFooter
                pagination={pagination}
                onPageChange={setPage}
                pageSize={pageSize}
                onPageSizeChange={(n) => {
                  setPageSize(n);
                  setPage(1);
                }}
              />
            </>
          )}
        </div>

        {showForm && (
          <aside className="announce-form-panel">
            <div className="announce-form-head">
              <span className="dash-icon purple">
                <MegaphoneIcon className="dash-icon-svg" />
              </span>
              <h2>{editingId ? "編輯公告" : "新增公告"}</h2>
              <button type="button" className="btn btn-ghost announce-form-close" onClick={() => setShowForm(false)} aria-label="關閉">
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-field">
                <label>公告標題</label>
                <input
                  maxLength={TITLE_MAX}
                  placeholder={`請輸入公告標題（最多 ${TITLE_MAX} 字）`}
                  value={form.title}
                  onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                  required
                />
                <div className="char-count">
                  {form.title.length} / {TITLE_MAX}
                </div>
              </div>
              <div className="form-field">
                <label>公告內容</label>
                <textarea
                  rows={8}
                  maxLength={CONTENT_MAX}
                  placeholder="請輸入公告內容…"
                  value={form.content}
                  onChange={(event) => setForm((prev) => ({ ...prev, content: event.target.value }))}
                  required
                />
                <div className="char-count">
                  {form.content.length} / {CONTENT_MAX}
                </div>
              </div>
              <div className="form-field">
                <label>通知對象</label>
                <select value="all" disabled aria-label="通知對象">
                  <option value="all">全部會員</option>
                </select>
              </div>

              <div className="announce-form-note">
                編輯公告將更新通知內容，系統會重新發送通知給全部會員；刪除公告將移除公告內容並停發相關通知。
              </div>

              {submitError && <Alert type="error">{submitError}</Alert>}

              <div className="announce-form-actions">
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  取消
                </Button>
                <Button type="submit" loading={submitting}>
                  儲存公告
                </Button>
              </div>
            </form>
          </aside>
        )}
      </div>

      {deleteTarget && (
        <ConfirmModal
          title="刪除公告"
          message="確定要刪除此平台公告嗎？相關通知也會一併移除，此操作無法復原。"
          confirmLabel="確定刪除"
          danger
          loading={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}
