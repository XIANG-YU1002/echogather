import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getFollowList } from "../../api/followList.js";
import { getMyProfile } from "../../api/users.js";
import { createOrder } from "../../api/orders.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";

const PAYMENT_METHOD_LABELS = {
  bank_transfer: "銀行匯款",
  cash_on_delivery: "貨到付款／取貨付款",
  other: "其他",
};
const CONTACT_PLATFORM_LABELS = { facebook: "Facebook", discord: "Discord", line: "LINE" };

function formatDeadline(isoString) {
  return new Date(isoString).toLocaleString("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Taipei",
  });
}

export default function OrderConfirmPage() {
  const { token } = useAuth();
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
      <ErrorState
        title="購物車目前是空的"
        description="請先至購物車加入商品後再確認訂單。"
      >
        <Link className="btn btn-primary" to="/follow-list">
          前往購物車
        </Link>
      </ErrorState>
    );
  }

  const { group_buy: groupBuy } = followList;
  const hasContact = Boolean(profile.facebook_contact || profile.discord_contact || profile.line_contact);

  return (
    <>
      <div className="page-header">
        <h1>確認訂單</h1>
        <p className="helper-text">送出後會建立獨立訂單，不能與先前訂單合併。</p>
      </div>

      {!followList.is_submittable && (
        <Alert type="error">{followList.invalid_reasons.join("；") || "目前購物車不可送出訂單。"}</Alert>
      )}

      <div className="checkout-layout">
        <div>
          <div className="section">
            <h2 className="section-title">A. 商品確認</h2>
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
                  {followList.items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.product.name}</td>
                      <td>NT$ {item.unit_price}</td>
                      <td>{item.quantity}</td>
                      <td>NT$ {item.estimated_subtotal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="helper-text" style={{ marginTop: "0.5rem" }}>
              如需修改數量，請返回 <Link to="/follow-list">購物車</Link>。
            </p>
          </div>

          <div className="section">
            <h2 className="section-title">B. 開團資訊</h2>
            <dl className="detail-list">
              <dt>活動</dt>
              <dd>{groupBuy.activity.name}</dd>
              <dt>團主</dt>
              <dd>{groupBuy.group_leader.display_name}</dd>
              <dt>付款方式</dt>
              <dd>
                {PAYMENT_METHOD_LABELS[groupBuy.payment_method]}
                {groupBuy.payment_method_note ? `（${groupBuy.payment_method_note}）` : ""}
              </dd>
              <dt>是否二補</dt>
              <dd>{groupBuy.requires_second_payment ? "需要" : "不需要"}</dd>
              <dt>是否含滿贈</dt>
              <dd>{groupBuy.includes_full_gift ? "含滿贈" : "不含滿贈"}</dd>
              <dt>收單期限</dt>
              <dd>{formatDeadline(groupBuy.deadline_at)}</dd>
              <dt>團主主要聯絡方式</dt>
              <dd>
                {CONTACT_PLATFORM_LABELS[groupBuy.contact_platform]}：{groupBuy.contact_value}
              </dd>
            </dl>
            <Link className="btn btn-secondary" to={`/group-leaders/${groupBuy.group_leader.id}`}>
              查看團主頁面
            </Link>
          </div>

          <div className="section">
            <h2 className="section-title">C. 會員聯絡資料</h2>
            {!hasContact && (
              <Alert type="error">至少需要提供一種聯絡方式以供團主聯絡與通知。</Alert>
            )}
            <dl className="detail-list">
              {profile.facebook_contact && (
                <>
                  <dt>Facebook</dt>
                  <dd>{profile.facebook_contact}</dd>
                </>
              )}
              {profile.discord_contact && (
                <>
                  <dt>Discord</dt>
                  <dd>{profile.discord_contact}</dd>
                </>
              )}
              {profile.line_contact && (
                <>
                  <dt>LINE</dt>
                  <dd>{profile.line_contact}</dd>
                </>
              )}
            </dl>
            <Link to="/profile">修改個人聯絡資料</Link>
          </div>

          <div className="section">
            <h2 className="section-title">D. 團規確認</h2>
            <div className="rules-text" style={{ maxHeight: "220px", overflowY: "auto", border: "1px solid var(--color-border)", borderRadius: "var(--radius)", padding: "1rem" }}>
              {groupBuy.rules}
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.75rem" }}>
              <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} />
              我已閱讀並同意本次團規
            </label>
          </div>
        </div>

        <aside className="group-buy-card">
          <h2 className="section-title">訂單摘要</h2>
          <dl className="detail-list">
            <dt>商品項目數</dt>
            <dd>{followList.items.length}</dd>
            <dt>商品總額</dt>
            <dd style={{ fontWeight: 700, color: "var(--color-primary)" }}>
              NT$ {followList.estimated_product_total}
            </dd>
          </dl>
          <p className="helper-text">
            商品總額僅包含商品單價 × 數量，不包含二補、國際運費、國內運費或其他後續費用。
          </p>

          {submitError && <Alert type="error">{submitError}</Alert>}

          <Link className="btn btn-secondary btn-full" to="/follow-list" style={{ marginBottom: "0.75rem" }}>
            返回購物車
          </Link>
          <Button
            fullWidth
            loading={submitting}
            disabled={!agreed || !hasContact || !followList.is_submittable}
            onClick={handleSubmit}
          >
            送出訂單
          </Button>
        </aside>
      </div>
    </>
  );
}
