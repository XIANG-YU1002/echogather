import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  clearFollowList,
  getFollowList,
  removeFollowListItem,
  updateFollowListItemQuantity,
} from "../../api/followList.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useCart } from "../../context/CartContext.jsx";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  BagIcon,
  BellIcon,
  CalendarIcon,
  ChatIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClipboardIcon,
  CreditCardIcon,
  CartIcon,
  GiftIcon,
  RefreshIcon,
  TrashIcon,
  UsersIcon,
} from "../../components/common/icons.jsx";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "可取付",
  other: "其他",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };

function formatDeadline(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function PageHead() {
  return (
    <>
      <nav className="breadcrumb" aria-label="breadcrumb">
        <Link to="/">首頁</Link>
        <span> / </span>
        <span className="breadcrumb-current">購物車</span>
      </nav>
      <div className="page-head">
        <span className="page-head-badge">
          <CartIcon />
        </span>
        <div>
          <h1>購物車</h1>
          <p>確認你想跟團的商品與數量，送出後才會正式建立訂單。</p>
        </div>
      </div>
    </>
  );
}

export default function FollowListPage() {
  const { token } = useAuth();
  const { refresh: refreshCart } = useCart();
  const navigate = useNavigate();
  const [followList, setFollowList] = useState(undefined);
  const [error, setError] = useState(false);
  const [busyItemId, setBusyItemId] = useState(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(true);

  function load(silent = false) {
    setError(false);
    if (!silent) {
      setFollowList(undefined);
    }
    return getFollowList(token)
      .then((response) => setFollowList(response.data))
      .catch(() => {
        if (!silent) setError(true);
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleQuantityChange(item, quantity) {
    if (quantity < 1) return;
    setBusyItemId(item.id);
    try {
      await updateFollowListItemQuantity(item.id, quantity, token);
      await load(true);
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleRemove(item) {
    setBusyItemId(item.id);
    try {
      await removeFollowListItem(item.id, token);
      await load(true);
      refreshCart();
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleClear() {
    setClearing(true);
    try {
      await clearFollowList(token);
      setConfirmClear(false);
      await load(true);
      refreshCart();
    } finally {
      setClearing(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (followList === undefined) {
    return <PageLoader />;
  }

  if (followList === null || followList.items.length === 0) {
    return (
      <>
        <PageHead />
        <EmptyState
          title="您的購物車目前是空的。"
          description="瀏覽商品並加入購物車後，即可在此送出訂單。"
          action={
            <Link className="btn btn-primary" to="/">
              繼續挑選商品
            </Link>
          }
        />
      </>
    );
  }

  const { group_buy: groupBuy } = followList;
  const showFullGift = groupBuy.activity.has_full_gift;
  const firstImage = followList.items[0]?.product.primary_image_url;

  const chips = [
    { icon: <CreditCardIcon />, label: "付款方式", value: PAYMENT_METHOD_LABELS[groupBuy.payment_method] },
    { icon: <RefreshIcon />, label: "是否二補", value: groupBuy.requires_second_payment ? "需二補" : "免二補" },
    ...(showFullGift
      ? [{ icon: <GiftIcon />, label: "是否含滿贈", value: groupBuy.includes_full_gift ? "含滿贈" : "不含滿贈" }]
      : []),
    { icon: <CalendarIcon />, label: "收單期限", value: formatDeadline(groupBuy.deadline_at) },
    { icon: <ChatIcon />, label: "聯絡方式", value: CONTACT_PLATFORM_LABELS[groupBuy.contact_platform] },
  ];

  const summaryRows = [
    { icon: <UsersIcon />, label: "團主", value: groupBuy.group_leader.display_name },
    { icon: <BagIcon />, label: "活動", value: groupBuy.activity.name },
    { icon: <CreditCardIcon />, label: "付款方式", value: PAYMENT_METHOD_LABELS[groupBuy.payment_method] },
    { icon: <RefreshIcon />, label: "是否二補", value: groupBuy.requires_second_payment ? "是" : "否" },
    ...(showFullGift
      ? [{ icon: <GiftIcon />, label: "是否含滿贈", value: groupBuy.includes_full_gift ? "含滿贈" : "不含滿贈" }]
      : []),
    { icon: <CalendarIcon />, label: "收單期限", value: formatDeadline(groupBuy.deadline_at) },
    { icon: <ChatIcon />, label: "聯絡方式", value: CONTACT_PLATFORM_LABELS[groupBuy.contact_platform] },
  ];

  return (
    <>
      <PageHead />

      {!followList.is_submittable && followList.invalid_reasons.length > 0 && (
        <Alert type="error">此清單目前無法送出，請調整後再試。</Alert>
      )}

      <div className="fl-layout">
        <div>
          <div className="gb-panel">
            <h2 className="section-title" style={{ marginBottom: 0 }}>
              購物車內容
            </h2>

            <div className="fl-gb-head">
              {firstImage && <MediaImage className="fl-gb-thumb" src={firstImage} alt="" />}
              <div className="fl-gb-head-text">
                <span className="gb-badge">{groupBuy.activity.name}</span>
                <p className="fl-gb-leader">團主：{groupBuy.group_leader.display_name}</p>
              </div>
              <div className="fl-gb-chips">
                {chips.map((chip) => (
                  <div className="meta-chip" key={chip.label}>
                    <span className="meta-chip-icon">{chip.icon}</span>
                    <span className="meta-chip-text">
                      <span className="meta-chip-label">{chip.label}</span>
                      <span className="meta-chip-value">{chip.value}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <hr className="fl-divider" />

            <div className="table-wrap" style={{ border: "none" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>商品</th>
                    <th>款式 / 角色</th>
                    <th>單價 (TWD)</th>
                    <th>數量</th>
                    <th>小計</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {followList.items.map((item) => {
                    const badges = item.chosen_character
                      ? [item.chosen_character]
                      : item.product.characters ?? [];
                    return (
                      <tr key={item.id}>
                        <td>
                          <div className="compare-leader" style={{ color: "var(--color-text)" }}>
                            <MediaImage
                              src={item.product.primary_image_url}
                              alt={item.product.name}
                              style={{
                                width: "3rem",
                                height: "3rem",
                                objectFit: "cover",
                                borderRadius: "8px",
                              }}
                            />
                            <Link to={`/products/${item.product.id}`}>{item.product.name}</Link>
                          </div>
                        </td>
                        <td>
                          {badges.length > 0 ? (
                            <span className="char-tags">
                              {badges.map((c) => (
                                <span className="char-tag" key={c.id}>
                                  {c.name}
                                </span>
                              ))}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>NT$ {item.unit_price}</td>
                        <td>
                          <div className="qty-box">
                            <button
                              type="button"
                              disabled={busyItemId === item.id || item.quantity <= 1}
                              onClick={() => handleQuantityChange(item, item.quantity - 1)}
                              aria-label="減少數量"
                            >
                              −
                            </button>
                            <span className="qty-n">{item.quantity}</span>
                            <button
                              type="button"
                              disabled={busyItemId === item.id}
                              onClick={() => handleQuantityChange(item, item.quantity + 1)}
                              aria-label="增加數量"
                            >
                              +
                            </button>
                          </div>
                        </td>
                        <td>
                          <span className="fl-subtotal">NT$ {item.estimated_subtotal}</span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="icon-btn"
                            disabled={busyItemId === item.id}
                            onClick={() => handleRemove(item)}
                            aria-label="刪除"
                          >
                            <TrashIcon />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="info-note" style={{ marginTop: "1.25rem" }}>
              <span aria-hidden="true">ⓘ</span>
              送出後才會正式建立訂單，商品總額不含二補、國際運費與國內運費。
            </div>
          </div>

          <div className="fl-actions">
            <Button variant="secondary" className="favorite-btn" onClick={() => setConfirmClear(true)}>
              <TrashIcon className="favorite-btn-icon" />
              清空購物車
            </Button>
            <Link className="btn btn-secondary" to="/">
              ← 繼續挑選商品
            </Link>
          </div>
        </div>

        <div className="fl-side">
          <div className="gb-panel">
            <h2 className="fl-sum-title">
              <ClipboardIcon />
              清單摘要
            </h2>
            {summaryRows.map((row) => (
              <div className="fl-sum-row" key={row.label}>
                {row.icon}
                <span className="label">{row.label}</span>
                <span className="value">{row.value}</span>
              </div>
            ))}
            <hr className="fl-sum-divider" />
            <div className="fl-sum-row">
              <span className="label">商品項目</span>
              <span className="value">{followList.items.length} 項</span>
            </div>
            <div className="fl-total-row">
              <span className="label" style={{ color: "var(--color-text-muted)" }}>
                商品總額
              </span>
              <span className="fl-total-value">NT$ {followList.estimated_product_total}</span>
            </div>
            <div className="info-note purple">
              <span aria-hidden="true">ⓘ</span>
              其他費用將由團主後續通知，不包含於商品總額。
            </div>
            <Button
              className="fl-confirm-btn"
              fullWidth
              disabled={!followList.is_submittable}
              onClick={() => navigate("/orders/confirm")}
            >
              <ClipboardIcon style={{ width: "1.1rem", height: "1.1rem" }} />
              前往確認訂單
              <ChevronRightIcon style={{ width: "1rem", height: "1rem" }} />
            </Button>
          </div>

          <div className="gb-panel">
            <button
              type="button"
              className="fl-reminder-head"
              onClick={() => setReminderOpen((v) => !v)}
              aria-expanded={reminderOpen}
            >
              <BellIcon className="bell" />
              清單提醒
              <ChevronDownIcon className={`fl-reminder-chevron${reminderOpen ? " open" : ""}`} />
            </button>
            {reminderOpen && (
              <p className="fl-reminder-body">
                若開團已結單或商品額滿，系統會保留清單內容並提示你調整後再送出。
              </p>
            )}
          </div>
        </div>
      </div>

      {confirmClear && (
        <ConfirmModal
          title="清空購物車"
          message="確定要清空目前的購物車嗎？此操作無法復原。"
          confirmLabel="確定清空"
          danger
          loading={clearing}
          onCancel={() => setConfirmClear(false)}
          onConfirm={handleClear}
        />
      )}
    </>
  );
}
