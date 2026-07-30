import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getActivities, getActivityProducts } from "../../api/activities.js";
import { createGroupBuy } from "../../api/groupLeaderGroupBuys.js";
import { getMyGroupLeaderProfile } from "../../api/groupLeaderProfile.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import {
  ArrowLeftIcon,
  CheckIcon,
  InfoIcon,
  SaveIcon,
  TrashIcon,
} from "../../components/common/icons.jsx";

/**
 * 欄位標籤，附圖 24 的說明圖示。
 *
 * 提示用自繪的 tooltip 而非原生 title：原生要 hover 約一秒才出現、樣式也不受控，
 * 容易讓人以為圖示沒有作用。
 */
function FieldLabel({ children, hint, htmlFor }) {
  const Tag = htmlFor ? "label" : "span";
  return (
    <Tag className="gbc-label" htmlFor={htmlFor}>
      {children}
      <span className="gbc-info" data-tip={hint} tabIndex={0} role="note" aria-label={hint}>
        <InfoIcon />
      </span>
    </Tag>
  );
}

// 依使用者 2026-07-29 裁決只做兩種付款方式（資料庫也只有這兩個值）；
// 其他付款細節寫在「付款方式備註」。
const PAYMENT_METHODS = [
  { value: "bank_transfer", label: "匯款" },
  { value: "cash_on_delivery", label: "取貨付款" },
];
const CONTACT_PLATFORMS = [
  { value: "facebook", label: "Facebook" },
  { value: "discord", label: "Discord" },
  { value: "line", label: "LINE" },
];
const RULES_MAX_LENGTH = 2000;

export default function GroupBuyCreatePage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [activities, setActivities] = useState(null);
  const [activityId, setActivityId] = useState("");
  const [products, setProducts] = useState([]);
  // { [productId]: { unit_price, max_quantity, character_quantities: { [characterId]: value } } }
  const [selectedProducts, setSelectedProducts] = useState({});

  const [paymentMethod, setPaymentMethod] = useState("bank_transfer");
  const [paymentMethodNote, setPaymentMethodNote] = useState("");
  const [requiresSecondPayment, setRequiresSecondPayment] = useState(false);
  const [includesFullGift, setIncludesFullGift] = useState(false);
  const [deadlineAt, setDeadlineAt] = useState("");
  const [rules, setRules] = useState("");
  const [contactPlatform, setContactPlatform] = useState("discord");

  // 主要聯絡方式一律取自團主資料（依使用者裁決，同開團設定頁）
  const [profileContacts, setProfileContacts] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    getActivities({ status: "open", pageSize: 50 }).then((response) =>
      setActivities(response.data),
    );
    getMyGroupLeaderProfile(token).then((response) => {
      if (response.data.default_rules) setRules(response.data.default_rules);
      const contacts = {
        facebook: response.data.facebook_url,
        discord: response.data.discord_contact,
        line: response.data.line_contact,
      };
      setProfileContacts(contacts);
      // 預設選第一個已設定的平台，避免一進來就停在未設定的選項
      const firstAvailable = CONTACT_PLATFORMS.find((option) => contacts[option.value]);
      if (firstAvailable) setContactPlatform(firstAvailable.value);
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

  const selectedEntries = useMemo(
    () =>
      products
        .filter((product) => selectedProducts[product.id])
        .map((product) => ({ product, values: selectedProducts[product.id] })),
    [products, selectedProducts],
  );

  const allSelected = products.length > 0 && selectedEntries.length === products.length;
  const contactValue = profileContacts?.[contactPlatform] ?? "";
  const contactMissing = profileContacts !== null && !contactValue;

  function emptySelection(product) {
    return {
      unit_price: "",
      max_quantity: "",
      character_quantities: Object.fromEntries(
        product.characters.map((character) => [character.id, ""]),
      ),
    };
  }

  function toggleProduct(product) {
    setSelectedProducts((prev) => {
      const next = { ...prev };
      if (next[product.id]) {
        delete next[product.id];
      } else {
        next[product.id] = emptySelection(product);
      }
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedProducts((prev) => {
      if (products.length > 0 && Object.keys(prev).length === products.length) {
        return {};
      }
      return Object.fromEntries(
        products.map((product) => [product.id, prev[product.id] ?? emptySelection(product)]),
      );
    });
  }

  function updateProductField(productId, field, value) {
    setSelectedProducts((prev) => ({
      ...prev,
      [productId]: { ...prev[productId], [field]: value },
    }));
  }

  function updateCharacterQuantity(productId, characterId, value) {
    setSelectedProducts((prev) => ({
      ...prev,
      [productId]: {
        ...prev[productId],
        character_quantities: { ...prev[productId].character_quantities, [characterId]: value },
      },
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError(null);

    if (selectedEntries.length === 0) {
      setSubmitError("請至少選擇一項商品。");
      return;
    }
    if (contactMissing) {
      setSubmitError("請先於團主資料設定該聯絡方式，才能建立開團。");
      return;
    }
    // 多角色商品可以把不接的角色設 0，但不能全部設 0——那等於整個商品都不接，
    // 應該直接取消勾選。單一角色的 0 由輸入框 min="1" 擋掉。
    const allZeroProduct = selectedEntries.find(({ product, values }) => {
      if (product.characters.length < 2) return false;
      return product.characters.every(
        (character) => Number(values.character_quantities?.[character.id]) === 0,
      );
    });
    if (allZeroProduct) {
      setSubmitError(
        `「${allZeroProduct.product.name}」的所有角色接單上限都是 0，請至少開放一個角色，或取消勾選這項商品。`,
      );
      return;
    }

    setSubmitting(true);
    try {
      const response = await createGroupBuy(
        {
          activity_id: activityId,
          products: selectedEntries.map(({ product, values }) => {
            const characterQuantities = product.characters
              .map((character) => ({
                character_id: character.id,
                max_quantity: Number(values.character_quantities?.[character.id]),
              }))
              // 0＝不接這個角色的單，一定要送出去（濾掉就會被後端 fallback 成商品上限）；
              // 只有沒填的欄位（空字串轉成 NaN）才略過。
              .filter((entry) => Number.isFinite(entry.max_quantity) && entry.max_quantity >= 0);
            return {
              product_id: product.id,
              unit_price: values.unit_price,
              // 多角色商品的整體上限由後端加總各角色，這裡送總和保持一致；
              // 無角色商品才真正使用這個值。
              max_quantity:
                product.characters.length > 0
                  ? Math.max(
                      characterQuantities.reduce((sum, entry) => sum + entry.max_quantity, 0),
                      1,
                    )
                  : Number(values.max_quantity),
              character_quantities: characterQuantities,
            };
          }),
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
      setSubmitError(
        err instanceof ApiError ? err.message : "建立開團時發生錯誤，請稍後再試。",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>建立開團</h1>
        <p className="helper-text">依照步驟建立您的團購活動</p>
      </div>

      <form onSubmit={handleSubmit}>
        <section className="gbc-card gbc-activity">
          <div>
            <h2 className="gbc-card-title">選擇活動</h2>
            <p className="helper-text" style={{ margin: 0 }}>
              請先選擇要開團的活動
            </p>
          </div>
          <select
            aria-label="選擇活動"
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
        </section>

        {activityId && (
          <section className="gbc-card">
            <div className="gbc-card-head">
              <div>
                <h2 className="gbc-card-title">請選擇要開團的商品</h2>
                <p className="helper-text" style={{ margin: 0 }}>
                  可複選多個商品
                </p>
              </div>
              {products.length > 0 && (
                <button type="button" className="gbc-select-all" onClick={toggleSelectAll}>
                  <span className={`gbc-checkbox${allSelected ? " is-checked" : ""}`}>
                    {allSelected && <CheckIcon />}
                  </span>
                  全選
                </button>
              )}
            </div>

            {products.length === 0 ? (
              <p className="helper-text">此活動目前沒有已上架的商品。</p>
            ) : (
              <div className="gbc-product-grid">
                {products.map((product) => {
                  const selected = Boolean(selectedProducts[product.id]);
                  return (
                    <button
                      type="button"
                      key={product.id}
                      className={`gbc-product-card${selected ? " is-selected" : ""}`}
                      onClick={() => toggleProduct(product)}
                      aria-pressed={selected}
                    >
                      <img
                        className="gbc-product-image"
                        src={resolveMediaUrl(product.primary_image_url)}
                        alt=""
                      />
                      <span className="gbc-product-info">
                        <span className="gbc-product-name">{product.name}</span>
                        <span className="gbc-product-price">
                          {product.official_price
                            ? `NT$ ${Number(product.official_price)}`
                            : "官方未定價"}
                        </span>
                        {product.characters.length > 0 && (
                          <span className="gbc-product-characters">
                            {product.characters.length} 個角色
                          </span>
                        )}
                      </span>
                      <span className={`gbc-checkbox${selected ? " is-checked" : ""}`}>
                        {selected && <CheckIcon />}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {selectedEntries.length > 0 && (
          <section className="gbc-card">
            <h2 className="gbc-card-title">
              已選擇商品
              <span className="gbc-card-note">（可調整各商品設定）</span>
            </h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>商品</th>
                    <th>團購價格（每件）</th>
                    <th>接單角色</th>
                    <th>接單上限數量（件）</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedEntries.map(({ product, values }) => (
                    <tr key={product.id}>
                      <td>
                        <span className="gbe-product">
                          <img
                            className="gbe-product-image"
                            src={resolveMediaUrl(product.primary_image_url)}
                            alt=""
                          />
                          {product.name}
                        </span>
                      </td>
                      <td>
                        <span className="gbc-price-input">
                          <span className="gbc-currency">NT$</span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            required
                            aria-label={`${product.name} 團購價格`}
                            value={values.unit_price}
                            onChange={(event) =>
                              updateProductField(product.id, "unit_price", event.target.value)
                            }
                          />
                        </span>
                      </td>
                      {/* 角色與數量拆成兩欄，逐行對齊；無角色商品的角色欄留空 */}
                      <td>
                        <div className="gbc-stack">
                          {product.characters.length > 0 ? (
                            product.characters.map((character) => (
                              <span key={character.id} className="gbc-stack-row">
                                {character.name}
                              </span>
                            ))
                          ) : (
                            <span className="gbc-stack-row gbc-stack-empty" aria-hidden="true" />
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="gbc-stack">
                          {product.characters.length > 0 ? (
                            product.characters.map((character) => (
                              <span key={character.id} className="gbc-stack-row">
                                <input
                                  type="number"
                                  // 多角色商品可填 0＝不接這個角色的單；
                                  // 只有一個角色時填 0 等於整個商品不接，不允許。
                                  min={product.characters.length > 1 ? "0" : "1"}
                                  required
                                  title={
                                    product.characters.length > 1
                                      ? "填 0 表示不接這個角色的單"
                                      : undefined
                                  }
                                  aria-label={`${product.name} ${character.name} 接單上限`}
                                  value={values.character_quantities?.[character.id] ?? ""}
                                  onChange={(event) =>
                                    updateCharacterQuantity(
                                      product.id,
                                      character.id,
                                      event.target.value,
                                    )
                                  }
                                />
                              </span>
                            ))
                          ) : (
                            <span className="gbc-stack-row">
                              <input
                                type="number"
                                min="1"
                                required
                                aria-label={`${product.name} 接單上限`}
                                value={values.max_quantity}
                                onChange={(event) =>
                                  updateProductField(product.id, "max_quantity", event.target.value)
                                }
                              />
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="gbc-remove"
                          onClick={() => toggleProduct(product)}
                          aria-label={`移除 ${product.name}`}
                        >
                          <TrashIcon />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="gbc-card">
          <h2 className="gbc-card-title">
            開團整體設定
            <span className="gbc-card-note">（本區適用所有商品）</span>
          </h2>

          {/* 依圖 24 的三欄配置：付款相關｜時間與聯絡｜滿贈與團規 */}
          <div className="gbc-settings-grid">
            <div className="gbc-settings-col">
              <div className="gbc-setting">
                <FieldLabel hint="團員要用哪種方式付款；細節可寫在下方備註">付款方式</FieldLabel>
                <div className="gbc-radio-row">
                  {PAYMENT_METHODS.map((option) => (
                    <label key={option.value} className="gbc-radio">
                      <input
                        type="radio"
                        name="payment-method"
                        value={option.value}
                        checked={paymentMethod === option.value}
                        onChange={(event) => setPaymentMethod(event.target.value)}
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
                <input
                  aria-label="付款方式備註"
                  value={paymentMethodNote}
                  placeholder="備註（選填），例如：收單後再私訊匯款帳號"
                  onChange={(event) => setPaymentMethodNote(event.target.value)}
                />
              </div>

              <div className="gbc-setting">
                <FieldLabel hint="運費或匯差等後續是否需要再向團員補收款項">是否二補</FieldLabel>
                <div className="gbc-radio-row">
                  <label className="gbc-radio">
                    <input
                      type="radio"
                      name="second-payment"
                      checked={requiresSecondPayment}
                      onChange={() => setRequiresSecondPayment(true)}
                    />
                    是
                  </label>
                  <label className="gbc-radio">
                    <input
                      type="radio"
                      name="second-payment"
                      checked={!requiresSecondPayment}
                      onChange={() => setRequiresSecondPayment(false)}
                    />
                    否
                  </label>
                </div>
              </div>
            </div>

            <div className="gbc-settings-col">
              <div className="gbc-setting">
                <FieldLabel htmlFor="gb-deadline" hint="收單截止時間，過了此時間團員無法再跟團">
                  收單日期
                </FieldLabel>
                <input
                  id="gb-deadline"
                  type="datetime-local"
                  value={deadlineAt}
                  onChange={(event) => setDeadlineAt(event.target.value)}
                  required
                />
                <p className="gbe-hint">建立後可提早或延後，但不可早於目前時間</p>
              </div>

              <div className="gbc-setting">
                <FieldLabel
                  htmlFor="gb-contact-platform"
                  hint="供團員聯絡與付款通知使用，內容取自團主資料"
                >
                  主要聯絡方式
                </FieldLabel>
                <select
                  id="gb-contact-platform"
                  value={contactPlatform}
                  onChange={(event) => setContactPlatform(event.target.value)}
                >
                  {CONTACT_PLATFORMS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                      {profileContacts && !profileContacts[option.value] ? "（未設定）" : ""}
                    </option>
                  ))}
                </select>
                {contactMissing ? (
                  <p className="gbe-hint gbe-hint-warn">
                    團主資料尚未設定此聯絡方式，請先到{" "}
                    <Link to="/group-leader/profile">團主資料</Link> 填寫。
                  </p>
                ) : (
                  <p className="gbe-hint">
                    將使用：{contactValue || "—"}（取自
                    <Link to="/group-leader/profile">團主資料</Link>）
                  </p>
                )}
              </div>
            </div>

            <div className="gbc-settings-col">
              {/* 依圖 24：標籤與開關同一行 */}
              <div className="gbc-setting">
                <div className="gbc-setting-inline">
                  <FieldLabel hint="此團是否包含官方滿額贈品，僅支援滿贈的活動可開啟">
                    是否含滿贈
                  </FieldLabel>
                  <label className="gbc-switch">
                    <input
                      type="checkbox"
                      checked={includesFullGift}
                      disabled={!selectedActivity?.has_full_gift}
                      onChange={(event) => setIncludesFullGift(event.target.checked)}
                    />
                    <span className="gbc-switch-track" aria-hidden="true" />
                    <span className="gbc-switch-text">
                      {includesFullGift ? "包含" : "不含"}
                    </span>
                  </label>
                </div>
                {selectedActivity && !selectedActivity.has_full_gift && (
                  <p className="gbe-hint">此活動未設定滿贈，無法選擇包含滿贈。</p>
                )}
              </div>

              <div className="gbc-setting gbc-setting-rules">
                <FieldLabel htmlFor="gb-rules" hint="團員下單前必須閱讀的規則，可沿用團主資料的預設團規">
                  團規／備註
                </FieldLabel>
                <textarea
                  id="gb-rules"
                  rows={9}
                  maxLength={RULES_MAX_LENGTH}
                  value={rules}
                  onChange={(event) => setRules(event.target.value)}
                  required
                />
                <p className="gbc-counter">
                  {rules.length} / {RULES_MAX_LENGTH}
                </p>
              </div>
            </div>
          </div>
        </section>

        {submitError && <Alert type="error">{submitError}</Alert>}

        <div className="gbe-actions">
          <Link className="btn btn-secondary gbe-back" to="/group-leader/group-buys">
            <ArrowLeftIcon />
            返回
          </Link>
          <Button
            type="submit"
            loading={submitting}
            disabled={contactMissing}
            className="gbe-submit"
          >
            <SaveIcon />
            確認建立
          </Button>
        </div>
      </form>
    </>
  );
}
