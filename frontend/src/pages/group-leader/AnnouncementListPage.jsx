import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getMyGroupBuys } from "../../api/groupLeaderGroupBuys.js";
import {
  createAnnouncement,
  deleteAnnouncement,
  getMyAnnouncements,
  getRecipientPreview,
  updateAnnouncement,
} from "../../api/groupLeaderAnnouncements.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import ListFooter from "../../components/common/ListFooter.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  PencilIcon,
  PlusCircleIcon,
  TrashIcon,
  UsersIcon,
} from "../../components/common/icons.jsx";

/** 依圖 27，發布時間的日期與時間分兩行顯示。 */
function formatDate(isoString) {
  const date = new Date(isoString);
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`;
}

function formatTime(isoString) {
  const date = new Date(isoString);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const CONTENT_MAX_LENGTH = 1000;
const TITLE_MAX_LENGTH = 80;

// 抽屜寬度，必須與 CSS 的 .ann-form-panel 寬度一致（收窄量靠它換算）
const DRAWER_WIDTH = 400;

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
  // 依圖 27 預設每頁 10 筆
  const [pageSize, setPageSize] = useState(10);
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
  // 圖 27 的「通知對象預覽」：發布前由後端即時算出會通知誰、幾個人
  const [preview, setPreview] = useState(null);

  function load() {
    setError(false);
    setAnnouncements(null);
    getMyAnnouncements(token, { groupBuyId: filterGroupBuyId, page, pageSize })
      .then((response) => {
        setAnnouncements(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, filterGroupBuyId]);

  useEffect(() => {
    getMyGroupBuys(token, { pageSize: 50 }).then((response) => setGroupBuys(response.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 抽屜開啟時要做兩件事：
  // 1. 抽屜頂端貼齊 header 底部——header 是 sticky 且高度由內容決定，沒有固定值，
  //    只能量實際高度。
  // 2. 內容區向左收窄，讓表格（含最右邊的操作欄）完整可見。收窄量用「量測」而非
  //    CSS calc 推算：.container 有 max-width 且居中、後台還有側邊欄，
  //    推算值與實際重疊量對不上。量測前先把 padding 歸零，否則會拿到上一次
  //    收窄後的位置而愈收愈多。
  useEffect(() => {
    if (!showForm) return undefined;

    const content = document.querySelector(".member-content");

    function syncDrawerLayout() {
      const header = document.querySelector(".app-header");
      const headerHeight = header ? header.getBoundingClientRect().height : 0;
      document.documentElement.style.setProperty("--ann-drawer-top", `${headerHeight}px`);

      if (!content) return;
      // 量測前歸零，否則量到的是上一次收窄後的位置而愈收愈多
      content.style.paddingRight = "0px";

      // 直接量抽屜的實際左緣，不用 window.innerWidth 推算：
      // innerWidth 含垂直滾動條寬度，而 getBoundingClientRect 的座標不含，
      // 兩者混用會少算約 15px，剛好讓最右邊的操作欄被切掉一小條。
      const panel = document.querySelector(".ann-form-panel");
      const viewportWidth = document.documentElement.clientWidth;
      const drawerLeft = panel
        ? panel.getBoundingClientRect().left
        : viewportWidth - Math.min(DRAWER_WIDTH, viewportWidth);

      const overlap = content.getBoundingClientRect().right - drawerLeft;
      // 視窗窄到抽屜佔滿整頁時就不收窄（也收不出空間）
      const shift = viewportWidth <= 1023 ? 0 : Math.max(0, Math.ceil(overlap) + 24);
      content.style.paddingRight = `${shift}px`;
    }

    syncDrawerLayout();
    window.addEventListener("resize", syncDrawerLayout);

    return () => {
      window.removeEventListener("resize", syncDrawerLayout);
      if (content) {
        content.style.paddingRight = "";
      }
    };
  }, [showForm]);

  // 只有新增時需要預覽：編輯不能改通知對象（後端只接受標題／內容／是否公開）。
  useEffect(() => {
    if (!showForm || editingId) {
      setPreview(null);
      return;
    }
    if (form.audience_scope === "group_buy_unfinished" && !form.group_buy_id) {
      setPreview(null);
      return;
    }
    getRecipientPreview(token, {
      audienceScope: form.audience_scope,
      groupBuyId: form.group_buy_id,
    })
      .then((response) => setPreview(response.data))
      .catch(() => setPreview(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showForm, editingId, form.audience_scope, form.group_buy_id]);

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

  function groupBuyLabel(announcement) {
    if (!announcement.group_buy_activity_name) return "指定開團";
    return announcement.group_buy_round_number
      ? `${announcement.group_buy_activity_name}｜第 ${announcement.group_buy_round_number} 團`
      : announcement.group_buy_activity_name;
  }

  return (
    <>
      <div className="page-header ann-header">
        <h1>公告管理</h1>
        <p className="helper-text">管理團主整體公告與特定開團公告</p>
      </div>

      {/* 依圖 27，新增按鈕在副標下方、左對齊 */}
      <div className="ann-actions">
        <Button onClick={openCreateForm}>
          <PlusCircleIcon />
          新增公告
        </Button>
      </div>

      {/* 篩選中要讓團主看得出來現在不是全部公告，否則會以為公告不見了
          （從圖 22 的「團購公告」分頁帶 group_buy_id 進來時顯示） */}
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

      <div className="ann-layout">
        <div className="ann-panel">
          {error ? (
            <ErrorState onRetry={load} />
          ) : announcements === null ? (
            <PageLoader />
          ) : announcements.length === 0 ? (
            <EmptyState title="尚未發布任何公告。" />
          ) : (
            <>
              <div className="table-wrap">
                <table className="table ann-table">
                  <thead>
                    <tr>
                      <th>公告標題</th>
                      <th>公告類型</th>
                      <th>目標與對象</th>
                      <th>公開狀態</th>
                      <th>發布時間</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {announcements.map((announcement) => {
                      const isLeaderWide = announcement.audience_scope === "leader_unfinished";
                      return (
                        <tr key={announcement.id}>
                          <td>
                            <span className="ann-title">{announcement.title}</span>
                            {/* 參考圖沒有內容欄，但使用者要求加一行摘要，
                                免得每則都得點編輯才知道寫了什麼 */}
                            <span className="ann-excerpt">{announcement.content}</span>
                          </td>
                          <td>
                            <span className="status-badge status-badge-info">
                              {isLeaderWide ? "團主整體公告" : "特定開團公告"}
                            </span>
                          </td>
                          <td>
                            {!isLeaderWide && (
                              <span className="ann-target-block">
                                <span className="ann-target-label">指定開團</span>
                                <span className="ann-target-value">
                                  {groupBuyLabel(announcement)}
                                </span>
                              </span>
                            )}
                            <span className="ann-target-block">
                              <span className="ann-target-label">通知對象</span>
                              <span className="ann-target-value">
                                {isLeaderWide
                                  ? "所有未完成訂單會員"
                                  : "該開團未完成訂單會員"}
                                （{announcement.recipient_count} 人）
                              </span>
                            </span>
                          </td>
                          <td>
                            <span
                              className={`status-badge ${
                                announcement.is_public
                                  ? "status-badge-success"
                                  : "status-badge-warning"
                              }`}
                            >
                              {announcement.is_public ? "公開" : "僅通知相關會員"}
                            </span>
                          </td>
                          <td>
                            <span className="ann-time">
                              <span>{formatDate(announcement.published_at)}</span>
                              <span>{formatTime(announcement.published_at)}</span>
                            </span>
                          </td>
                          <td>
                            <div className="ann-row-actions">
                              <button
                                type="button"
                                className="ann-action-btn edit"
                                onClick={() => openEditForm(announcement)}
                              >
                                <PencilIcon />
                                編輯
                              </button>
                              <button
                                type="button"
                                className="ann-action-btn delete"
                                onClick={() => setDeleteTarget(announcement.id)}
                              >
                                <TrashIcon />
                                刪除
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <ListFooter
                pagination={pagination}
                onPageChange={setPage}
                pageSize={pageSize}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setPage(1);
                }}
              />
            </>
          )}
        </div>

        {showForm && (
          <aside className="ann-form-panel">
            <div className="ann-form-head">
              <h2>{editingId ? "編輯公告" : "新增公告"}</h2>
              <button
                type="button"
                className="modal-close-btn"
                aria-label="關閉"
                onClick={() => setShowForm(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-field">
                <label htmlFor="ann-title">公告標題</label>
                <input
                  id="ann-title"
                  value={form.title}
                  maxLength={TITLE_MAX_LENGTH}
                  placeholder="請輸入公告標題"
                  onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                  required
                />
              </div>

              {/* 編輯時不顯示公告類型與指定開團：後端只接受改標題／內容／是否公開，
                  通知對象在發布時就固定了 */}
              {!editingId && (
                <>
                  <div className="form-field">
                    <span className="gbe-label">公告類型</span>
                    <label className="ann-radio">
                      <input
                        type="radio"
                        name="ann-scope"
                        checked={form.audience_scope === "leader_unfinished"}
                        onChange={() =>
                          setForm((prev) => ({ ...prev, audience_scope: "leader_unfinished" }))
                        }
                      />
                      <span>團主整體公告</span>
                    </label>
                    <label className="ann-radio">
                      <input
                        type="radio"
                        name="ann-scope"
                        checked={form.audience_scope === "group_buy_unfinished"}
                        onChange={() =>
                          setForm((prev) => ({ ...prev, audience_scope: "group_buy_unfinished" }))
                        }
                      />
                      <span>特定開團公告</span>
                    </label>
                  </div>

                  {form.audience_scope === "group_buy_unfinished" && (
                    <div className="form-field">
                      <label htmlFor="ann-group-buy">指定開團</label>
                      <select
                        id="ann-group-buy"
                        value={form.group_buy_id}
                        onChange={(event) =>
                          setForm((prev) => ({ ...prev, group_buy_id: event.target.value }))
                        }
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
                <span className="gbe-label">公開狀態</span>
                <label className="ann-radio">
                  <input
                    type="radio"
                    name="ann-public"
                    checked={form.is_public}
                    onChange={() => setForm((prev) => ({ ...prev, is_public: true }))}
                  />
                  <span>公開顯示並通知相關會員</span>
                </label>
                <label className="ann-radio">
                  <input
                    type="radio"
                    name="ann-public"
                    checked={!form.is_public}
                    onChange={() => setForm((prev) => ({ ...prev, is_public: false }))}
                  />
                  <span>僅通知相關會員</span>
                </label>
              </div>

              <div className="form-field ann-content-field">
                <label htmlFor="ann-content">公告內容</label>
                <textarea
                  id="ann-content"
                  rows={8}
                  maxLength={CONTENT_MAX_LENGTH}
                  placeholder="請輸入公告內容..."
                  value={form.content}
                  onChange={(event) => setForm((prev) => ({ ...prev, content: event.target.value }))}
                  required
                />
                <span className="ann-char-count">
                  {form.content.length} / {CONTENT_MAX_LENGTH}
                </span>
              </div>

              {/* 通知對象預覽（依圖 27）。人數由後端即時計算，
                  與實際發送用的是同一組收件人查詢 */}
              {!editingId && (
                <div className="ann-preview">
                  <h3 className="ann-preview-title">通知對象預覽</h3>
                  {preview ? (
                    <div className="ann-preview-body">
                      <span className="ann-preview-icon">
                        <UsersIcon />
                      </span>
                      <span className="ann-preview-text">
                        <span className="ann-preview-label">通知對象：</span>
                        <span className="ann-preview-value">
                          {preview.audience_label}（{preview.recipient_count} 人）
                        </span>
                        <span className="ann-preview-note">
                          {form.is_public
                            ? "此公告會公開顯示，並通知上述對象。"
                            : "此公告將僅通知上述對象。"}
                        </span>
                        {preview.recipient_count === 0 && (
                          <span className="ann-preview-note">
                            目前沒有收件人，公告必須設為公開才能發布。
                          </span>
                        )}
                      </span>
                    </div>
                  ) : (
                    <p className="ann-preview-empty">
                      {form.audience_scope === "group_buy_unfinished"
                        ? "請先選擇開團，即可預覽通知對象。"
                        : "正在計算通知對象…"}
                    </p>
                  )}
                </div>
              )}

              {submitError && <Alert type="error">{submitError}</Alert>}

              <div className="ann-form-actions">
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  取消
                </Button>
                <Button type="submit" loading={submitting}>
                  {editingId ? "儲存變更" : "發布公告"}
                </Button>
              </div>
            </form>
          </aside>
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
