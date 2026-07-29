import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  acceptOrder,
  approveCancellationRequest,
  completeOrder,
  getGroupLeaderOrderDetail,
  getMergeableOrders,
  markOrderPaid,
  markOrderShipped,
  mergeOrders,
  rejectCancellationRequest,
  rejectOrder,
} from "../../api/groupLeaderOrders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import {
  CalendarIcon,
  CheckCircleIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  InfoIcon,
  LineIcon,
  UserIcon,
  XCircleIcon,
} from "../../components/common/icons.jsx";

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
const REJECT_REASON_MAX = 200;

function formatDateTime(isoString) {
  // 欄位缺值時不要算出 NaN/NaN/NaN
  if (!isoString) {
    return "—";
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`;
}

/** 會員聯絡方式小卡。Facebook 已強制為連結，可直接開啟；其餘提供複製。 */
function ContactCard({ platform, value }) {
  const [copied, setCopied] = useState(false);
  const Icon = { facebook: FacebookIcon, discord: DiscordIcon, line: LineIcon }[platform];

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 瀏覽器不允許剪貼簿時就不提示，團主仍可手動選取
    }
  }

  const href = value.startsWith("http") ? value : `https://${value}`;

  return (
    <div className="od-contact">
      <Icon className="od-contact-icon" />
      <span className="od-contact-text">
        <span className="od-contact-platform">{CONTACT_PLATFORM_LABELS[platform]}</span>
        <span className="od-contact-value">{value}</span>
      </span>
      {platform === "facebook" ? (
        <a className="od-contact-action" href={href} target="_blank" rel="noreferrer noopener">
          查看個人檔案 ↗
        </a>
      ) : (
        <button type="button" className="od-contact-action" onClick={handleCopy}>
          {copied ? "已複製" : "複製 ID"}
        </button>
      )}
    </div>
  );
}

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [cancellationNote, setCancellationNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // 可合併的其他訂單（同會員同開團）
  const [mergeable, setMergeable] = useState([]);
  const [selectedMergeIds, setSelectedMergeIds] = useState([]);
  const [mergeKeep, setMergeKeep] = useState("oldest");
  const [confirmMerge, setConfirmMerge] = useState(false);
  const [mergeError, setMergeError] = useState(null);

  function load() {
    setError(false);
    setOrder(null);
    getGroupLeaderOrderDetail(orderId, token)
      .then((response) => setOrder(response.data))
      .catch(() => setError(true));
    // 合併候選清單失敗不影響整頁
    getMergeableOrders(orderId, token)
      .then((response) => setMergeable(response.data))
      .catch(() => setMergeable([]));
    setSelectedMergeIds([]);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  function toggleMergeId(id) {
    setSelectedMergeIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  async function handleMerge() {
    setBusy(true);
    setFeedback(null);
    try {
      const response = await mergeOrders(
        orderId,
        { mergeWithOrderIds: selectedMergeIds, keep: mergeKeep },
        token,
      );
      setConfirmMerge(false);
      setMergeError(null);
      // 保留的可能是別張訂單，導向合併後的那一張
      if (response.data.id !== orderId) {
        navigate(`/group-leader/orders/${response.data.id}`, { replace: true });
      } else {
        load();
        setFeedback({ type: "success", message: "訂單已合併。" });
      }
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "合併訂單時發生錯誤，請稍後再試。";
      // 頁面較長，錯誤同時顯示在合併卡片內，避免只出現在頁首而被忽略
      setMergeError(message);
      setFeedback({ type: "error", message });
      setConfirmMerge(false);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(fn) {
    setBusy(true);
    setFeedback(null);
    try {
      await fn();
      load();
    } catch (err) {
      setFeedback({
        type: "error",
        message: err instanceof ApiError ? err.message : "操作時發生錯誤，請稍後再試。",
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) {
      setFeedback({ type: "error", message: "拒絕訂單前請先填寫拒絕原因。" });
      return;
    }
    await runAction(() => rejectOrder(orderId, rejectReason.trim(), token));
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
  const contacts = [
    ["facebook", order.member_contacts.facebook],
    ["discord", order.member_contacts.discord],
    ["line", order.member_contacts.line],
  ].filter(([, value]) => value);
  // 已出貨／已完成／已取消／已拒絕的訂單不能合併，連區塊都不顯示
  const canMerge = ["pending_confirmation", "pending_payment", "paid"].includes(order.status);

  return (
    <>
      <Breadcrumb
        items={[
          { label: "團主後台", to: "/group-leader" },
          { label: "訂單管理", to: "/group-leader/orders" },
          { label: "訂單詳情" },
        ]}
      />

      <div className="page-header od-header">
        <h1>訂單詳情</h1>
        <StatusBadge domain="order" value={order.status} />
      </div>

      {!isTerminalOther && (
        <section className="od-timeline-wrap">
          <span className="od-timeline-title">訂單狀態</span>
          {/* 沿用圖 17／18 已驗收的步驟指示器結構（.gla-*），只把圓點內容換成數字 */}
          <ol className="gla-steps od-timeline">
            {TIMELINE_STEPS.map((step, index) => (
              <li
                key={step.key}
                className={`gla-step${index < currentStepIndex ? " gla-step-done" : ""}${
                  index === currentStepIndex ? " gla-step-current" : ""
                }`}
              >
                <span className="gla-step-line gla-step-line-before" />
                <span className="gla-step-line gla-step-line-after" />
                <span className="gla-step-dot">{index + 1}</span>
                <span className="gla-step-label">{step.label}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      <div className="od-layout">
        <div className="od-main">
          <section className="gbe-card">
            <h2 className="gbe-card-title">基本資訊</h2>
            <dl className="od-info">
              <div>
                <dt>
                  <ClipboardIcon />
                  訂單編號
                </dt>
                <dd>{order.order_number}</dd>
              </div>
              <div>
                <dt>
                  <CalendarIcon />
                  下單時間
                </dt>
                <dd>{formatDateTime(order.created_at)}</dd>
              </div>
              <div>
                <dt>
                  <UserIcon />
                  會員名稱
                </dt>
                <dd>
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
                </dd>
              </div>
              {order.status === "rejected" && order.rejection_reason && (
                <div>
                  <dt>
                    <XCircleIcon />
                    拒絕原因
                  </dt>
                  <dd>{order.rejection_reason}</dd>
                </div>
              )}
            </dl>
          </section>

          <section className="gbe-card">
            <h2 className="gbe-card-title">訂購商品</h2>
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
                      <td>
                        <span className="gbe-product">
                          <img
                            className="gbe-product-image"
                            src={resolveMediaUrl(item.image_url_snapshot)}
                            alt=""
                          />
                          <span>
                            {item.product_name_snapshot}
                            {item.chosen_character_name && (
                              <span className="od-item-character">
                                {item.chosen_character_name}
                              </span>
                            )}
                            <span className="od-item-activity">{order.activity_name}</span>
                          </span>
                        </span>
                      </td>
                      <td>NT$ {item.unit_price}</td>
                      <td>{item.quantity}</td>
                      <td>NT$ {item.subtotal}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3} className="od-total-label">
                      商品總額
                    </td>
                    <td className="od-total-value">NT$ {order.product_total_amount}</td>
                  </tr>
                  {/* 合併過的訂單才會有已收金額，此時把已收與待收分開顯示 */}
                  {Number(order.paid_amount) > 0 && (
                    <>
                      <tr>
                        <td colSpan={3} className="od-total-label">
                          其中已收款
                        </td>
                        <td className="od-paid-value">NT$ {order.paid_amount}</td>
                      </tr>
                      <tr>
                        <td colSpan={3} className="od-total-label">
                          待收款
                        </td>
                        <td className="od-total-value">
                          NT$ {Number(order.product_total_amount) - Number(order.paid_amount)}
                        </td>
                      </tr>
                    </>
                  )}
                </tfoot>
              </table>
            </div>
          </section>

          <section className="gbe-card">
            <h2 className="gbe-card-title">開團資訊</h2>
            <div className="od-group-buy">
              <dl className="od-info">
                <div>
                  <dt>活動名稱</dt>
                  <dd>{order.activity_name}</dd>
                </div>
                <div>
                  <dt>團主名稱</dt>
                  <dd>{order.group_leader_name}</dd>
                </div>
                <div>
                  <dt>付款方式</dt>
                  <dd>
                    {PAYMENT_METHOD_LABELS[order.payment_method]}
                    {order.payment_method_note ? `（${order.payment_method_note}）` : ""}
                  </dd>
                </div>
                <div>
                  <dt>是否二補</dt>
                  <dd>{order.requires_second_payment ? "是" : "否"}</dd>
                </div>
                <div>
                  <dt>是否含滿贈</dt>
                  <dd>{order.includes_full_gift ? "是" : "否"}</dd>
                </div>
                <div>
                  <dt>主要聯絡方式</dt>
                  <dd>
                    {CONTACT_PLATFORM_LABELS[order.contact_platform]}：{order.contact_value}
                  </dd>
                </div>
              </dl>
              <div className="od-rules">
                <dl className="od-info">
                  <div>
                    <dt>收單期限</dt>
                    <dd>{formatDateTime(order.deadline_at)}</dd>
                  </div>
                </dl>
                <span className="gbe-label">團規</span>
                {/* 直接保留團主寫的原文與換行：團主通常自己就編了號，
                    再套 <ol>／<ul> 會變成「1. 1. …」重複標號 */}
                <div className="rules-text od-rules-text">{order.rules}</div>
              </div>
            </div>
          </section>
        </div>

        <div className="od-side">
          <section className="gbe-card">
            <h2 className="gbe-card-title">團主操作</h2>
            {positiveActions.map((action) => (
              <Button
                key={action}
                fullWidth
                loading={busy}
                className="od-action-btn"
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
                <CheckCircleIcon />
                {ACTION_LABELS[action]}
              </Button>
            ))}

            {canReject && (
              <>
                <button
                  type="button"
                  className="od-reject-btn"
                  disabled={busy}
                  onClick={handleReject}
                >
                  <XCircleIcon />
                  拒絕訂單
                </button>

                {/* 依圖 26：拒絕原因輸入框常駐顯示，不必先按一次按鈕才出現 */}
                <div className="od-reject-reason">
                  <span className="gbe-label">拒絕原因（拒絕訂單時必填）</span>
                  <textarea
                    rows={4}
                    maxLength={REJECT_REASON_MAX}
                    placeholder="請填寫拒絕原因..."
                    value={rejectReason}
                    onChange={(event) => setRejectReason(event.target.value)}
                  />
                  <p className="gbc-counter">
                    {rejectReason.length} / {REJECT_REASON_MAX}
                  </p>
                  <p className="gbe-hint">填寫拒絕原因後，系統將通知會員。</p>
                </div>
              </>
            )}

            {positiveActions.length === 0 && !canReject && (
              <p className="helper-text">此訂單目前無可執行的操作。</p>
            )}
          </section>

          <section className="gbe-card">
            <h2 className="gbe-card-title">會員聯絡資訊</h2>
            {contacts.length === 0 ? (
              <p className="helper-text">此訂單沒有聯絡方式快照。</p>
            ) : (
              <div className="od-contacts">
                {contacts.map(([platform, value]) => (
                  <ContactCard key={platform} platform={platform} value={value} />
                ))}
              </div>
            )}
          </section>

          {order.pending_cancellation_request && (
            <section className="gbe-card">
              <h2 className="gbe-card-title">取消申請處理</h2>
              {order.pending_cancellation_request.reason && (
                <p className="od-cancel-reason">
                  會員原因：{order.pending_cancellation_request.reason}
                </p>
              )}
              <span className="gbe-label">回覆備註（選填）</span>
              <textarea
                rows={3}
                value={cancellationNote}
                onChange={(event) => setCancellationNote(event.target.value)}
              />
              <div className="od-cancel-actions">
                <Button
                  variant="secondary"
                  loading={busy}
                  onClick={() =>
                    runAction(() =>
                      rejectCancellationRequest(
                        order.pending_cancellation_request.id,
                        cancellationNote,
                        token,
                      ),
                    )
                  }
                >
                  拒絕取消
                </Button>
                <Button
                  variant="danger"
                  loading={busy}
                  onClick={() =>
                    runAction(() =>
                      approveCancellationRequest(
                        order.pending_cancellation_request.id,
                        cancellationNote,
                        token,
                      ),
                    )
                  }
                >
                  核准取消
                </Button>
              </div>
            </section>
          )}

          {/* 訂單合併：同會員同開團的多筆訂單可併成一筆（使用者 2026-07-29 需求）。
              參考圖原文寫「請勿與其他訂單合併」，已隨此功能改寫。 */}
          {canMerge && mergeable.length > 0 && (
            <section className="gbe-card">
              <h2 className="gbe-card-title">合併訂單</h2>
              <p className="gbe-hint" style={{ marginTop: 0 }}>
                這位會員在本團還有下列訂單，可合併成一筆處理。
              </p>

              <div className="od-merge-list">
                {mergeable.map((candidate) => (
                  <label key={candidate.id} className="od-merge-item">
                    <input
                      type="checkbox"
                      checked={selectedMergeIds.includes(candidate.id)}
                      onChange={() => toggleMergeId(candidate.id)}
                    />
                    <span className="od-merge-text">
                      <span className="od-merge-number">{candidate.order_number}</span>
                      <span className="od-merge-meta">
                        <StatusBadge domain="order" value={candidate.status} />
                        NT$ {candidate.product_total_amount}／共 {candidate.total_quantity} 件
                      </span>
                      <span className="od-merge-time">
                        {formatDateTime(candidate.created_at)}
                      </span>
                    </span>
                  </label>
                ))}
              </div>

              <span className="gbe-label od-merge-keep-label">保留哪一張訂單的編號與時間</span>
              <div className="gbc-radio-row">
                <label className="gbc-radio">
                  <input
                    type="radio"
                    name="merge-keep"
                    checked={mergeKeep === "oldest"}
                    onChange={() => setMergeKeep("oldest")}
                  />
                  最舊的
                </label>
                <label className="gbc-radio">
                  <input
                    type="radio"
                    name="merge-keep"
                    checked={mergeKeep === "newest"}
                    onChange={() => setMergeKeep("newest")}
                  />
                  最新的
                </label>
              </div>
              <p className="gbe-hint">
                建立時間會影響順位，保留最舊的可維持原本順位。
              </p>

              {mergeError && <Alert type="error">{mergeError}</Alert>}

              <Button
                fullWidth
                variant="secondary"
                className="od-merge-btn"
                loading={busy}
                disabled={selectedMergeIds.length === 0}
                onClick={() => {
                  setMergeError(null);
                  setConfirmMerge(true);
                }}
              >
                合併選取的 {selectedMergeIds.length} 筆訂單
              </Button>
            </section>
          )}

          <section className="od-notice">
            <InfoIcon className="od-notice-icon" />
            <div>
              <p className="od-notice-title">訂單提醒</p>
              <p className="od-notice-text">
                每張訂單各自獨立計算金額與數量。同一會員在同一開團若有多筆訂單，可用上方的
                合併功能併成一筆；未特別合併時就維持原樣，請留意避免重複出貨。
              </p>
            </div>
          </section>
        </div>
      </div>

      <div className="od-back">
        <Link className="btn btn-secondary" to="/group-leader/orders">
          ← 返回訂單管理
        </Link>
      </div>

      {confirmMerge && (
        <ConfirmModal
          title="合併訂單"
          message={
            `將把選取的 ${selectedMergeIds.length} 筆訂單併入保留的訂單（` +
            `${mergeKeep === "oldest" ? "最舊" : "最新"}的那一張）。` +
            "合併等於確認這些訂單，合併後狀態會變成「待付款」（若全部都已付款則維持已付款）；" +
            "已收到的金額會保留並與待收金額分開顯示。" +
            "被併入的訂單會標記為已取消並通知會員。此操作無法復原，確定要繼續嗎？"
          }
          confirmLabel="確定合併"
          loading={busy}
          onCancel={() => setConfirmMerge(false)}
          onConfirm={handleMerge}
        />
      )}
    </>
  );
}
