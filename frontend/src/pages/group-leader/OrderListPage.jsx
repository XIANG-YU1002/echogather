import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getGroupLeaderOrders, markAllOrdersShipped } from "../../api/groupLeaderOrders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";

const STATUS_TABS = [
  { value: undefined, label: "全部" },
  { value: "pending_confirmation", label: "待確認" },
  { value: "pending_payment", label: "待付款" },
  { value: "paid", label: "已付款" },
  { value: "shipped", label: "已出貨" },
  { value: "completed", label: "已完成" },
  { value: "rejected", label: "已拒絕" },
  { value: "cancelled", label: "已取消" },
];

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  });
}

export default function OrderListPage() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const groupBuyId = searchParams.get("group_buy_id") ?? undefined;
  const initialStatus = searchParams.get("status") ?? undefined;

  const [status, setStatus] = useState(initialStatus);
  const [keyword, setKeyword] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [page, setPage] = useState(1);
  const [orders, setOrders] = useState(null);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState(false);
  const [confirmShipAll, setConfirmShipAll] = useState(false);
  const [shippingAll, setShippingAll] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function load() {
    setError(false);
    setOrders(null);
    getGroupLeaderOrders(token, { status, groupBuyId, keyword: keyword || undefined, page })
      .then((response) => {
        setOrders(response.data);
        setPagination(response.pagination);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, groupBuyId, keyword, page]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    setPage(1);
    setKeyword(keywordInput.trim());
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
        <p className="helper-text">查看與管理團購訂單狀態。</p>
        {groupBuyId && (
          <p className="helper-text">
            篩選中：僅顯示此開團的訂單 <Link to="/group-leader/orders">清除篩選</Link>
          </p>
        )}
      </div>

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      {groupBuyId ? (
        <div className="gl-bulk-actions">
          <Button variant="secondary" onClick={() => setConfirmShipAll(true)}>
            一鍵標記全團已出貨
          </Button>
          <span className="helper-text">
            會將此開團所有「已付款」訂單一次標記為已出貨並通知團員；其他狀態的訂單不受影響。
          </span>
        </div>
      ) : (
        <p className="helper-text" style={{ marginBottom: "1rem" }}>
          想一次為整團出貨？請從「我的開團」進入該開團的訂單，或在網址帶上 group_buy_id 篩選後即可使用批次出貨。
        </p>
      )}

      <div className="group-buy-card-row" style={{ flexWrap: "wrap", marginBottom: "1rem" }}>
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.label}
            type="button"
            className={`btn ${status === tab.value ? "btn-primary" : "btn-secondary"}`}
            onClick={() => {
              setStatus(tab.value);
              setPage(1);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <form className="search-input" style={{ maxWidth: "360px", marginBottom: "1.5rem" }} onSubmit={handleSearchSubmit}>
        <input
          type="search"
          placeholder="搜尋訂單編號或會員名稱"
          value={keywordInput}
          onChange={(event) => setKeywordInput(event.target.value)}
        />
        <button type="submit">搜尋</button>
      </form>

      {error ? (
        <ErrorState onRetry={load} />
      ) : orders === null ? (
        <PageLoader />
      ) : orders.length === 0 ? (
        <EmptyState title="沒有符合的訂單。" />
      ) : (
        <>
          <p className="helper-text">共 {pagination.total_items} 筆訂單</p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>訂單編號</th>
                  <th>會員</th>
                  <th>活動</th>
                  <th>商品總額</th>
                  <th>訂單狀態</th>
                  <th>下單時間</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.order_number}</td>
                    <td>{order.member_nickname}</td>
                    <td>{order.activity_name}</td>
                    <td>NT$ {order.product_total_amount}</td>
                    <td>
                      <StatusBadge domain="order" value={order.status} />
                      {order.has_pending_cancellation && (
                        <span className="status-badge status-badge-danger" style={{ marginLeft: "0.35rem" }}>
                          取消申請中
                        </span>
                      )}
                    </td>
                    <td>{formatDateTime(order.created_at)}</td>
                    <td>
                      <Link className="btn btn-secondary" to={`/group-leader/orders/${order.id}`}>
                        查看詳情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={pagination.page} totalPages={pagination.total_pages} onPageChange={setPage} />
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
