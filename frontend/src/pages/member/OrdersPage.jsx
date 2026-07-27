import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMyOrders } from "../../api/orders.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import { CalendarIcon, ClipboardIcon } from "../../components/common/icons.jsx";

const STATUS_TABS = [
  { value: "", label: "全部訂單" },
  { value: "pending_confirmation", label: "等待團主確認" },
  { value: "pending_payment", label: "等待付款" },
  { value: "paid", label: "已付款" },
  { value: "shipped", label: "已出貨" },
  { value: "completed", label: "已完成" },
  { value: "rejected", label: "已拒絕" },
  { value: "cancelled", label: "已取消" },
];

const DATE_RANGES = [
  { value: "", label: "全部時間" },
  { value: "7", label: "近 7 天" },
  { value: "30", label: "近 30 天" },
  { value: "90", label: "近 90 天" },
];

const PAGE_SIZES = [10, 20, 50];

const EMPTY_FILTERS = {
  status: "",
  createdWithinDays: "",
  activityName: "",
  groupLeaderName: "",
};

function formatDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export default function OrdersPage() {
  const { token } = useAuth();

  // applied = 實際送出查詢的條件；draft = 篩選卡上尚未套用的輸入值
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [draft, setDraft] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [orders, setOrders] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    setOrders(null);
    getMyOrders(token, {
      status: applied.status || undefined,
      activityName: applied.activityName,
      groupLeaderName: applied.groupLeaderName,
      createdWithinDays: applied.createdWithinDays,
      page,
      pageSize,
    })
      .then((response) => {
        setOrders(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applied, page, pageSize]);

  function selectTab(value) {
    setPage(1);
    setDraft((prev) => ({ ...prev, status: value }));
    setApplied((prev) => ({ ...prev, status: value }));
  }

  function applyFilters() {
    setPage(1);
    setApplied(draft);
  }

  function resetFilters() {
    setPage(1);
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
  }

  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "我的訂單" }]} />

      <div className="page-head">
        <span className="page-head-badge">
          <ClipboardIcon />
        </span>
        <div>
          <h1>我的訂單</h1>
          <p>查看您所有的訂單狀態與詳細資訊。</p>
        </div>
      </div>

      <div className="ol-tabs" role="tablist">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value || "all"}
            type="button"
            role="tab"
            aria-selected={applied.status === tab.value}
            className={`ol-tab${applied.status === tab.value ? " active" : ""}`}
            onClick={() => selectTab(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="ol-layout">
        <div>
          {error ? (
            <ErrorState onRetry={load} />
          ) : orders === null ? (
            <PageLoader />
          ) : orders.length === 0 ? (
            <EmptyState title="目前沒有符合的訂單。" />
          ) : (
            <div className="gb-panel ol-panel">
              <p className="ol-count">共 {pagination.total_items} 筆訂單</p>

              <div className="table-wrap" style={{ border: "none" }}>
                <table className="table ol-table">
                  <thead>
                    <tr>
                      <th>訂單資訊</th>
                      <th>活動 / 團主</th>
                      <th className="ol-num">商品總額</th>
                      <th>狀態</th>
                      <th>建立時間</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <div className="ol-order">
                            <MediaImage
                              className="ol-thumb"
                              src={order.representative_image_url}
                              alt=""
                            />
                            <div className="ol-order-text">
                              <span className="ol-order-no">{order.order_number}</span>
                              <span className="ol-order-items">{order.item_count} 項商品</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="ol-activity">
                            <span className="ol-activity-name">{order.activity_name}</span>
                            <span className="ol-leader-name">{order.group_leader_name}</span>
                          </div>
                        </td>
                        <td className="ol-num">NT$ {order.product_total_amount}</td>
                        <td>
                          <StatusBadge domain="order" value={order.status} />
                          {order.status === "rejected" && order.rejection_reason && (
                            <Link className="ol-reject-link" to={`/orders/${order.id}`}>
                              查看原因
                            </Link>
                          )}
                        </td>
                        <td className="ol-time">{formatDateTime(order.created_at)}</td>
                        <td>
                          <Link className="btn btn-secondary ol-detail-btn" to={`/orders/${order.id}`}>
                            查看詳情
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="ol-footer">
                <Pagination
                  page={pagination.page}
                  totalPages={pagination.total_pages}
                  onPageChange={setPage}
                />
                <label className="ol-page-size">
                  每頁顯示
                  <select
                    value={pageSize}
                    onChange={(event) => {
                      setPage(1);
                      setPageSize(Number(event.target.value));
                    }}
                  >
                    {PAGE_SIZES.map((size) => (
                      <option key={size} value={size}>
                        {size} 筆
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          )}
        </div>

        <aside className="ol-side">
          <div className="gb-panel">
            <h2 className="ol-filter-title">篩選條件</h2>

            <label className="ol-field">
              訂單狀態
              <select
                value={draft.status}
                onChange={(event) => setDraft((p) => ({ ...p, status: event.target.value }))}
              >
                <option value="">全部狀態</option>
                {STATUS_TABS.filter((t) => t.value).map((tab) => (
                  <option key={tab.value} value={tab.value}>
                    {tab.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="ol-field">
              時間範圍
              <span className="ol-field-icon-wrap">
                <CalendarIcon className="ol-field-icon" />
                <select
                  value={draft.createdWithinDays}
                  onChange={(event) =>
                    setDraft((p) => ({ ...p, createdWithinDays: event.target.value }))
                  }
                >
                  {DATE_RANGES.map((range) => (
                    <option key={range.value || "all"} value={range.value}>
                      {range.label}
                    </option>
                  ))}
                </select>
              </span>
            </label>

            <label className="ol-field">
              活動名稱
              <input
                value={draft.activityName}
                placeholder="請輸入活動名稱"
                onChange={(event) => setDraft((p) => ({ ...p, activityName: event.target.value }))}
              />
            </label>

            <label className="ol-field">
              團主名稱
              <input
                value={draft.groupLeaderName}
                placeholder="請輸入團主名稱"
                onChange={(event) =>
                  setDraft((p) => ({ ...p, groupLeaderName: event.target.value }))
                }
              />
            </label>

            <div className="ol-filter-actions">
              <button type="button" className="btn btn-secondary" onClick={resetFilters}>
                重設篩選
              </button>
              <button type="button" className="btn btn-primary" onClick={applyFilters}>
                套用篩選
              </button>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
