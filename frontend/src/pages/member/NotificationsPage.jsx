import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getNotificationSummary,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../api/notifications.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useNotifications } from "../../context/NotificationContext.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import MediaImage from "../../components/common/MediaImage.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import UnmergeRequestModal from "../../components/common/UnmergeRequestModal.jsx";
import {
  BellIcon,
  ChevronRightIcon,
  ClipboardIcon,
  InfoIcon,
  MegaphoneIcon,
} from "../../components/common/icons.jsx";

const TYPE_LABELS = { system: "系統通知", group_leader: "團主公告" };

const TYPE_TABS = [
  { value: "", label: "全部" },
  { value: "system", label: "系統通知" },
  { value: "group_leader", label: "團主公告" },
];

// 已讀狀態篩選；空字串代表不篩選
const READ_FILTERS = [
  { value: "", label: "全部通知" },
  { value: "false", label: "只看未讀" },
  { value: "true", label: "只看已讀" },
];

const PAGE_SIZE = 10;

// 與 NotificationContext 的未讀數輪詢間隔一致
const POLL_INTERVAL_MS = 30000;

/** 相對時間；超過兩天改顯示日期時間。 */
function formatRelativeTime(isoString) {
  const target = new Date(isoString);
  if (Number.isNaN(target.getTime())) return isoString;
  const minutes = Math.floor((Date.now() - target.getTime()) / 60000);
  if (minutes < 1) return "剛剛";
  if (minutes < 60) return `${minutes} 分鐘前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小時前`;
  const pad = (n) => String(n).padStart(2, "0");
  const time = `${pad(target.getHours())}:${pad(target.getMinutes())}`;
  if (hours < 48) return `昨天 ${time}`;
  return `${target.getFullYear()}/${pad(target.getMonth() + 1)}/${pad(target.getDate())} ${time}`;
}

export default function NotificationsPage() {
  const { token } = useAuth();
  // 與 Header 鈴鐺共用未讀數，這裡標記已讀後鈴鐺紅點會即時消失
  const { refresh: refreshUnreadCount } = useNotifications();
  const [type, setType] = useState("");
  const [readFilter, setReadFilter] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  // 「訂單已合併」通知底下的取消合併申請（使用者 2026-07-30 需求）。
  // 存整則通知，因為要用 source.id 取得對應的訂單。
  const [unmergeTarget, setUnmergeTarget] = useState(null);

  function loadSummary() {
    getNotificationSummary(token)
      .then((response) => setSummary(response.data))
      .catch(() => setSummary(null));
  }

  /**
   * silent：自動刷新時不清空列表、不跳 loading，否則每 30 秒整頁會閃一次。
   * 同購物車數量調整時採用的靜默刷新做法。
   */
  function load({ silent = false } = {}) {
    setError(false);
    if (!silent) {
      setItems(null);
    }
    getNotifications(token, {
      notificationType: type,
      isRead: readFilter,
      page,
      pageSize: PAGE_SIZE,
    })
      .then((response) => {
        setItems(response.data);
        setPagination(response.pagination);
      })
      .catch(() => {
        // 自動刷新失敗時保留現有內容，不要把整頁換成錯誤畫面
        if (!silent) {
          setError(true);
        }
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, readFilter, page]);

  useEffect(() => {
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // 停在通知頁時也要看得到新通知（原本只在進頁面時載入一次，得手動 F5）。
  // 與 NotificationContext 的未讀數同一套機制：定時輪詢 ＋ 切回分頁時立即刷新。
  useEffect(() => {
    if (!token) return undefined;

    function refreshSilently() {
      load({ silent: true });
      loadSummary();
    }
    const timer = setInterval(refreshSilently, POLL_INTERVAL_MS);

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        refreshSilently();
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", refreshSilently);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", refreshSilently);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, type, readFilter, page]);

  async function handleItemClick(notification) {
    if (notification.is_read) return;
    try {
      await markNotificationRead(notification.id, token);
      setItems((prev) =>
        prev ? prev.map((item) => (item.id === notification.id ? { ...item, is_read: true } : item)) : prev,
      );
      loadSummary();
      await refreshUnreadCount();
    } catch {
      // 非關鍵操作，失敗不影響導頁
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true);
    try {
      await markAllNotificationsRead(token);
      setItems((prev) => (prev ? prev.map((item) => ({ ...item, is_read: true })) : prev));
      loadSummary();
      await refreshUnreadCount();
      // 若正在「只看未讀」，標記完應重新查詢（清單會變空）
      if (readFilter === "false") {
        load();
      }
    } finally {
      setMarkingAll(false);
    }
  }

  function selectType(value) {
    setPage(1);
    setType(value);
  }

  const summaryRows = summary
    ? [
        { icon: <BellIcon />, label: "未讀通知", value: summary.unread_count, accent: true },
        { icon: <ClipboardIcon />, label: "系統通知", value: summary.system_count },
        { icon: <MegaphoneIcon />, label: "團主公告", value: summary.group_leader_count },
      ]
    : [];

  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "通知中心" }]} />

      <div className="page-head">
        <span className="page-head-badge">
          <BellIcon />
        </span>
        <div>
          <h1>通知中心</h1>
          <p>查看系統通知與團主公告</p>
        </div>
      </div>

      <div className="nc-layout">
        <div>
          <div className="gb-panel nc-panel">
            {/* 類型頁籤 ＋ 已讀狀態下拉 ＋ 全部標記已讀 */}
            <div className="nc-toolbar">
              <div className="ol-tabs nc-tabs" role="tablist">
                {TYPE_TABS.map((tab) => (
                  <button
                    key={tab.value || "all"}
                    type="button"
                    role="tab"
                    aria-selected={type === tab.value}
                    className={`ol-tab${type === tab.value ? " active" : ""}`}
                    onClick={() => selectType(tab.value)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="nc-toolbar-actions">
                <select
                  className="nc-read-filter"
                  value={readFilter}
                  aria-label="依已讀狀態篩選"
                  onChange={(event) => {
                    setPage(1);
                    setReadFilter(event.target.value);
                  }}
                >
                  {READ_FILTERS.map((option) => (
                    <option key={option.value || "all"} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <Button
                  variant="secondary"
                  loading={markingAll}
                  disabled={summary ? summary.unread_count === 0 : false}
                  onClick={handleMarkAllRead}
                >
                  全部標記為已讀
                </Button>
              </div>
            </div>

            {error ? (
              <ErrorState onRetry={load} />
            ) : items === null ? (
              <PageLoader />
            ) : items.length === 0 ? (
              <EmptyState title="目前沒有符合條件的通知。" />
            ) : (
              <>
                <ul className="nc-list">
                  {items.map((notification) => {
                    const isLeaderAnnouncement =
                      notification.notification_type === "group_leader";
                    const body = (
                      <>
                        <span className="nc-item-avatar">
                          {isLeaderAnnouncement && notification.actor_avatar_url ? (
                            <MediaImage
                              className="nc-item-avatar-img"
                              src={notification.actor_avatar_url}
                              alt={notification.actor_name ?? ""}
                            />
                          ) : (
                            <span
                              className={`nc-item-icon${isLeaderAnnouncement ? " leader" : ""}`}
                            >
                              {isLeaderAnnouncement ? <MegaphoneIcon /> : <ClipboardIcon />}
                            </span>
                          )}
                        </span>

                        <span className="nc-item-main">
                          <span className="nc-item-head">
                            <span
                              className={`nc-type-tag${isLeaderAnnouncement ? " leader" : ""}`}
                            >
                              {TYPE_LABELS[notification.notification_type] ??
                                notification.notification_type}
                            </span>
                            <span className="nc-item-title">{notification.title}</span>
                          </span>
                          <span className="nc-item-message">{notification.message}</span>
                          {isLeaderAnnouncement && notification.actor_name && (
                            <span className="nc-item-actor">— {notification.actor_name}</span>
                          )}
                        </span>

                        <span className="nc-item-meta">
                          <span className="nc-item-time">
                            {formatRelativeTime(notification.created_at)}
                          </span>
                          {!notification.is_read && (
                            <span className="nc-unread-dot" aria-label="未讀" />
                          )}
                        </span>

                        <ChevronRightIcon className="nc-item-arrow" />
                      </>
                    );

                    const className = `nc-item${notification.is_read ? "" : " unread"}`;

                    return (
                      <li key={notification.id}>
                        {notification.target_url ? (
                          <Link
                            className={className}
                            to={notification.target_url}
                            onClick={() => handleItemClick(notification)}
                          >
                            {body}
                          </Link>
                        ) : (
                          <button
                            type="button"
                            className={className}
                            onClick={() => handleItemClick(notification)}
                          >
                            {body}
                          </button>
                        )}
                        {/* 取消合併按鈕必須放在可點擊的通知本體外面，否則會變成
                            巢狀互動元素，而且點按鈕就會被當成點通知而導頁 */}
                        {notification.can_request_unmerge && (
                          <div className="nc-item-actions">
                            <Button
                              variant="secondary"
                              onClick={() => openUnmergeModal(notification)}
                            >
                              取消合併訂單
                            </Button>
                            <span className="nc-item-actions-hint">
                              需由團主確認後才會拆回原本的訂單
                            </span>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>

                <div className="nc-footer">
                  <Pagination
                    page={pagination.page}
                    totalPages={pagination.total_pages}
                    onPageChange={setPage}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        <aside className="od-side">
          <div className="gb-panel">
            <h2 className="fl-sum-title">通知摘要</h2>
            {summary === null ? (
              <p className="od-subtle-block">摘要載入中…</p>
            ) : (
              summaryRows.map((row) => (
                <div className="nc-summary-row" key={row.label}>
                  <span className={`nc-summary-icon${row.accent ? " accent" : ""}`}>{row.icon}</span>
                  <span className="label">{row.label}</span>
                  <span className={`value${row.accent ? " accent" : ""}`}>{row.value}</span>
                </div>
              ))
            )}
          </div>

          <div className="gb-panel">
            <h2 className="fl-sum-title nc-tip-title">
              <InfoIcon />
              小提醒
            </h2>
            <p className="nc-tip-body">
              目前不支援刪除通知，您可以透過標記為已讀來管理通知狀態。
            </p>
          </div>
        </aside>
      </div>

      {unmergeTarget && (
        <UnmergeRequestModal
          orderId={unmergeTarget.source.id}
          onClose={() => setUnmergeTarget(null)}
          // 送出後重新載入：後端在有待處理申請時會把 can_request_unmerge 轉為 false，
          // 按鈕因此消失
          onSubmitted={load}
        />
      )}
    </>
  );
}
