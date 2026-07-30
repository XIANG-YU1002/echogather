import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createCancellationRequest, getMyOrderDetail } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import MediaImage from "../../components/common/MediaImage.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import {
  ArrowLeftIcon,
  CalendarIcon,
  ClipboardIcon,
  InfoIcon,
} from "../../components/common/icons.jsx";
import {
  CANCELLABLE_STATUSES,
  STATUS_LABELS,
  TIMELINE_STEPS,
  firstOccurrenceMap,
  formatOrderDateTime,
} from "../../constants/orderStatus.js";

const REASON_MAX = 300;

export default function CancellationRequestPage() {
  const { orderId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [error, setError] = useState(false);
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [copied, setCopied] = useState(false);

  function load() {
    setError(false);
    setOrder(null);
    getMyOrderDetail(orderId, token)
      .then((response) => setOrder(response.data))
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  async function copyOrderNumber() {
    try {
      await navigator.clipboard.writeText(order.order_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // 瀏覽器不支援或未授權時靜默略過
    }
  }

  async function handleConfirmedSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await createCancellationRequest(orderId, reason.trim(), token);
      navigate(`/orders/${orderId}`, { replace: true });
    } catch (err) {
      setSubmitError(
        err instanceof ApiError ? err.message : "送出取消申請時發生錯誤，請稍後再試。",
      );
      setConfirming(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!order) {
    return <PageLoader />;
  }

  const occurredAt = firstOccurrenceMap(order.status_history);
  const currentStepIndex = TIMELINE_STEPS.findIndex((step) => step.key === order.status);

  // 依 Business Rules §22.1／§22.4 在進頁時就判斷資格，
  // 不符時不顯示註定失敗的表單，直接說明原因。
  const statusNotAllowed = !CANCELLABLE_STATUSES.includes(order.status);
  const hasPendingRequest = Boolean(order.pending_cancellation_request);
  const ineligibleReason = statusNotAllowed
    ? `此訂單目前的狀態為「${STATUS_LABELS[order.status]}」，依規則僅在${CANCELLABLE_STATUSES.map(
        (status) => STATUS_LABELS[status],
      ).join("、")}時可申請取消。`
    : hasPendingRequest
      ? "此訂單已有一筆待團主處理的取消申請，同一時間只能有一筆。請等待團主處理結果。"
      : null;

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: "我的訂單", to: "/orders" },
          { label: "訂單詳情", to: `/orders/${orderId}` },
          { label: "申請取消訂單" },
        ]}
      />

      <div className="page-head">
        <span className="page-head-badge cr-badge">✕</span>
        <div>
          <h1>申請取消訂單</h1>
          <p>取消申請送出後，訂單狀態不會立即變更，需等待團主處理。</p>
        </div>
      </div>

      <div className="od-layout">
        <div>
          {/* 訂單資訊 */}
          <div className="gb-panel">
            <h2 className="section-title plain">訂單資訊</h2>

            <div className="od-meta">
              <span className="od-meta-item">
                <ClipboardIcon />
                <span className="od-meta-label">訂單編號</span>
                <span className="od-meta-value">{order.order_number}</span>
                <button
                  type="button"
                  className="od-copy"
                  onClick={copyOrderNumber}
                  aria-label="複製訂單編號"
                >
                  {copied ? "已複製" : "複製"}
                </button>
              </span>
              <span className="od-meta-item">
                <CalendarIcon />
                <span className="od-meta-label">建立時間</span>
                <span className="od-meta-value">{formatOrderDateTime(order.created_at)}</span>
              </span>
              <span className="od-meta-item">
                <span className="od-meta-label">目前狀態</span>
                <StatusBadge domain="order" value={order.status} />
              </span>
            </div>

            <hr className="fl-divider" />

            {order.items.map((item) => (
              <div className="od-item" key={item.id}>
                <MediaImage
                  className="od-item-thumb"
                  src={item.image_url_snapshot}
                  alt={item.product_name_snapshot}
                />
                <div className="od-item-body">
                  <div className="od-item-head">
                    <span className="od-item-name">{item.product_name_snapshot}</span>
                    <span className="gb-badge">{order.activity_name}</span>
                    {item.chosen_character_name && (
                      <span className="char-tag">{item.chosen_character_name}</span>
                    )}
                  </div>
                  <div className="od-item-figures">
                    <span>
                      <span className="od-figure-label">單價</span>
                      <span className="od-figure-value">NT$ {item.unit_price}</span>
                    </span>
                    <span>
                      <span className="od-figure-label">數量</span>
                      <span className="od-figure-value">{item.quantity}</span>
                    </span>
                    <span>
                      <span className="od-figure-label">小計</span>
                      <span className="od-figure-value">NT$ {item.subtotal}</span>
                    </span>
                  </div>
                </div>
              </div>
            ))}

            <div className="od-total-row">
              <span>商品總額</span>
              <span className="fl-total-value">NT$ {order.product_total_amount}</span>
            </div>
          </div>

          {/* 不符申請資格：不顯示表單，直接說明原因 */}
          {ineligibleReason ? (
            <div className="gb-panel">
              <h2 className="section-title plain">無法申請取消</h2>
              <div className="info-note cr-ineligible">
                <InfoIcon />
                <span>{ineligibleReason}</span>
              </div>
              {hasPendingRequest && !statusNotAllowed && (
                <div className="cr-pending-box">
                  <div className="od-cancel-entry-head">
                    <StatusBadge
                      domain="application"
                      value={order.pending_cancellation_request.status}
                    />
                    <span className="od-subtle">
                      {formatOrderDateTime(order.pending_cancellation_request.created_at)}
                    </span>
                  </div>
                  {order.pending_cancellation_request.reason && (
                    <p>你填寫的原因：{order.pending_cancellation_request.reason}</p>
                  )}
                </div>
              )}
            </div>
          ) : (
          <div className="gb-panel">
            <h2 className="section-title plain">
              取消原因
              <span className="od-subtle">（選填）</span>
            </h2>
            <p className="od-subtle-block">請簡單說明您申請取消的原因，我們將提供給團主參考。</p>

            <div className="cr-textarea-wrap">
              <textarea
                id="cancel-reason"
                rows={5}
                maxLength={REASON_MAX}
                placeholder={`請輸入取消原因（選填，最多 ${REASON_MAX} 字）`}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <span className="cr-counter">
                {reason.length} / {REASON_MAX}
              </span>
            </div>

            <div className="info-note purple cr-notice">
              <InfoIcon />
              <div>
                <p className="cr-notice-title">注意事項</p>
                <ul>
                  <li>取消申請送出後，訂單狀態不會立即變更，需等待團主處理。</li>
                  <li>若團主拒絕您的申請，且訂單仍符合申請條件，您可以再次提出申請。</li>
                  <li>同一時間只能有一筆待處理的取消申請。</li>
                </ul>
              </div>
            </div>

            {submitError && <Alert type="error">{submitError}</Alert>}
          </div>
          )}

          {/* 底部操作列 */}
          <div className="od-actions">
            <Link className="btn btn-secondary" to={`/orders/${orderId}`}>
              <ArrowLeftIcon />
              返回訂單詳情
            </Link>
            {!ineligibleReason && (
              <div className="od-actions-right">
                <Button onClick={() => setConfirming(true)}>送出取消申請</Button>
              </div>
            )}
          </div>
        </div>

        {/* 右側：訂單狀態流程 ＋ 取消規則提醒 */}
        <aside className="od-side">
          <div className="gb-panel">
            <h2 className="fl-sum-title">訂單狀態流程</h2>
            <ol className="od-timeline">
              {TIMELINE_STEPS.map((step, index) => (
                <li
                  key={step.key}
                  className={`od-timeline-item${index <= currentStepIndex ? " done" : ""}${
                    index === currentStepIndex ? " current" : ""
                  }`}
                >
                  <span className="od-timeline-dot" aria-hidden="true" />
                  <span className="od-timeline-label">{step.label}</span>
                  {occurredAt[step.key] && (
                    <span className="od-timeline-time">
                      {formatOrderDateTime(occurredAt[step.key])}
                    </span>
                  )}
                  {index === currentStepIndex && (
                    <span className="cr-step-hint">{step.hint}</span>
                  )}
                </li>
              ))}
            </ol>
          </div>

          <div className="gb-panel">
            <h2 className="fl-sum-title cr-rule-title">
              <span aria-hidden="true">⚠</span>
              取消規則提醒
            </h2>
            <ul className="cr-rules">
              <li>
                僅在以下狀態可申請取消：
                <br />
                <span className="cr-rule-statuses">
                  {CANCELLABLE_STATUSES.map((status) => STATUS_LABELS[status]).join("、")}
                </span>
              </li>
              <li>申請取消不代表一定會成功，需由團主決定。</li>
              <li>若團主已出貨或交易已完成，將無法申請取消。</li>
            </ul>
          </div>
        </aside>
      </div>

      {confirming && (
        <ConfirmModal
          title="確定要申請取消這筆訂單嗎？"
          message={
            `訂單 ${order.order_number} 將送出取消申請給團主。` +
            "送出後訂單狀態不會立即變更，需等待團主處理；在團主處理前無法再提出第二筆申請。"
          }
          confirmLabel="確定送出"
          loading={submitting}
          onCancel={() => setConfirming(false)}
          onConfirm={handleConfirmedSubmit}
        />
      )}
    </>
  );
}
