import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getGroupBuyAnnouncements, getGroupBuyDetail } from "../api/groupBuys.js";
import { addFollowListItem } from "../api/followList.js";
import { ApiError } from "../api/client.js";
import MediaImage from "../components/common/MediaImage.jsx";
import Alert from "../components/common/Alert.jsx";
import Breadcrumb from "../components/common/Breadcrumb.jsx";
import Button from "../components/common/Button.jsx";
import ConfirmModal from "../components/common/ConfirmModal.jsx";
import ErrorState from "../components/common/ErrorState.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import {
  BagIcon,
  CalendarIcon,
  ChatIcon,
  CheckCircleIcon,
  ClipboardIcon,
  CreditCardIcon,
  GiftIcon,
  RefreshIcon,
  TagIcon,
  UsersIcon,
} from "../components/common/icons.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";

const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };
const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "可取付",
  other: "其他",
};
const UNAVAILABLE_REASON_LABELS = {
  closed: "此開團已結單",
  expired: "此開團已截止",
  activity_ended: "此活動已結束",
  full: "此開團已額滿",
};

function formatDeadline(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function InfoItem({ icon, label, value, valueClass = "" }) {
  return (
    <div className="meta-chip">
      <span className="meta-chip-icon">{icon}</span>
      <span className="meta-chip-text">
        <span className="meta-chip-label">{label}</span>
        <span className={`meta-chip-value ${valueClass}`}>{value}</span>
      </span>
    </div>
  );
}

function AddToFollowListPanel({ product, groupBuy }) {
  const { isAuthenticated, token, user } = useAuth();
  const { refresh: refreshCart } = useCart();
  const navigate = useNavigate();
  const location = useLocation();

  // 管理員全程在後台作業，前台僅供瀏覽；不提供加入跟團清單，避免產生無用資料。
  const isAdmin = user?.permissions?.is_admin;

  const characters = product.characters ?? [];
  const hasCharacters = characters.length > 0;
  const multiCharacter = characters.length >= 2;

  const [quantity, setQuantity] = useState(1);
  const [selectedCharacterId, setSelectedCharacterId] = useState(
    characters.length === 1 ? characters[0].character_id : null,
  );
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [conflict, setConflict] = useState(null);

  if (isAdmin) {
    return null;
  }

  const selectedCharacter = hasCharacters
    ? characters.find((c) => c.character_id === selectedCharacterId) ?? null
    : null;
  const needsChoice = multiCharacter && !selectedCharacterId;
  const effectiveAvailable = hasCharacters
    ? selectedCharacter?.available_quantity ?? 0
    : product.available_quantity;
  const effectiveIsAvailable = hasCharacters
    ? Boolean(selectedCharacter?.is_available)
    : product.is_available;
  const maxQuantity = Math.max(effectiveAvailable, 1);

  function chooseCharacter(characterId) {
    setSelectedCharacterId(characterId);
    setQuantity(1);
    setFeedback(null);
  }

  async function submit(replaceExisting) {
    setSubmitting(true);
    setFeedback(null);
    try {
      await addFollowListItem(
        {
          group_buy_product_id: product.group_buy_product_id,
          quantity,
          replace_existing: replaceExisting,
          chosen_character_id: selectedCharacterId ?? null,
        },
        token,
      );
      setFeedback({ type: "success", message: "已加入購物車。" });
      setConflict(null);
      refreshCart();
    } catch (err) {
      if (err instanceof ApiError && err.code === "FOLLOW_LIST_GROUP_BUY_CONFLICT") {
        setConflict(true);
      } else if (err instanceof ApiError && err.code === "INSUFFICIENT_AVAILABLE_QUANTITY") {
        setFeedback({ type: "error", message: "目前可接受數量不足，請調整數量後再送出。" });
      } else {
        setFeedback({ type: "error", message: "加入購物車時發生錯誤，請稍後再試。" });
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleAddClick() {
    if (needsChoice) {
      setFeedback({ type: "error", message: "請先選擇款式／角色。" });
      return;
    }
    if (!isAuthenticated) {
      navigate("/login", {
        state: {
          redirectPath: location.pathname + location.search,
          message: "請先登入後使用購物車功能。",
        },
      });
      return;
    }
    submit(false);
  }

  return (
    <aside className="gb-panel gb-side">
      <h2 className="gb-side-title">加入購物車</h2>

      <div className="gb-side-product">
        {product.product.primary_image_url && (
          <MediaImage src={product.product.primary_image_url} alt={product.product.name} />
        )}
        <div>
          <p className="gb-side-product-name">{product.product.name}</p>
          <span className="gb-badge">{groupBuy.activity.name}</span>
        </div>
      </div>

      <div className="gb-side-row">
        <span className="label">選擇團主</span>
        <span className="value">{groupBuy.group_leader.display_name}</span>
      </div>
      <div className="gb-side-row">
        <span className="label">單價</span>
        <span className="value is-price">NT$ {product.unit_price}</span>
      </div>

      {hasCharacters && (
        <div className="gb-character-select">
          <p className="meta-chip-label" style={{ marginBottom: "0.5rem" }}>
            款式／角色{multiCharacter && <span style={{ color: "var(--color-danger)" }}> *</span>}
          </p>
          <div className="gb-character-options">
            {characters.map((character) => {
              const active = character.character_id === selectedCharacterId;
              const soldOut = !character.is_available;
              return (
                <button
                  key={character.character_id}
                  type="button"
                  className={`gb-character-option${active ? " active" : ""}${
                    soldOut ? " sold-out" : ""
                  }`}
                  aria-pressed={active}
                  onClick={() => chooseCharacter(character.character_id)}
                >
                  <span className="gb-character-name">{character.name}</span>
                  <span className="gb-character-remaining">
                    {soldOut ? "已額滿" : `剩餘 ${character.available_quantity}`}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {effectiveIsAvailable && (
        <>
          <p className="meta-chip-label" style={{ marginBottom: "0.4rem" }}>
            數量
          </p>
          <div className="gb-qty">
            <button
              type="button"
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              disabled={quantity <= 1}
              aria-label="減少數量"
            >
              −
            </button>
            <span className="qty-value">{quantity}</span>
            <button
              type="button"
              onClick={() => setQuantity((q) => Math.min(maxQuantity, q + 1))}
              disabled={quantity >= maxQuantity}
              aria-label="增加數量"
            >
              +
            </button>
          </div>
        </>
      )}

      {needsChoice ? (
        <div className="gb-status-box no">
          <span className="status-label">請先選擇款式／角色</span>
        </div>
      ) : effectiveIsAvailable ? (
        <div className="gb-status-box ok">
          <span className="status-label">
            <CheckCircleIcon />
            尚可跟團
          </span>
          <span className="remaining">剩餘 {effectiveAvailable} 個</span>
        </div>
      ) : (
        <div className="gb-status-box no">
          <span className="status-label">
            {hasCharacters
              ? "此款式／角色目前已額滿"
              : UNAVAILABLE_REASON_LABELS[groupBuy.effective_status] ?? "目前不可跟團"}
          </span>
        </div>
      )}

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      {effectiveIsAvailable ? (
        <Button
          className="gb-side-btn"
          fullWidth
          onClick={handleAddClick}
          loading={submitting}
          disabled={needsChoice}
        >
          <ClipboardIcon />
          加入購物車
        </Button>
      ) : (
        <Button className="gb-side-btn" fullWidth disabled>
          {needsChoice ? "請先選擇款式／角色" : "目前不可跟團"}
        </Button>
      )}

      <Link className="btn btn-secondary btn-full gb-side-btn" to={`/products/${product.product.id}`}>
        ← 返回商品頁
      </Link>

      {conflict && (
        <ConfirmModal
          title="替換購物車"
          message="目前購物車屬於其他開團，確定要清空並改為加入此開團的商品嗎？"
          confirmLabel="確定替換"
          onCancel={() => setConflict(null)}
          onConfirm={() => submit(true)}
          loading={submitting}
        />
      )}
    </aside>
  );
}

export default function GroupBuyDetailPage() {
  const { groupBuyId } = useParams();
  const [searchParams] = useSearchParams();
  const featuredProductId = searchParams.get("product");

  const [groupBuy, setGroupBuy] = useState(null);
  const [announcements, setAnnouncements] = useState([]);
  const [error, setError] = useState(null);

  async function load() {
    setError(null);
    setGroupBuy(null);
    try {
      const [detailResponse, announcementsResponse] = await Promise.all([
        getGroupBuyDetail(groupBuyId),
        getGroupBuyAnnouncements(groupBuyId),
      ]);
      setGroupBuy(detailResponse.data);
      setAnnouncements(announcementsResponse.data);
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBuyId]);

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState title="找不到此開團" description="開團不存在或已被移除。" />;
    }
    return <ErrorState onRetry={load} />;
  }

  if (!groupBuy) {
    return <PageLoader />;
  }

  const featuredProduct =
    groupBuy.products.find((item) => item.group_buy_product_id === featuredProductId) ??
    groupBuy.products[0];

  const otherProducts = groupBuy.products.filter(
    (item) => item.group_buy_product_id !== featuredProduct.group_buy_product_id,
  );

  return (
    <>
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: groupBuy.activity.name, to: `/activities/${groupBuy.activity.id}` },
          { label: featuredProduct.product.name, to: `/products/${featuredProduct.product.id}` },
          { label: `${groupBuy.group_leader.display_name}開團詳情` },
        ]}
      />

      <div className="gb-detail-layout">
        <div>
          <Alert type={groupBuy.is_available ? "success" : "info"}>
            {groupBuy.is_available ? "此團仍可接受訂單" : "此開團目前已停止接受新的訂單。"}
          </Alert>

          <div className="gb-panel gb-summary">
            {featuredProduct.product.primary_image_url && (
              <MediaImage
                className="gb-summary-img"
                src={featuredProduct.product.primary_image_url}
                alt={featuredProduct.product.name}
              />
            )}
            <div className="gb-summary-body">
              <h1>{featuredProduct.product.name}</h1>
              <span className="gb-badge">{groupBuy.activity.name}</span>
            </div>
          </div>

          <div className="gb-panel">
            <h2 className="section-title" style={{ marginBottom: 0 }}>
              {groupBuy.group_leader.display_name}｜開團詳情
            </h2>

            <div className="gb-info-grid">
              <InfoItem
                icon={<UsersIcon />}
                label="團主"
                value={groupBuy.group_leader.display_name}
              />
              <InfoItem
                icon={<TagIcon />}
                label="團購價格"
                value={`NT$ ${featuredProduct.unit_price}`}
                valueClass="is-price"
              />
              <InfoItem
                icon={<CreditCardIcon />}
                label="付款方式"
                value={`${PAYMENT_METHOD_LABELS[groupBuy.payment_method]}${
                  groupBuy.payment_method_note ? `（${groupBuy.payment_method_note}）` : ""
                }`}
              />
              <InfoItem
                icon={<RefreshIcon />}
                label="是否二補"
                value={groupBuy.requires_second_payment ? "是" : "否"}
              />
              {groupBuy.activity.has_full_gift && (
                <InfoItem
                  icon={<GiftIcon />}
                  label="是否含滿贈"
                  value={groupBuy.includes_full_gift ? "是" : "否"}
                />
              )}
              <InfoItem
                icon={<CalendarIcon />}
                label="收單期限"
                value={formatDeadline(groupBuy.deadline_at)}
              />
              <InfoItem
                icon={<BagIcon />}
                label="商品剩餘數量"
                value={featuredProduct.available_quantity}
              />
              <InfoItem
                icon={<CheckCircleIcon />}
                label="狀態"
                value={groupBuy.is_available ? "可跟團" : "不可跟團"}
                valueClass={groupBuy.is_available ? "is-ok" : "is-danger"}
              />
              <InfoItem
                icon={<ChatIcon />}
                label="主要聯絡方式"
                value={`${CONTACT_PLATFORM_LABELS[groupBuy.contact_platform]}：${groupBuy.contact_value}`}
              />
            </div>

            <div className="gb-rules">
              <div className="gb-rules-head">
                <ClipboardIcon />
                完整團規
              </div>
              <p className="gb-rules-text">{groupBuy.rules}</p>
            </div>

            <Link className="gb-leader-link" to={`/group-leaders/${groupBuy.group_leader.id}`}>
              查看團主公開頁
              <span aria-hidden="true">›</span>
            </Link>
          </div>

          {otherProducts.length > 0 && (
            <div className="gb-panel">
              <h2 className="section-title">此開團包含的其他商品</h2>
              <ul style={{ margin: 0, paddingLeft: "1.2rem", lineHeight: 1.9 }}>
                {otherProducts.map((item) => (
                  <li key={item.group_buy_product_id}>
                    <Link to={`/group-buys/${groupBuy.id}?product=${item.group_buy_product_id}`}>
                      {item.product.name}
                    </Link>{" "}
                    — NT$ {item.unit_price}（剩餘 {item.available_quantity} 個）
                  </li>
                ))}
              </ul>
            </div>
          )}

          {announcements.length > 0 && (
            <div className="gb-panel">
              <h2 className="section-title">開團公告</h2>
              {announcements.map((announcement) => (
                <div key={announcement.id} style={{ marginBottom: "1rem" }}>
                  <h3 style={{ margin: "0 0 0.4rem" }}>{announcement.title}</h3>
                  <p className="gb-rules-text">{announcement.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <AddToFollowListPanel
          key={featuredProduct.group_buy_product_id}
          product={featuredProduct}
          groupBuy={groupBuy}
        />
      </div>
    </>
  );
}
