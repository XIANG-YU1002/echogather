import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getFollowList } from "../../api/followList.js";
import { getMyProfile } from "../../api/users.js";
import { createOrder } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useCart } from "../../context/CartContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import ContactValue from "../../components/common/ContactValue.jsx";
import MediaImage from "../../components/common/MediaImage.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  ArrowLeftIcon,
  ClipboardIcon,
  DiscordIcon,
  FacebookIcon,
  InfoIcon,
  LineIcon,
  PencilIcon,
} from "../../components/common/icons.jsx";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "匯款",
  cash_on_delivery: "取貨付款",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };

// 依圖 06：三個平台固定列出，未填寫者顯示灰字提示。
const CONTACT_ROWS = [
  { key: "facebook", label: "Facebook", icon: FacebookIcon, field: "facebook_contact" },
  { key: "discord", label: "Discord", icon: DiscordIcon, field: "discord_contact" },
  { key: "line", label: "LINE", icon: LineIcon, field: "line_contact" },
];

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
      <Breadcrumb
        items={[
          { label: "首頁", to: "/" },
          { label: "購物車", to: "/follow-list" },
          { label: "確認訂單" },
        ]}
      />
      <div className="oc-head">
        <h1>確認訂單</h1>
        <p>送出後會建立獨立訂單，不能與先前訂單合併。</p>
      </div>
    </>
  );
}

export default function OrderConfirmPage() {
  const { token } = useAuth();
  const { refresh: refreshCart } = useCart();
  const navigate = useNavigate();

  const [followList, setFollowList] = useState(undefined);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  function load() {
    setError(false);
    setFollowList(undefined);
    Promise.all([getFollowList(token), getMyProfile(token)])
      .then(([followListResponse, profileResponse]) => {
        setFollowList(followListResponse.data);
        setProfile(profileResponse.data);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await createOrder(true, token);
      // 後端下單成功後會刪除跟團清單，這裡同步更新 Header 的購物車數量，
      // 否則紅點會殘留到下次重新整理。
      await refreshCart();
      navigate(`/orders/${response.data.id}`, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError("送出訂單時發生錯誤，請稍後再試。");
      }
    } finally {
      setSubmitting(false);
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
        <ErrorState title="購物車目前是空的" description="請先至購物車加入商品後再確認訂單。">
          <Link className="btn btn-primary" to="/follow-list">
            前往購物車
          </Link>
        </ErrorState>
      </>
    );
  }

  const { group_buy: groupBuy } = followList;
  const hasContact = Boolean(
    profile.facebook_contact || profile.discord_contact || profile.line_contact,
  );
  const showFullGift = groupBuy.activity.has_full_gift;

  const groupBuyRows = [
    { label: "活動", value: groupBuy.activity.name },
    { label: "團主", value: groupBuy.group_leader.display_name },
    {
      label: "付款方式",
      value: `${PAYMENT_METHOD_LABELS[groupBuy.payment_method]}${
        groupBuy.payment_method_note ? `（${groupBuy.payment_method_note}）` : ""
      }`,
    },
    { label: "是否二補", value: groupBuy.requires_second_payment ? "是" : "否" },
    ...(showFullGift
      ? [{ label: "是否包含滿贈", value: groupBuy.includes_full_gift ? "是" : "否" }]
      : []),
    { label: "收單期限", value: formatDeadline(groupBuy.deadline_at) },
    {
      label: "團主主要聯絡方式",
      // Facebook 的值是一長串網址，直接印會把左邊的標籤壓成一個字一行；
      // 平台名＋ID 也比其他列長，套用與訂單詳情頁同一組「維持單排」的樣式。
      value: (
        <span className="contact-inline">
          <span className="oc-contact-platform">
            {CONTACT_PLATFORM_LABELS[groupBuy.contact_platform]}：
          </span>
          <ContactValue
            platform={groupBuy.contact_platform}
            value={groupBuy.contact_value}
            displayName={groupBuy.group_leader.display_name}
            className="oc-contact-link"
          />
        </span>
      ),
    },
  ];

  return (
    <>
      <PageHead />

      {!followList.is_submittable && (
        <Alert type="error">
          {followList.invalid_reasons.join("；") || "目前購物車不可送出訂單。"}
        </Alert>
      )}

      <div className="checkout-layout">
        <div>
          <div className="gb-panel">
            <h2 className="section-title plain">A. 商品確認</h2>

            <div className="table-wrap" style={{ border: "none" }}>
              <table className="table oc-table">
                <thead>
                  <tr>
                    <th>商品</th>
                    <th>款式 / 角色</th>
                    <th className="oc-num">單價</th>
                    <th className="oc-num">數量</th>
                    <th className="oc-num">小計</th>
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
                          <div className="oc-product">
                            <MediaImage
                              className="oc-product-thumb"
                              src={item.product.primary_image_url}
                              alt={item.product.name}
                            />
                            <div className="oc-product-text">
                              <Link to={`/products/${item.product.id}`}>{item.product.name}</Link>
                              <span className="gb-badge">{groupBuy.activity.name}</span>
                            </div>
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
                        <td className="oc-num">NT${item.unit_price}</td>
                        <td className="oc-num">{item.quantity}</td>
                        <td className="oc-num">
                          <span className="fl-subtotal">NT${item.estimated_subtotal}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="info-note" style={{ marginTop: "1.25rem" }}>
              <InfoIcon />
              <span>
                如需修改數量，請返回 <Link to="/follow-list">購物車</Link>。
              </span>
            </div>
          </div>

          <div className="two-col-section">
            <div className="gb-panel">
              <h2 className="section-title plain">B. 開團資訊</h2>
              {groupBuyRows.map((row) => (
                <div className="oc-row" key={row.label}>
                  <span className="label">{row.label}</span>
                  <span className="value">{row.value}</span>
                </div>
              ))}
              <Link
                className="btn btn-secondary btn-full oc-leader-btn"
                to={`/group-leaders/${groupBuy.group_leader.id}`}
              >
                <ClipboardIcon />
                查看團主頁面
              </Link>
            </div>

            <div className="gb-panel">
              <h2 className="section-title plain">C. 會員聯絡資料</h2>
              {CONTACT_ROWS.map(({ key, label, icon: Icon, field }) => (
                <div className="oc-contact-row" key={key}>
                  <Icon className="oc-contact-icon" />
                  <span className="oc-contact-name">{label}</span>
                  {profile[field] ? (
                    <ContactValue
                      platform={key}
                      value={profile[field]}
                      displayName={profile.nickname}
                      className="oc-contact-value"
                    />
                  ) : (
                    <span className="oc-contact-value empty">未填寫</span>
                  )}
                </div>
              ))}
              <p className="oc-contact-hint">至少需要提供一種聯絡方式以供團主聯絡與通知。</p>
              {!hasContact && (
                <Alert type="error">尚未填寫任何聯絡方式，請先補齊後才能送出訂單。</Alert>
              )}
              <Link className="oc-contact-edit" to="/profile">
                <PencilIcon />
                修改個人聯絡資料
              </Link>
            </div>
          </div>

          <div className="gb-panel">
            <h2 className="section-title plain">D. 團規確認</h2>
            <div className="oc-rules rules-text">{groupBuy.rules}</div>
            <label className="oc-agree">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(event) => setAgreed(event.target.checked)}
              />
              <span>我已閱讀並同意本次團規</span>
            </label>
          </div>
        </div>

        <aside className="fl-side">
          <div className="gb-panel">
            <h2 className="fl-sum-title">
              <ClipboardIcon />
              訂單摘要
            </h2>
            <div className="fl-sum-row">
              <span className="label">商品項目數</span>
              <span className="value">{followList.items.length}</span>
            </div>
            <div className="fl-total-row">
              <span className="label" style={{ color: "var(--color-text-muted)" }}>
                商品總額
              </span>
              <span className="fl-total-value">NT${followList.estimated_product_total}</span>
            </div>
            <div className="info-note purple">
              <InfoIcon />
              <span>
                商品總額僅包含商品單價 × 數量，不包含二補、國際運費、國內運費或其他後續費用。
              </span>
            </div>

            {submitError && <Alert type="error">{submitError}</Alert>}

            <Link className="btn btn-secondary btn-full oc-back-btn" to="/follow-list">
              <ArrowLeftIcon />
              返回購物車
            </Link>
            <Button
              className="fl-confirm-btn"
              fullWidth
              loading={submitting}
              disabled={!agreed || !hasContact || !followList.is_submittable}
              onClick={handleSubmit}
            >
              <ClipboardIcon style={{ width: "1.1rem", height: "1.1rem" }} />
              送出訂單
            </Button>
          </div>
        </aside>
      </div>
    </>
  );
}
