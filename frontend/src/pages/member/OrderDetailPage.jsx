import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMyOrderDetail } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "取貨付款",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };
const CANCELLABLE_STATUSES = ["pending_confirmation", "pending_payment", "paid"];
const TIMELINE_STEPS = [
  { key: "pending_confirmation", label: "等待團主確認" },
  { key: "pending_payment", label: "等待付款" },
  { key: "paid", label: "已付款" },
  { key: "shipped", label: "已出貨" },
  { key: "completed", label: "已完成" },
];

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  });
}

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const { token } = useAuth();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);

  function load() {
    setError(null);
    setOrder(null);
    getMyOrderDetail(orderId, token)
      .then((response) => setOrder(response.data))
      .catch((err) => setError(err));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState title="找不到此訂單" description="訂單不存在或不屬於您。" />;
    }
    return <ErrorState onRetry={load} />;
  }

  if (!order) {
    return <PageLoader />;
  }

  const isTerminalOther = order.status === "rejected" || order.status === "cancelled";
  const currentStepIndex = TIMELINE_STEPS.findIndex((step) => step.key === order.status);
  const canCancel = CANCELLABLE_STATUSES.includes(order.status) && !order.pending_cancellation_request;

  return (
    <>
      <div className="page-header">
        <h1>訂單詳情</h1>
      </div>

      <dl className="detail-list">
        <dt>訂單編號</dt>
        <dd>{order.order_number}</dd>
        <dt>建立時間</dt>
        <dd>{formatDateTime(order.created_at)}</dd>
        <dt>目前狀態</dt>
        <dd>
          <StatusBadge domain="order" value={order.status} />
        </dd>
        {order.status === "rejected" && order.rejection_reason && (
          <>
            <dt>拒絕原因</dt>
            <dd>{order.rejection_reason}</dd>
          </>
        )}
      </dl>

      {!isTerminalOther && (
        <div className="group-buy-card-row" style={{ flexWrap: "nowrap", overflowX: "auto", margin: "1.5rem 0" }}>
          {TIMELINE_STEPS.map((step, index) => (
            <span key={step.key} className="helper-text" style={{ display: "flex", alignItems: "center", gap: "0.4rem", whiteSpace: "nowrap" }}>
              <span
                className="status-badge"
                style={{
                  borderRadius: "50%",
                  width: "1.75rem",
                  height: "1.75rem",
                  justifyContent: "center",
                  padding: 0,
                  backgroundColor: index <= currentStepIndex ? "var(--color-primary)" : "#f0f0f7",
                  color: index <= currentStepIndex ? "#fff" : "var(--color-text-muted)",
                }}
              >
                {index + 1}
              </span>
              {step.label}
            </span>
          ))}
        </div>
      )}

      <section className="section">
        <h2 className="section-title">訂單商品</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>商品</th>
                <th>下單時單價</th>
                <th>數量</th>
                <th>小計</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="group-buy-card-row">
                      <MediaImage
                        src={item.image_url_snapshot}
                        alt={item.product_name_snapshot}
                        style={{ width: "3rem", height: "3rem", objectFit: "cover", borderRadius: "var(--radius)" }}
                      />
                      {item.product_name_snapshot}
                    </div>
                  </td>
                  <td>NT$ {item.unit_price}</td>
                  <td>{item.quantity}</td>
                  <td>NT$ {item.subtotal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ textAlign: "right", fontWeight: 700, marginTop: "0.5rem" }}>
          商品總額：NT$ {order.product_total_amount}
        </p>
      </section>

      <div className="two-col-section">
        <section className="section">
          <h2 className="section-title">開團資訊（下單當時快照）</h2>
          <dl className="detail-list">
            <dt>活動名稱</dt>
            <dd>{order.activity_name}</dd>
            <dt>團主名稱</dt>
            <dd>{order.group_leader_name}</dd>
            <dt>付款方式</dt>
            <dd>
              {PAYMENT_METHOD_LABELS[order.payment_method]}
              {order.payment_method_note ? `（${order.payment_method_note}）` : ""}
            </dd>
            <dt>是否需要二補</dt>
            <dd>{order.requires_second_payment ? "需要" : "不需要"}</dd>
            <dt>是否包含滿贈</dt>
            <dd>{order.includes_full_gift ? "包含" : "不包含"}</dd>
            <dt>主要聯絡方式</dt>
            <dd>
              {CONTACT_PLATFORM_LABELS[order.contact_platform]}：{order.contact_value}
            </dd>
          </dl>
        </section>

        <section className="section">
          <h2 className="section-title">取消申請</h2>
          {order.pending_cancellation_request ? (
            <div className="group-buy-card">
              <StatusBadge domain="application" value={order.pending_cancellation_request.status} />
              <p style={{ marginTop: "0.5rem" }}>已提出取消申請，請耐心等待團主處理。</p>
            </div>
          ) : canCancel ? (
            <Link className="btn btn-primary" to={`/orders/${order.id}/cancel`}>
              申請取消訂單
            </Link>
          ) : (
            <p className="helper-text">目前狀態無法申請取消訂單。</p>
          )}

          {order.cancellation_requests.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <p className="helper-text">歷史取消申請：</p>
              {order.cancellation_requests.map((request) => (
                <div key={request.id} className="group-buy-card">
                  <div className="group-buy-card-row">
                    <StatusBadge domain="application" value={request.status} />
                    <span className="helper-text">{formatDateTime(request.created_at)}</span>
                  </div>
                  {request.reason && <p>原因：{request.reason}</p>}
                  {request.response_note && <p>團主回覆：{request.response_note}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="section">
        <h2 className="section-title">下單時團規（完整內容快照）</h2>
        <div className="rules-text">{order.rules}</div>
      </section>

      <Link to="/orders">← 返回我的訂單</Link>
    </>
  );
}
