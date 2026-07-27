import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  acceptOrder,
  approveCancellationRequest,
  completeOrder,
  getGroupLeaderOrderDetail,
  markOrderPaid,
  markOrderShipped,
  rejectCancellationRequest,
  rejectOrder,
} from "../../api/groupLeaderOrders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";

const TIMELINE_STEPS = [
  { key: "pending_confirmation", label: "待確認" },
  { key: "pending_payment", label: "待付款" },
  { key: "paid", label: "已付款" },
  { key: "shipped", label: "已出貨" },
  { key: "completed", label: "已完成" },
];

const ACTION_LABELS = {
  accept: "接受訂單",
  "mark-paid": "標記已付款",
  "mark-shipped": "標記已出貨",
  complete: "標記已完成",
};

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "取貨付款",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };

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
  const [error, setError] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [cancellationNote, setCancellationNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function load() {
    setError(false);
    setOrder(null);
    getGroupLeaderOrderDetail(orderId, token)
      .then((response) => setOrder(response.data))
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  async function runAction(fn) {
    setBusy(true);
    setFeedback(null);
    try {
      await fn();
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "操作時發生錯誤，請稍後再試。" });
    } finally {
      setBusy(false);
    }
  }

  async function handleReject(event) {
    event.preventDefault();
    if (!rejectReason.trim()) return;
    await runAction(() => rejectOrder(orderId, rejectReason.trim(), token));
    setShowRejectForm(false);
    setRejectReason("");
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!order) {
    return <PageLoader />;
  }

  const isTerminalOther = order.status === "rejected" || order.status === "cancelled";
  const currentStepIndex = TIMELINE_STEPS.findIndex((step) => step.key === order.status);
  const positiveActions = order.available_actions.filter((action) => action !== "reject");
  const canReject = order.available_actions.includes("reject");

  return (
    <>
      <div className="group-buy-card-row">
        <h1>訂單詳情</h1>
        <StatusBadge domain="order" value={order.status} />
      </div>

      {!isTerminalOther && (
        <div className="group-buy-card-row" style={{ flexWrap: "nowrap", overflowX: "auto", margin: "1rem 0" }}>
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

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      <div className="two-col-section">
        <div>
          <dl className="detail-list">
            <dt>訂單編號</dt>
            <dd>{order.order_number}</dd>
            <dt>下單時間</dt>
            <dd>{formatDateTime(order.created_at)}</dd>
            <dt>會員名稱</dt>
            <dd>{order.member_nickname}</dd>
            {order.status === "rejected" && order.rejection_reason && (
              <>
                <dt>拒絕原因</dt>
                <dd>{order.rejection_reason}</dd>
              </>
            )}
          </dl>

          <section className="section">
            <h2 className="section-title">訂購商品</h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>商品</th>
                    <th>單價</th>
                    <th>數量</th>
                    <th>小計</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.product_name_snapshot}</td>
                      <td>NT$ {item.unit_price}</td>
                      <td>{item.quantity}</td>
                      <td>NT$ {item.subtotal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ textAlign: "right", fontWeight: 700 }}>商品總額：NT$ {order.product_total_amount}</p>
          </section>

          <section className="section">
            <h2 className="section-title">開團資訊</h2>
            <dl className="detail-list">
              <dt>活動名稱</dt>
              <dd>{order.activity_name}</dd>
              <dt>付款方式</dt>
              <dd>
                {PAYMENT_METHOD_LABELS[order.payment_method]}
                {order.payment_method_note ? `（${order.payment_method_note}）` : ""}
              </dd>
              <dt>是否需要二補</dt>
              <dd>{order.requires_second_payment ? "需要" : "不需要"}</dd>
              <dt>是否包含滿贈</dt>
              <dd>{order.includes_full_gift ? "包含" : "不包含"}</dd>
              <dt>聯絡方式</dt>
              <dd>
                {CONTACT_PLATFORM_LABELS[order.contact_platform]}：{order.contact_value}
              </dd>
              <dt>團規</dt>
              <dd>
                <div className="rules-text">{order.rules}</div>
              </dd>
            </dl>
          </section>
        </div>

        <div>
          <section className="section">
            <h2 className="section-title">團主操作</h2>
            <div className="group-buy-card">
              {positiveActions.map((action) => (
                <Button
                  key={action}
                  fullWidth
                  loading={busy}
                  style={{ marginBottom: "0.5rem" }}
                  onClick={() =>
                    runAction(() => {
                      if (action === "accept") return acceptOrder(orderId, token);
                      if (action === "mark-paid") return markOrderPaid(orderId, token);
                      if (action === "mark-shipped") return markOrderShipped(orderId, token);
                      if (action === "complete") return completeOrder(orderId, token);
                      return Promise.resolve();
                    })
                  }
                >
                  {ACTION_LABELS[action]}
                </Button>
              ))}

              {canReject && !showRejectForm && (
                <Button variant="danger" fullWidth onClick={() => setShowRejectForm(true)}>
                  拒絕訂單
                </Button>
              )}

              {canReject && showRejectForm && (
                <form onSubmit={handleReject}>
                  <textarea
                    rows={3}
                    maxLength={200}
                    placeholder="請填寫拒絕原因...（必填）"
                    value={rejectReason}
                    onChange={(event) => setRejectReason(event.target.value)}
                    required
                  />
                  <div className="group-buy-card-row" style={{ marginTop: "0.5rem" }}>
                    <Button type="button" variant="secondary" onClick={() => setShowRejectForm(false)}>
                      取消
                    </Button>
                    <Button type="submit" variant="danger" loading={busy}>
                      確認拒絕
                    </Button>
                  </div>
                </form>
              )}

              {positiveActions.length === 0 && !canReject && (
                <p className="helper-text">此訂單目前無可執行的操作。</p>
              )}
            </div>
          </section>

          <section className="section">
            <h2 className="section-title">會員聯絡資訊</h2>
            <dl className="detail-list">
              {order.member_contacts.facebook && (
                <>
                  <dt>Facebook</dt>
                  <dd>{order.member_contacts.facebook}</dd>
                </>
              )}
              {order.member_contacts.discord && (
                <>
                  <dt>Discord</dt>
                  <dd>{order.member_contacts.discord}</dd>
                </>
              )}
              {order.member_contacts.line && (
                <>
                  <dt>LINE</dt>
                  <dd>{order.member_contacts.line}</dd>
                </>
              )}
            </dl>
          </section>

          {order.pending_cancellation_request && (
            <section className="section">
              <h2 className="section-title">取消申請處理</h2>
              <div className="group-buy-card">
                {order.pending_cancellation_request.reason && (
                  <p>會員原因：{order.pending_cancellation_request.reason}</p>
                )}
                <textarea
                  rows={2}
                  placeholder="回覆備註（選填）"
                  value={cancellationNote}
                  onChange={(event) => setCancellationNote(event.target.value)}
                />
                <div className="group-buy-card-row" style={{ marginTop: "0.5rem" }}>
                  <Button
                    variant="danger"
                    loading={busy}
                    onClick={() =>
                      runAction(() =>
                        rejectCancellationRequest(order.pending_cancellation_request.id, cancellationNote, token),
                      )
                    }
                  >
                    拒絕取消
                  </Button>
                  <Button
                    loading={busy}
                    onClick={() =>
                      runAction(() =>
                        approveCancellationRequest(order.pending_cancellation_request.id, cancellationNote, token),
                      )
                    }
                  >
                    核准取消
                  </Button>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>

      <Link to="/group-leader/orders">← 返回訂單管理</Link>
    </>
  );
}
