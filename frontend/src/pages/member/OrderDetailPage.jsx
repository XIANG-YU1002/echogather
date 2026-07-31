import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMyOrderDetail } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ContactValue from "../../components/common/ContactValue.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";
import UnmergeRequestModal from "../../components/common/UnmergeRequestModal.jsx";
import {
  ArrowLeftIcon,
  CalendarIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  InfoIcon,
  LineIcon,
} from "../../components/common/icons.jsx";
import {
  CANCELLABLE_STATUSES,
  STATUS_LABELS,
  TIMELINE_STEPS,
  firstOccurrenceMap,
  formatOrderDateTime as formatDateTime,
} from "../../constants/orderStatus.js";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "取貨付款",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };
const CONTACT_PLATFORM_ICONS = {
  facebook: FacebookIcon,
  discord: DiscordIcon,
  line: LineIcon,
};
const CONTACT_ROWS = [
  { key: "facebook", label: "Facebook", icon: FacebookIcon, field: "member_facebook_contact" },
  { key: "discord", label: "Discord", icon: DiscordIcon, field: "member_discord_contact" },
  { key: "line", label: "LINE", icon: LineIcon, field: "member_line_contact" },
];

/** 回傳距離 deadline 的剩餘描述；已過期回 null。 */
function formatRemaining(isoString) {
  const target = new Date(isoString).getTime();
  if (Number.isNaN(target)) return null;
  const diff = target - Date.now();
  if (diff <= 0) return null;
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  if (days > 0) return `剩餘 ${days} 天 ${hours} 小時`;
  if (hours > 0) return `剩餘 ${hours} 小時 ${minutes} 分`;
  return `剩餘 ${minutes} 分`;
}

export default function OrderDetailPage() {
  const { orderId } = useParams();
  // user 只用來當 Facebook 連結的顯示名稱（訂單快照沒有暱稱欄位）
  const { token, user } = useAuth();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [unmergeOpen, setUnmergeOpen] = useState(false);

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

  async function copyOrderNumber() {
    try {
      await navigator.clipboard.writeText(order.order_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // 瀏覽器不支援或未授權時靜默略過，不影響其他功能
    }
  }

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
  const currentStep = currentStepIndex >= 0 ? TIMELINE_STEPS[currentStepIndex] : null;
  const canCancel =
    CANCELLABLE_STATUSES.includes(order.status) && !order.pending_cancellation_request;
  // 合併而來的訂單才會有拆回的區塊。兩個區塊並存時才加小標題區分——
  // 一般訂單只有一個區塊，卡片標題就足夠，多加小標題反而囉嗦（也才與圖 08 一致）。
  const hasUnmergeSection = Boolean(
    order.can_request_unmerge || order.pending_unmerge_request,
  );
  const remaining = formatRemaining(order.deadline_at);
  const LeaderContactIcon = CONTACT_PLATFORM_ICONS[order.contact_platform];

  // 各狀態第一次發生的時間，供進度條節點顯示
  const firstOccurredAt = firstOccurrenceMap(order.status_history);

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: "我的訂單", to: "/orders" },
          { label: "訂單詳情" },
        ]}
      />

      <div className="od-layout">
        <div>
          {/* 頁首卡：標題 + 訂單編號／建立時間／目前狀態 + 進度條 */}
          <div className="gb-panel">
            <h1 className="od-title">訂單詳情</h1>

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
                <span className="od-meta-value">{formatDateTime(order.created_at)}</span>
              </span>
              <span className="od-meta-item">
                <span className="od-meta-label">目前狀態</span>
                <StatusBadge domain="order" value={order.status} />
              </span>
            </div>

            {isTerminalOther ? (
              <div className="info-note od-terminal">
                <InfoIcon />
                <span>
                  此訂單已{order.status === "rejected" ? "被團主拒絕" : "取消"}，不再繼續進行。
                  {order.status === "rejected" && order.rejection_reason
                    ? `拒絕原因：${order.rejection_reason}`
                    : ""}
                </span>
              </div>
            ) : (
              <>
                <ol className="od-progress">
                  {TIMELINE_STEPS.map((step, index) => (
                    <li
                      key={step.key}
                      className={`od-progress-step${index <= currentStepIndex ? " done" : ""}${
                        index === currentStepIndex ? " current" : ""
                      }`}
                    >
                      <span className="od-progress-dot">{index + 1}</span>
                      <span className="od-progress-label">{step.label}</span>
                      {firstOccurredAt[step.key] && (
                        <span className="od-progress-time">
                          {formatDateTime(firstOccurredAt[step.key])}
                        </span>
                      )}
                    </li>
                  ))}
                </ol>

                {currentStep && (
                  <div className="info-note od-hint">
                    <InfoIcon />
                    <span>{currentStep.hint}</span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* 訂單商品 */}
          <div className="gb-panel">
            <h2 className="section-title plain">訂單商品</h2>
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
                      <span className="od-figure-label">下單時單價</span>
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

          {/* 會員聯絡資料 ＋ 狀態相關訊息 */}
          <div className="two-col-section">
            <div className="gb-panel">
              <h2 className="section-title plain">
                會員聯絡資料
                <span className="od-subtle">（下單當時保存）</span>
              </h2>
              {CONTACT_ROWS.map(({ key, label, icon: Icon, field }) => (
                <div className="oc-contact-row" key={key}>
                  <Icon className="oc-contact-icon" />
                  <span className="oc-contact-name">{label}</span>
                  {order[field] ? (
                    <ContactValue
                      platform={key}
                      value={order[field]}
                      displayName={user?.nickname}
                      className="oc-contact-value"
                    />
                  ) : (
                    <span className="oc-contact-value empty">未填寫</span>
                  )}
                </div>
              ))}
              <p className="oc-contact-hint">
                <InfoIcon />
                此為下單當時的聯絡資料快照，後續修改個人資料不會影響本訂單。
              </p>
            </div>

            <div className="gb-panel">
              <h2 className="section-title plain">狀態相關訊息</h2>
              <p className="od-status-headline">{STATUS_LABELS[order.status]}</p>
              {currentStep && <p className="od-status-hint">{currentStep.hint}</p>}
              {order.status === "rejected" && order.rejection_reason && (
                <p className="od-status-hint">拒絕原因：{order.rejection_reason}</p>
              )}
              <div className="od-status-box">
                <div className="od-status-line">
                  <span className="label">收單期限</span>
                  <span className="value">
                    {formatDateTime(order.deadline_at)}
                    {remaining && <span className="od-remaining">（{remaining}）</span>}
                    {!remaining && <span className="od-remaining">（已截止）</span>}
                  </span>
                </div>
                <div className="od-status-line">
                  <span className="label">付款提醒</span>
                  <span className="value">請完成付款並主動通知團主以利對帳。</span>
                </div>
              </div>
            </div>
          </div>

          {/* 下單時團規 ＋ 取消申請 */}
          <div className="two-col-section">
            <div className="gb-panel">
              <h2 className="section-title plain">
                下單時團規
                <span className="od-subtle">（完整內容快照）</span>
              </h2>
              <div className="oc-rules rules-text">{order.rules}</div>
              <label className="oc-agree od-agree-readonly">
                <input type="checkbox" checked readOnly disabled />
                <span>我已詳閱並同意以上團規內容（下單時已勾選）</span>
              </label>
            </div>

            <div className="gb-panel">
              <h2 className="section-title plain">取消申請</h2>

              {/* 合併而來的訂單多出「拆回原訂單」區塊。與下方的「取消整筆訂單」
                  併在同一張卡片內，兩欄區才不會變成 3 張而空一格（圖 08 是兩欄）。
                  兩者容易混淆，因此文字刻意強調「商品保留，不是取消訂單」。
                  入口除了這裡，通知中心那則「訂單已合併」通知底下也有一個。 */}
              {hasUnmergeSection && (
                <div className="od-cancel-group">
                  <h3 className="od-cancel-subtitle">拆回原本的訂單</h3>

                  {order.pending_unmerge_request ? (
                    <>
                      <p className="od-cancel-state">
                        <InfoIcon />
                        <span>
                          已提出申請，等待團主處理。核准後會拆回合併前的
                          {order.pending_unmerge_request.source_orders.length + 1} 張訂單。
                        </span>
                      </p>
                      {order.pending_unmerge_request.reason && (
                        <p className="od-subtle-block">
                          你填寫的原因：{order.pending_unmerge_request.reason}
                        </p>
                      )}
                    </>
                  ) : (
                    <>
                      <p className="od-subtle-block">
                        這張訂單由多張合併而成。拆回後商品仍保留，
                        <strong>不是取消訂單</strong>；各張會回到合併前的狀態與金額。
                      </p>
                      <Button
                        variant="secondary"
                        fullWidth
                        className="od-cancel-btn"
                        onClick={() => setUnmergeOpen(true)}
                      >
                        申請拆回原訂單
                      </Button>
                      <p className="od-cancel-state">
                        <InfoIcon />
                        <span>已出貨之後就無法再拆。</span>
                      </p>
                    </>
                  )}
                </div>
              )}

              <div className="od-cancel-group">
                {hasUnmergeSection && (
                  <h3 className="od-cancel-subtitle">取消整筆訂單</h3>
                )}
                <p className="od-subtle-block">在以下狀態可申請取消訂單</p>
                <div className="od-cancellable-chips">
                  {CANCELLABLE_STATUSES.map((status) => (
                    <span className="char-tag" key={status}>
                      {STATUS_LABELS[status]}
                    </span>
                  ))}
                </div>

                {canCancel ? (
                  <Link
                    className="btn btn-secondary btn-full od-cancel-btn"
                    to={`/orders/${order.id}/cancel`}
                  >
                    申請取消訂單
                  </Link>
                ) : null}

                <p className="od-cancel-state">
                  <InfoIcon />
                  <span>
                    目前狀態：
                    {order.pending_cancellation_request
                      ? "已提出取消申請，等待團主處理"
                      : canCancel
                        ? "尚未提出取消申請"
                        : "目前狀態無法申請取消訂單"}
                  </span>
                </p>

                <div className="info-note">
                  <InfoIcon />
                  <span>提出申請後，請耐心等待團主處理。若團主拒絕，您可再次提出申請。</span>
                </div>

                {order.cancellation_requests.length > 0 && (
                  <div className="od-cancel-history">
                    <p className="od-subtle-block">歷史取消申請</p>
                    {order.cancellation_requests.map((request) => (
                      <div className="od-cancel-entry" key={request.id}>
                        <div className="od-cancel-entry-head">
                          <StatusBadge domain="application" value={request.status} />
                          <span className="od-subtle">{formatDateTime(request.created_at)}</span>
                        </div>
                        {request.reason && <p>原因：{request.reason}</p>}
                        {request.response_note && <p>團主回覆：{request.response_note}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 底部操作列。參考圖 08 在這裡也畫了一顆「申請取消訂單」，但與
              「取消申請」卡片內那顆完全重複（同一個路由、同樣文字），
              使用者 2026-07-30 裁決移除這一顆——卡片內那顆旁邊才有可取消狀態、
              目前狀態與「被拒絕可再申請」的說明脈絡。 */}
          <div className="od-actions">
            <Link className="btn btn-secondary" to="/orders">
              <ArrowLeftIcon />
              返回我的訂單
            </Link>
            <div className="od-actions-right">
              <Link className="btn btn-secondary" to={`/group-leaders/${order.group_leader_id}`}>
                查看團主公開頁
              </Link>
            </div>
          </div>
        </div>

        {/* 右側三張卡 */}
        <aside className="od-side">
          {!isTerminalOther && (
            <div className="gb-panel">
              <h2 className="fl-sum-title">狀態時間軸</h2>
              <ol className="od-timeline">
                {TIMELINE_STEPS.map((step, index) => (
                  <li
                    key={step.key}
                    className={`od-timeline-item${index <= currentStepIndex ? " done" : ""}${
                      index === currentStepIndex ? " current" : ""
                    }`}
                  >
                    <span className="od-timeline-dot" aria-hidden="true" />
                    {firstOccurredAt[step.key] && (
                      <span className="od-timeline-time">
                        {formatDateTime(firstOccurredAt[step.key])}
                      </span>
                    )}
                    <span className="od-timeline-label">{step.label}</span>
                    <span className="od-timeline-desc">{step.description}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="gb-panel">
            <h2 className="fl-sum-title">
              開團資料
              <span className="od-subtle">（下單當時快照）</span>
            </h2>
            <div className="oc-row">
              <span className="label">活動名稱</span>
              <span className="value">{order.activity_name}</span>
            </div>
            <div className="oc-row">
              <span className="label">團主名稱</span>
              <span className="value">
                <Link to={`/group-leaders/${order.group_leader_id}`}>{order.group_leader_name}</Link>
              </span>
            </div>
            <div className="oc-row">
              <span className="label">付款方式</span>
              <span className="value">{PAYMENT_METHOD_LABELS[order.payment_method]}</span>
            </div>
            <div className="oc-row">
              <span className="label">付款方式備註</span>
              <span className="value">{order.payment_method_note || "無"}</span>
            </div>
            <div className="oc-row">
              <span className="label">是否需要二補</span>
              <span className="value">{order.requires_second_payment ? "是" : "否"}</span>
            </div>
            <div className="oc-row">
              <span className="label">是否包含滿贈</span>
              <span className="value">{order.includes_full_gift ? "是" : "否"}</span>
            </div>
            <div className="oc-row">
              <span className="label">收單期限</span>
              <span className="value">{formatDateTime(order.deadline_at)}</span>
            </div>
            <div className="oc-row">
              <span className="label">主要聯絡方式</span>
              <span className="value contact-inline">
                {LeaderContactIcon && <LeaderContactIcon className="oc-contact-icon" />}
                <span className="oc-contact-platform">
                  {CONTACT_PLATFORM_LABELS[order.contact_platform]}：
                </span>
                <ContactValue
                  platform={order.contact_platform}
                  value={order.contact_value}
                  displayName={order.group_leader_name}
                  className="oc-contact-link"
                />
              </span>
            </div>
            <Link
              className="btn btn-secondary btn-full oc-leader-btn"
              to={`/group-leaders/${order.group_leader_id}`}
            >
              查看團主公開頁
            </Link>
          </div>

          <div className="gb-panel">
            <h2 className="fl-sum-title">狀態紀錄</h2>
            {(order.status_history ?? []).length === 0 ? (
              <p className="od-subtle-block">尚無狀態紀錄。</p>
            ) : (
              <ol className="od-history">
                {order.status_history.map((entry, index) => (
                  <li className="od-history-item" key={`${entry.status}-${index}`}>
                    <span className="od-history-dot" aria-hidden="true" />
                    <span className="od-history-time">{formatDateTime(entry.created_at)}</span>
                    <span className="od-history-label">{STATUS_LABELS[entry.status]}</span>
                    {entry.note && <span className="od-history-note">{entry.note}</span>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </aside>
      </div>

      {unmergeOpen && (
        <UnmergeRequestModal
          orderId={order.id}
          onClose={() => setUnmergeOpen(false)}
          onSubmitted={load}
        />
      )}
    </>
  );
}
