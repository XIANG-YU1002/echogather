import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getGroupLeaderOrders, markAllOrdersShipped } from "../../api/groupLeaderOrders.js";
import { getMyGroupBuys } from "../../api/groupLeaderGroupBuys.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import {
  AlertTriangleIcon,
  BagIcon,
  CheckCircleIcon,
  ClipboardIcon,
  CreditCardIcon,
  HourglassIcon,
  SearchIcon,
  TagIcon,
} from "../../components/common/icons.jsx";

// 依圖 25：六張統計卡。key 對應後端 summary 欄位；點擊切換狀態篩選。
const SUMMARY_CARDS = [
  {
    key: "pending_confirmation",
    label: "待確認",
    status: "pending_confirmation",
    Icon: ClipboardIcon,
    tone: "purple",
  },
  {
    key: "pending_payment",
    label: "待付款",
    status: "pending_payment",
    Icon: BagIcon,
    tone: "orange",
  },
  { key: "paid", label: "已付款", status: "paid", Icon: CreditCardIcon, tone: "blue" },
  { key: "shipped", label: "已出貨", status: "shipped", Icon: TagIcon, tone: "green" },
  {
    key: "completed",
    label: "已完成",
    status: "completed",
    Icon: CheckCircleIcon,
    tone: "green",
  },
  {
    key: "pending_cancellation",
    label: "待處理取消申請",
    Icon: HourglassIcon,
    tone: "red",
    cancellationFilter: true,
  },
];

// 不放「待處理」——它就是待確認＋待付款，兩者已各有頁籤（使用者 2026-07-29 指示）。
// 但儀表板的「待處理訂單」卡仍會帶 ?status=pending 進來，該情況以提示條說明。
const STATUS_TABS = [
  { value: undefined, label: "全部" },
  { value: "pending_confirmation", label: "待確認" },
  { value: "pending_payment", label: "待付款" },
  { value: "paid", label: "已付款" },
  { value: "shipped", label: "已出貨" },
  { value: "completed", label: "已完成" },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50];

function formatDateTime(isoString) {
  const date = new Date(isoString);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`;
}

export default function OrderListPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const groupBuyId = searchParams.get("group_buy_id") ?? undefined;

  // 狀態篩選以網址為單一來源：從儀表板帶 ?status=pending 進來後若只改元件狀態，
  // 網址仍留著舊參數，重新整理就會跳回原本的篩選。
  const status = searchParams.get("status") ?? undefined;
  const onlyPendingCancellation = searchParams.get("has_pending_cancellation") === "true";

  const [activityId, setActivityId] = useState("");
  const [keyword, setKeyword] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  // 畫面預設「從新到舊」（使用者 2026-07-29 裁決）。
  // API 本身仍以先喊先得為預設（Business Rules §24.1），這裡明確帶參數覆寫。
  const [newestFirst, setNewestFirst] = useState(true);
  const [page, setPage] = useState(1);
  // 依圖 25 預設每頁 10 筆
  const [pageSize, setPageSize] = useState(10);
  const [orders, setOrders] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(false);
  const [confirmShipAll, setConfirmShipAll] = useState(false);
  const [shippingAll, setShippingAll] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // 活動篩選下拉的選項：從自己的開團推導，避免列出從未開團的活動
  const [myGroupBuys, setMyGroupBuys] = useState([]);

  function load() {
    setError(false);
    setOrders(null);
    getGroupLeaderOrders(token, {
      status,
      groupBuyId,
      activityId: activityId || undefined,
      hasPendingCancellation: onlyPendingCancellation ? true : undefined,
      keyword: keyword || undefined,
      newestFirst: newestFirst ? true : undefined,
      page,
      pageSize,
    })
      .then((response) => {
        setOrders(response.data);
        setPagination(response.pagination);
        setSummary(response.summary);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, groupBuyId, activityId, onlyPendingCancellation, keyword, newestFirst, page, pageSize]);

  useEffect(() => {
    getMyGroupBuys(token, { pageSize: 50 })
      .then((response) => setMyGroupBuys(response.data))
      .catch(() => setMyGroupBuys([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activityOptions = useMemo(() => {
    const seen = new Map();
    myGroupBuys.forEach((groupBuy) => {
      if (!seen.has(groupBuy.activity.id)) {
        seen.set(groupBuy.activity.id, groupBuy.activity.name);
      }
    });
    return [...seen.entries()].map(([id, name]) => ({ id, name }));
  }, [myGroupBuys]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    setPage(1);
    setKeyword(keywordInput.trim());
  }

  /**
   * 更新狀態篩選並同步網址，讓重新整理後的畫面與目前選擇一致。
   * 兩個參數互斥：選了狀態就清掉取消申請篩選，反之亦然。
   */
  function applyFilter({ nextStatus, pendingCancellation }) {
    const params = new URLSearchParams(searchParams);
    if (nextStatus) {
      params.set("status", nextStatus);
    } else {
      params.delete("status");
    }
    if (pendingCancellation) {
      params.set("has_pending_cancellation", "true");
    } else {
      params.delete("has_pending_cancellation");
    }
    setSearchParams(params, { replace: true });
    setPage(1);
  }

  /** 統計卡：點待處理取消申請切換該篩選，其餘切換狀態（點第二次取消）。 */
  function handleCardClick(card) {
    if (card.cancellationFilter) {
      applyFilter({ pendingCancellation: !onlyPendingCancellation });
      return;
    }
    applyFilter({ nextStatus: status === card.status ? undefined : card.status });
  }

  async function handleShipAll() {
    setShippingAll(true);
    setFeedback(null);
    try {
      const response = await markAllOrdersShipped(groupBuyId, token);
      const { shipped_count, skipped_pending_confirmation, skipped_pending_payment } =
        response.data;
      const skipped = skipped_pending_confirmation + skipped_pending_payment;
      setFeedback({
        type: shipped_count > 0 ? "success" : "info",
        message:
          shipped_count > 0
            ? `已將 ${shipped_count} 張已付款訂單標記為已出貨。` +
              (skipped > 0
                ? `另有 ${skipped} 張尚未進入可出貨狀態（待確認 ${skipped_pending_confirmation} 張、待付款 ${skipped_pending_payment} 張），未受影響。`
                : "")
            : "此開團目前沒有「已付款」狀態的訂單可出貨。",
      });
      setConfirmShipAll(false);
      setPage(1);
      load();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err instanceof ApiError ? err.message : "批次出貨時發生錯誤，請稍後再試。",
      });
    } finally {
      setShippingAll(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>訂單管理</h1>
        <p className="helper-text">管理所有開團活動的訂單，掌握處理進度與狀態</p>
        {groupBuyId && (
          <p className="helper-text">
            篩選中：僅顯示此開團的訂單 <Link to="/group-leader/orders">清除篩選</Link>
          </p>
        )}
      </div>

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      {/* 從儀表板「待處理訂單」卡進來時沒有對應頁籤，用提示條說明目前的篩選 */}
      {status === "pending" && (
        <div className="ann-filter-bar">
          <span>目前顯示待處理訂單（待確認＋待付款）</span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => applyFilter({})}
          >
            顯示全部訂單
          </button>
        </div>
      )}

      {summary && (
        <div className="ol-summary">
          {SUMMARY_CARDS.map((card) => {
            // 選了複合值「待處理」時，待確認與待付款兩張卡都算選中
            const active = card.cancellationFilter
              ? onlyPendingCancellation
              : status === card.status ||
                (status === "pending" &&
                  ["pending_confirmation", "pending_payment"].includes(card.status));
            return (
              <button
                type="button"
                key={card.key}
                className={`stat-card stat-card--icon ol-summary-card${active ? " is-active" : ""}`}
                onClick={() => handleCardClick(card)}
                aria-pressed={active}
              >
                <span className={`dash-icon ${card.tone}`}>
                  <card.Icon className="dash-icon-svg" />
                </span>
                <span className="stat-card-text">
                  <span className="stat-card-label">{card.label}</span>
                  <span className="stat-card-value">{summary[card.key]}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="ol-toolbar">
        <div className="gbl-tabs">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              className={`gbl-tab${
                status === tab.value && !onlyPendingCancellation ? " is-active" : ""
              }`}
              onClick={() => applyFilter({ nextStatus: tab.value })}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <select
          aria-label="依活動篩選"
          className="ol-activity-select"
          value={activityId}
          onChange={(event) => {
            setActivityId(event.target.value);
            setPage(1);
          }}
        >
          <option value="">所有活動</option>
          {activityOptions.map((activity) => (
            <option key={activity.id} value={activity.id}>
              {activity.name}
            </option>
          ))}
        </select>

        <form className="search-input ol-search" onSubmit={handleSearchSubmit} role="search">
          <input
            type="search"
            placeholder="搜尋訂單編號或會員名稱"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            aria-label="搜尋訂單編號或會員名稱"
          />
          <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
            <SearchIcon className="icon-search" />
          </button>
        </form>

        <select
          aria-label="排序方式"
          className="ol-sort-select"
          value={newestFirst ? "newest" : "oldest"}
          onChange={(event) => {
            setNewestFirst(event.target.value === "newest");
            setPage(1);
          }}
        >
          {/* 預設為從舊到新，即 Business Rules §24.1 的先喊先得 */}
          <option value="oldest">從舊到新</option>
          <option value="newest">從新到舊</option>
        </select>
      </div>

      {groupBuyId && (
        <div className="gl-bulk-actions">
          <Button variant="secondary" onClick={() => setConfirmShipAll(true)}>
            一鍵標記全團已出貨
          </Button>
          <span className="helper-text">
            會將此開團所有「已付款」訂單一次標記為已出貨並通知團員；其他狀態的訂單不受影響。
          </span>
        </div>
      )}

      {error ? (
        <ErrorState onRetry={load} />
      ) : orders === null ? (
        <PageLoader />
      ) : orders.length === 0 ? (
        <EmptyState
          title="沒有符合的訂單。"
          description={keyword ? `找不到符合「${keyword}」的訂單。` : undefined}
        />
      ) : (
        <>
          <div className="table-wrap">
            <table className="table ol-table">
              <thead>
                <tr>
                  <th>訂單編號</th>
                  <th>開團</th>
                  <th>會員</th>
                  <th>商品摘要</th>
                  <th>商品總額</th>
                  <th>狀態</th>
                  <th>提交時間</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.order_number}</td>
                    <td>
                      <span className="ol-group-buy">
                        <span className="ol-group-buy-name">
                          {order.activity_name}｜第 {order.round_number} 團
                        </span>
                        <span
                          className={`status-badge ${
                            order.group_buy_status === "open"
                              ? "status-badge-success"
                              : "status-badge-neutral"
                          }`}
                        >
                          {order.group_buy_status === "open" ? "進行中" : "已結單"}
                        </span>
                      </span>
                    </td>
                    <td>
                      <span className="dash-applicant">
                        {order.member_avatar_url ? (
                          <img
                            className="avatar-circle avatar-circle-sm"
                            src={resolveMediaUrl(order.member_avatar_url)}
                            alt=""
                          />
                        ) : (
                          <span className="avatar-circle avatar-circle-sm" aria-hidden="true">
                            {order.member_nickname?.[0]?.toUpperCase() ?? "?"}
                          </span>
                        )}
                        {order.member_nickname}
                      </span>
                    </td>
                    <td>
                      <span className="ol-items">
                        {order.representative_image_url && (
                          <img
                            className="ol-item-image"
                            src={resolveMediaUrl(order.representative_image_url)}
                            alt=""
                          />
                        )}
                        <span className="ol-item-text">
                          <span>{order.item_summary}</span>
                          <span className="ol-item-count">
                            共 {order.total_quantity} 件商品
                          </span>
                        </span>
                      </span>
                    </td>
                    <td>NT$ {order.product_total_amount}</td>
                    <td>
                      <span className="ol-status">
                        <StatusBadge domain="order" value={order.status} />
                        {order.has_pending_cancellation && (
                          <span className="ol-cancel-note">
                            <AlertTriangleIcon />
                            有取消申請
                          </span>
                        )}
                      </span>
                    </td>
                    <td>{formatDateTime(order.created_at)}</td>
                    <td>
                      <Link className="ol-view-btn" to={`/group-leader/orders/${order.id}`}>
                        <ClipboardIcon />
                        查看訂單
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="gbl-footer">
            <Pagination
              page={pagination.page}
              totalPages={pagination.total_pages}
              onPageChange={setPage}
            />
            <label className="gbl-page-size">
              每頁顯示
              <select
                aria-label="每頁顯示筆數"
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(1);
                }}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
              筆
            </label>
          </div>
        </>
      )}

      {confirmShipAll && (
        <ConfirmModal
          title="一鍵標記全團已出貨"
          message="將把此開團所有「已付款」訂單一次標記為已出貨，並通知每位團員。其他狀態的訂單不受影響。此操作無法復原，確定要繼續嗎？"
          confirmLabel="確定出貨"
          loading={shippingAll}
          onCancel={() => setConfirmShipAll(false)}
          onConfirm={handleShipAll}
        />
      )}
    </>
  );
}
