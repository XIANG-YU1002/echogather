import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getActivities, getActivityProducts } from "../../api/activities.js";
import { createGroupBuy } from "../../api/groupLeaderGroupBuys.js";
import { getMyGroupLeaderProfile } from "../../api/groupLeaderProfile.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import FormField from "../../components/common/FormField.jsx";

const PAYMENT_METHODS = [
  { value: "bank_transfer", label: "匯款" },
  { value: "cash_on_delivery", label: "取貨付款" },
];
const CONTACT_PLATFORMS = [
  { value: "facebook", label: "Facebook" },
  { value: "discord", label: "Discord" },
  { value: "line", label: "LINE" },
];

export default function GroupBuyCreatePage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [activities, setActivities] = useState(null);
  const [activityId, setActivityId] = useState("");
  const [products, setProducts] = useState([]);
  const [selectedProducts, setSelectedProducts] = useState({});

  const [paymentMethod, setPaymentMethod] = useState("bank_transfer");
  const [paymentMethodNote, setPaymentMethodNote] = useState("");
  const [requiresSecondPayment, setRequiresSecondPayment] = useState(false);
  const [includesFullGift, setIncludesFullGift] = useState(false);
  const [deadlineAt, setDeadlineAt] = useState("");
  const [rules, setRules] = useState("");
  const [contactPlatform, setContactPlatform] = useState("discord");
  const [contactValue, setContactValue] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    getActivities({ status: "open", pageSize: 50 }).then((response) => setActivities(response.data));
    getMyGroupLeaderProfile(token).then((response) => {
      if (response.data.default_rules) setRules(response.data.default_rules);
      if (response.data.discord_contact) setContactValue(response.data.discord_contact);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!activityId) {
      setProducts([]);
      return;
    }
    getActivityProducts(activityId).then((response) => setProducts(response.data));
    setSelectedProducts({});
  }, [activityId]);

  const selectedActivity = activities?.find((activity) => activity.id === activityId);

  useEffect(() => {
    if (selectedActivity && !selectedActivity.has_full_gift) {
      setIncludesFullGift(false);
    }
  }, [selectedActivity]);

  function toggleProduct(product) {
    setSelectedProducts((prev) => {
      const next = { ...prev };
      if (next[product.id]) {
        delete next[product.id];
      } else {
        next[product.id] = { unit_price: "", max_quantity: "" };
      }
      return next;
    });
  }

  function updateProductField(productId, field, value) {
    setSelectedProducts((prev) => ({
      ...prev,
      [productId]: { ...prev[productId], [field]: value },
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError(null);

    const productEntries = Object.entries(selectedProducts);
    if (productEntries.length === 0) {
      setSubmitError("請至少選擇一項商品。");
      return;
    }

    setSubmitting(true);
    try {
      const response = await createGroupBuy(
        {
          activity_id: activityId,
          products: productEntries.map(([productId, values]) => ({
            product_id: productId,
            unit_price: values.unit_price,
            max_quantity: Number(values.max_quantity),
          })),
          payment_method: paymentMethod,
          payment_method_note: paymentMethodNote.trim() || null,
          requires_second_payment: requiresSecondPayment,
          includes_full_gift: includesFullGift,
          deadline_at: new Date(deadlineAt).toISOString(),
          rules,
          contact_platform: contactPlatform,
          contact_value: contactValue,
        },
        token,
      );
      navigate(`/group-leader/group-buys/${response.data.id}`, { replace: true });
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "建立開團時發生錯誤，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>建立開團</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <FormField label="選擇活動" htmlFor="gb-activity" required>
          <select
            id="gb-activity"
            value={activityId}
            onChange={(event) => setActivityId(event.target.value)}
            required
          >
            <option value="">請選擇活動</option>
            {activities?.map((activity) => (
              <option key={activity.id} value={activity.id}>
                {activity.name}
              </option>
            ))}
          </select>
        </FormField>

        {activityId && (
          <div className="section">
            <h2 className="section-title">選擇商品並設定接單資訊</h2>
            {products.length === 0 ? (
              <p className="helper-text">此活動目前沒有已上架的商品。</p>
            ) : (
              products.map((product) => {
                const selected = selectedProducts[product.id];
                return (
                  <div key={product.id} className="group-buy-card">
                    <label className="group-buy-card-row">
                      <input
                        type="checkbox"
                        checked={Boolean(selected)}
                        onChange={() => toggleProduct(product)}
                      />
                      <MediaImage
                        src={product.primary_image_url}
                        alt=""
                        style={{ width: "3rem", height: "3rem", objectFit: "cover", borderRadius: "var(--radius)" }}
                      />
                      {product.name}
                    </label>
                    {selected && (
                      <div className="group-buy-card-row" style={{ marginTop: "0.5rem" }}>
                        <label>
                          團購單價（TWD）
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            required
                            value={selected.unit_price}
                            onChange={(event) => updateProductField(product.id, "unit_price", event.target.value)}
                          />
                        </label>
                        <label>
                          接單上限
                          <input
                            type="number"
                            min="1"
                            required
                            value={selected.max_quantity}
                            onChange={(event) => updateProductField(product.id, "max_quantity", event.target.value)}
                          />
                        </label>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        <div className="section">
          <h2 className="section-title">開團設定</h2>

          <FormField label="付款方式" htmlFor="gb-payment-method" required>
            <select
              id="gb-payment-method"
              value={paymentMethod}
              onChange={(event) => setPaymentMethod(event.target.value)}
            >
              {PAYMENT_METHODS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField
            label="付款方式備註（選填）"
            htmlFor="gb-payment-note"
            helperText="可補充付款細節，例如：團費確認後再私訊告知匯款帳號、取貨地點與時間、可接受的分期方式等。不填則不會顯示。"
          >
            <input
              id="gb-payment-note"
              value={paymentMethodNote}
              onChange={(event) => setPaymentMethodNote(event.target.value)}
              placeholder="例如：團費確認後再私訊告知匯款帳號"
            />
          </FormField>

          <label className="group-buy-card-row">
            <input
              type="checkbox"
              checked={requiresSecondPayment}
              onChange={(event) => setRequiresSecondPayment(event.target.checked)}
            />
            是否需要二補
          </label>

          <label className="group-buy-card-row">
            <input
              type="checkbox"
              checked={includesFullGift}
              disabled={!selectedActivity?.has_full_gift}
              onChange={(event) => setIncludesFullGift(event.target.checked)}
            />
            是否包含滿贈
          </label>
          {selectedActivity && !selectedActivity.has_full_gift && (
            <p className="helper-text">此活動未設定滿贈，無法選擇包含滿贈。</p>
          )}

          <FormField label="收單期限" htmlFor="gb-deadline" required>
            <input
              id="gb-deadline"
              type="datetime-local"
              value={deadlineAt}
              onChange={(event) => setDeadlineAt(event.target.value)}
              required
            />
          </FormField>

          <FormField label="主要聯絡方式" htmlFor="gb-contact-platform" required>
            <select
              id="gb-contact-platform"
              value={contactPlatform}
              onChange={(event) => setContactPlatform(event.target.value)}
            >
              {CONTACT_PLATFORMS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="聯絡資料" htmlFor="gb-contact-value" required>
            <input
              id="gb-contact-value"
              value={contactValue}
              onChange={(event) => setContactValue(event.target.value)}
              required
            />
          </FormField>

          <FormField label="團規" htmlFor="gb-rules" required>
            <textarea
              id="gb-rules"
              rows={8}
              value={rules}
              onChange={(event) => setRules(event.target.value)}
              required
            />
          </FormField>
        </div>

        {submitError && <Alert type="error">{submitError}</Alert>}

        <Button type="submit" loading={submitting}>
          建立開團
        </Button>
      </form>
    </>
  );
}
