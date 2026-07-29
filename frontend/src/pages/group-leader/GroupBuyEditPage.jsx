import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getActivityProducts } from "../../api/activities.js";
import {
  addGroupBuyProduct,
  closeGroupBuy,
  getMyGroupBuyDetail,
  removeGroupBuyProduct,
  updateGroupBuyProduct,
  updateGroupBuySettings,
} from "../../api/groupLeaderGroupBuys.js";
import { getMyGroupLeaderProfile } from "../../api/groupLeaderProfile.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import GroupBuyTabs from "../../components/group-leader/GroupBuyTabs.jsx";
import {
  AlertTriangleIcon,
  ArrowLeftIcon,
  LockIcon,
  SaveIcon,
} from "../../components/common/icons.jsx";

const PAYMENT_METHODS = [
  { value: "bank_transfer", label: "匯款" },
  { value: "cash_on_delivery", label: "取貨付款" },
];
const CONTACT_PLATFORMS = [
  { value: "facebook", label: "Facebook" },
  { value: "discord", label: "Discord" },
  { value: "line", label: "LINE" },
];

function toDatetimeLocal(isoString) {
  const date = new Date(isoString);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

export default function GroupBuyEditPage() {
  const { groupBuyId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();

  const [groupBuy, setGroupBuy] = useState(null);
  const [error, setError] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [saving, setSaving] = useState(false);
  const [closing, setClosing] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);

  const [settings, setSettings] = useState(null);
  const [productMaxQuantities, setProductMaxQuantities] = useState({});

  const [newProducts, setNewProducts] = useState([]);
  const [newProductId, setNewProductId] = useState("");
  const [newUnitPrice, setNewUnitPrice] = useState("");
  const [newMaxQuantity, setNewMaxQuantity] = useState("");

  // 團主資料的公開聯絡方式：開團的主要聯絡方式一律取自這裡
  const [profileContacts, setProfileContacts] = useState(null);

  function load() {
    setError(false);
    setGroupBuy(null);
    getMyGroupBuyDetail(groupBuyId, token)
      .then((response) => {
        const data = response.data;
        setGroupBuy(data);
        setSettings({
          payment_method: data.payment_method,
          payment_method_note: data.payment_method_note ?? "",
          requires_second_payment: data.requires_second_payment,
          includes_full_gift: data.includes_full_gift,
          deadline_at: toDatetimeLocal(data.deadline_at),
          rules: data.rules,
          contact_platform: data.contact_platform,
          contact_value: data.contact_value,
        });
        setProductMaxQuantities(
          Object.fromEntries(data.products.map((item) => [item.id, item.max_quantity])),
        );
        if (!data.has_orders) {
          getActivityProducts(data.activity.id).then((productResponse) => {
            const ownedIds = new Set(data.products.map((item) => item.product.id));
            setNewProducts(productResponse.data.filter((p) => !ownedIds.has(p.id)));
          });
        }
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBuyId]);

  useEffect(() => {
    getMyGroupLeaderProfile(token)
      .then((response) =>
        setProfileContacts({
          facebook: response.data.facebook_url,
          discord: response.data.discord_contact,
          line: response.data.line_contact,
        }),
      )
      .catch(() => setProfileContacts(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function isEditable(field) {
    return groupBuy?.editable_fields.includes(field);
  }

  /** 切換平台時同步帶入團主資料該平台的值；未設定則留空，交由提示說明。 */
  function handleChangeContactPlatform(platform) {
    setSettings((prev) => ({
      ...prev,
      contact_platform: platform,
      contact_value: profileContacts?.[platform] ?? "",
    }));
  }

  async function handleSaveSettings(event) {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      const payload = {};
      for (const field of groupBuy.editable_fields) {
        if (field === "max_quantity") continue;
        if (field === "deadline_at") {
          payload.deadline_at = new Date(settings.deadline_at).toISOString();
        } else if (field === "payment_method_note") {
          // 選填欄位：留白代表清除備註
          payload.payment_method_note = settings.payment_method_note.trim() || null;
        } else {
          payload[field] = settings[field];
        }
      }
      await updateGroupBuySettings(groupBuyId, payload, token);
      setFeedback({ type: "success", message: "開團設定已儲存。" });
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "儲存時發生錯誤。" });
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveMaxQuantity(groupBuyProductId) {
    setFeedback(null);
    try {
      await updateGroupBuyProduct(
        groupBuyId,
        groupBuyProductId,
        { max_quantity: Number(productMaxQuantities[groupBuyProductId]) },
        token,
      );
      setFeedback({ type: "success", message: "接單上限已更新。" });
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "更新時發生錯誤。" });
    }
  }

  async function handleRemoveProduct(groupBuyProductId) {
    setFeedback(null);
    try {
      await removeGroupBuyProduct(groupBuyId, groupBuyProductId, token);
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "移除商品時發生錯誤。" });
    }
  }

  async function handleAddProduct(event) {
    event.preventDefault();
    setFeedback(null);
    try {
      await addGroupBuyProduct(
        groupBuyId,
        { product_id: newProductId, unit_price: newUnitPrice, max_quantity: Number(newMaxQuantity) },
        token,
      );
      setNewProductId("");
      setNewUnitPrice("");
      setNewMaxQuantity("");
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "新增商品時發生錯誤。" });
    }
  }

  async function handleClose() {
    setClosing(true);
    try {
      await closeGroupBuy(groupBuyId, token);
      setConfirmClose(false);
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err instanceof ApiError ? err.message : "結單時發生錯誤。" });
    } finally {
      setClosing(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!groupBuy) {
    return <PageLoader />;
  }

  const productTotal = groupBuy.products.reduce(
    (sum, item) => sum + Number(item.unit_price) * item.occupied_quantity,
    0,
  );
  const remainingSlots = groupBuy.products.reduce((sum, item) => sum + item.available_quantity, 0);
  const maxSlots = groupBuy.products.reduce((sum, item) => sum + item.max_quantity, 0);

  const roundLabel = `第 ${groupBuy.round_number} 團`;
  const currentPlatformLabel =
    CONTACT_PLATFORMS.find((option) => option.value === settings.contact_platform)?.label ??
    settings.contact_platform;
  // 團主資料還沒載入時不顯示警告，避免閃現誤導
  const currentContactMissing =
    profileContacts !== null && !profileContacts[settings.contact_platform];
  const occupiedTotal = groupBuy.products.reduce((sum, item) => sum + item.occupied_quantity, 0);
  const paymentMethodLabel =
    PAYMENT_METHODS.find((option) => option.value === groupBuy.payment_method)?.label ??
    groupBuy.payment_method;
  const contactPlatformLabel =
    CONTACT_PLATFORMS.find((option) => option.value === groupBuy.contact_platform)?.label ??
    groupBuy.contact_platform;
  // 團規以換行分條顯示（唯讀時）
  const ruleLines = groupBuy.rules.split("\n").filter((line) => line.trim());

  return (
    <>
      <Breadcrumb
        items={[
          { label: "我的開團", to: "/group-leader/group-buys" },
          {
            label: groupBuy.activity.name,
            to: `/group-leader/group-buys?keyword=${encodeURIComponent(groupBuy.activity.name)}`,
          },
          { label: roundLabel, to: `/group-leader/group-buys/${groupBuyId}/product-orders` },
          { label: "開團設定" },
        ]}
      />

      <div className="page-header">
        <h1>開團設定</h1>
      </div>

      <GroupBuyTabs groupBuyId={groupBuyId} />

      {groupBuy.has_orders && (
        <div className="gbe-lock-notice">
          <AlertTriangleIcon className="gbe-lock-icon" />
          <div>
            <p className="gbe-lock-title">此開團已有訂單，部分欄位已鎖定</p>
            <p className="gbe-lock-desc">
              不可編輯的欄位已鎖定，僅可調整截止時間、聯絡方式與商品接單上限。
            </p>
          </div>
        </div>
      )}
      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-card">
          <p className="stat-card-label">商品總額（已下單）</p>
          <p className="stat-card-value">NT$ {productTotal}</p>
        </div>
        <div className="stat-card">
          <p className="stat-card-label">剩餘名額</p>
          <p className="stat-card-value">
            {remainingSlots} / {maxSlots}
          </p>
        </div>
      </div>

      <form onSubmit={handleSaveSettings}>
        <section className="gbe-card">
          <h2 className="gbe-card-title">基本資訊</h2>
          <div className="gbe-grid">
            <div className="gbe-field">
              <span className="gbe-label">開團名稱</span>
              {/* 資料庫沒有開團名稱欄位（使用者裁決不新增），以活動名稱組出輪次 */}
              <p className="gbe-readonly">
                {groupBuy.activity.name} - {roundLabel}
                <LockIcon className="gbe-lock-mark" />
              </p>
            </div>

            <div className="gbe-field">
              <span className="gbe-label">所屬活動</span>
              <p className="gbe-readonly">
                {groupBuy.activity.name}
                <LockIcon className="gbe-lock-mark" />
              </p>
            </div>

            <div className="gbe-field">
              <span className="gbe-label">開團狀態</span>
              <p className="gbe-status">
                <span
                  className={`status-badge ${
                    groupBuy.status === "open" ? "status-badge-success" : "status-badge-neutral"
                  }`}
                >
                  {groupBuy.status === "open" ? "進行中" : "已結單"}
                </span>
              </p>
            </div>

            <div className="gbe-field">
              <label className="gbe-label" htmlFor="edit-deadline">
                截止時間
              </label>
              <input
                id="edit-deadline"
                type="datetime-local"
                value={settings.deadline_at}
                disabled={!isEditable("deadline_at")}
                onChange={(event) =>
                  setSettings((prev) => ({ ...prev, deadline_at: event.target.value }))
                }
              />
              {/* 依 Business Rules §16.5：可延長也可縮短，只是不能改到過去。
                  參考圖只寫「可延後」，與規格不符，故改寫。 */}
              <p className="gbe-hint">
                可提早或延後，但不可早於目前時間；要立即停止收單請用下方的「提前結單」
              </p>
            </div>

            <div className="gbe-field">
              <label className="gbe-label" htmlFor="edit-contact-platform">
                主要聯絡方式
              </label>
              <div className="gbe-contact">
                <select
                  id="edit-contact-platform"
                  value={settings.contact_platform}
                  disabled={!isEditable("contact_platform")}
                  onChange={(event) => handleChangeContactPlatform(event.target.value)}
                >
                  {CONTACT_PLATFORMS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                      {profileContacts && !profileContacts[option.value] ? "（未設定）" : ""}
                    </option>
                  ))}
                </select>
                {/* 值一律取自團主資料，不在此輸入，避免同一團主在各開團留下不一致的聯絡資訊 */}
                <p className="gbe-readonly gbe-contact-value">
                  {settings.contact_value || "—"}
                  <LockIcon className="gbe-lock-mark" />
                </p>
              </div>
              {currentContactMissing ? (
                <p className="gbe-hint gbe-hint-warn">
                  團主資料尚未設定{currentPlatformLabel}，請先到{" "}
                  <Link to="/group-leader/profile">團主資料</Link> 填寫後才能設為主要聯絡方式。
                </p>
              ) : (
                <p className="gbe-hint">
                  供團員聯絡與付款通知使用；內容取自
                  <Link to="/group-leader/profile">團主資料</Link>，需修改請至該頁。
                </p>
              )}
            </div>

            <div className="gbe-field">
              <span className="gbe-label">最大數量</span>
              <p className="gbe-readonly">
                {maxSlots}
                <LockIcon className="gbe-lock-mark" />
              </p>
              <p className="gbe-hint">各商品接單上限的總和，要調整請至下方商品列表</p>
            </div>

            <div className="gbe-field">
              <span className="gbe-label">已接單數量</span>
              <p className="gbe-readonly">
                {occupiedTotal}
                <LockIcon className="gbe-lock-mark" />
              </p>
              <p className="gbe-hint">此數量包含所有已建立的訂單</p>
            </div>
          </div>
        </section>

        <div className="gbe-mini-cards">
          <section className="gbe-card gbe-mini-card">
            <h3 className="gbe-mini-title">
              {!isEditable("payment_method") && <LockIcon />}
              付款方式
            </h3>
            {isEditable("payment_method") ? (
              <>
                <select
                  aria-label="付款方式"
                  value={settings.payment_method}
                  onChange={(event) =>
                    setSettings((prev) => ({ ...prev, payment_method: event.target.value }))
                  }
                >
                  {PAYMENT_METHODS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="付款方式備註"
                  value={settings.payment_method_note}
                  placeholder="備註（選填），例如：收單後再私訊匯款帳號"
                  onChange={(event) =>
                    setSettings((prev) => ({ ...prev, payment_method_note: event.target.value }))
                  }
                />
              </>
            ) : (
              <>
                <p className="gbe-mini-value">{paymentMethodLabel}</p>
                {groupBuy.payment_method_note && (
                  <p className="gbe-hint">{groupBuy.payment_method_note}</p>
                )}
              </>
            )}
          </section>

          <section className="gbe-card gbe-mini-card">
            <h3 className="gbe-mini-title">
              {!isEditable("requires_second_payment") && <LockIcon />}
              是否需要二補
            </h3>
            {isEditable("requires_second_payment") ? (
              <select
                aria-label="是否需要二補"
                value={settings.requires_second_payment ? "true" : "false"}
                onChange={(event) =>
                  setSettings((prev) => ({
                    ...prev,
                    requires_second_payment: event.target.value === "true",
                  }))
                }
              >
                <option value="false">不需要二補</option>
                <option value="true">需要二補</option>
              </select>
            ) : (
              <p className="gbe-mini-value">
                {groupBuy.requires_second_payment ? "需要二補" : "不需要二補"}
              </p>
            )}
          </section>

          <section className="gbe-card gbe-mini-card">
            <h3 className="gbe-mini-title">
              {!isEditable("includes_full_gift") && <LockIcon />}
              是否包含滿額贈
            </h3>
            {isEditable("includes_full_gift") ? (
              <select
                aria-label="是否包含滿額贈"
                value={settings.includes_full_gift ? "true" : "false"}
                onChange={(event) =>
                  setSettings((prev) => ({
                    ...prev,
                    includes_full_gift: event.target.value === "true",
                  }))
                }
              >
                <option value="false">不含滿額贈</option>
                <option value="true">包含滿額贈</option>
              </select>
            ) : (
              <p className="gbe-mini-value">
                {groupBuy.includes_full_gift ? "包含滿額贈" : "不含滿額贈"}
              </p>
            )}
          </section>
        </div>

        <section className="gbe-card">
          <h2 className="gbe-card-title">
            開團規則
            {!isEditable("rules") && <LockIcon className="gbe-lock-mark" />}
          </h2>
          {isEditable("rules") ? (
            <textarea
              aria-label="開團規則"
              rows={6}
              value={settings.rules}
              onChange={(event) => setSettings((prev) => ({ ...prev, rules: event.target.value }))}
            />
          ) : (
            <ul className="gbe-rules">
              {ruleLines.map((line, index) => (
                <li key={index}>{line}</li>
              ))}
            </ul>
          )}
        </section>

        <div className="gbe-actions">
          {/* 團主資料沒有該平台時直接停用送出，不必等後端回 422 */}
          <Button
            type="submit"
            loading={saving}
            disabled={currentContactMissing}
            className="gbe-submit"
          >
            <SaveIcon />
            儲存變更
          </Button>
          <Link className="btn btn-secondary gbe-back" to="/group-leader/group-buys">
            <ArrowLeftIcon />
            返回我的開團
          </Link>
        </div>
      </form>

      <section className="gbe-card">
        <h2 className="gbe-card-title">已選擇商品</h2>
        <p className="helper-text" style={{ marginTop: 0 }}>
          單價不可修改；接單上限可調整，但不得低於已占用數量。
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>商品</th>
                <th>單價（新台幣）</th>
                <th>已訂購</th>
                <th>接單上限</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {groupBuy.products.map((item) => (
                <tr key={item.id}>
                  <td>
                    <span className="gbe-product">
                      <img
                        className="gbe-product-image"
                        src={resolveMediaUrl(item.product.primary_image_url)}
                        alt=""
                      />
                      <span>
                        {item.product.name}
                        {item.character_stock.length > 0 && (
                          <span className="gbe-character-stock">
                            {item.character_stock.map((stock) => (
                              <span key={stock.character_id}>
                                {stock.name}：{stock.occupied_quantity}／{stock.max_quantity}
                              </span>
                            ))}
                          </span>
                        )}
                      </span>
                    </span>
                  </td>
                  <td>{item.unit_price}</td>
                  <td>{item.occupied_quantity}</td>
                  <td>
                    <input
                      type="number"
                      min={item.occupied_quantity}
                      style={{ width: "5rem" }}
                      value={productMaxQuantities[item.id] ?? item.max_quantity}
                      onChange={(event) =>
                        setProductMaxQuantities((prev) => ({
                          ...prev,
                          [item.id]: event.target.value,
                        }))
                      }
                    />
                  </td>
                  <td>
                    <div className="group-buy-card-row" style={{ flexWrap: "nowrap" }}>
                      <Button variant="secondary" onClick={() => handleSaveMaxQuantity(item.id)}>
                        儲存
                      </Button>
                      {!groupBuy.has_orders && groupBuy.products.length > 1 && (
                        <Button variant="ghost" onClick={() => handleRemoveProduct(item.id)}>
                          移除
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!groupBuy.has_orders && newProducts.length > 0 && (
          <form onSubmit={handleAddProduct} className="gbe-add-product">
            <h3 className="gbe-mini-title">新增商品</h3>
            <div className="group-buy-card-row">
              <select
                value={newProductId}
                onChange={(event) => setNewProductId(event.target.value)}
                required
              >
                <option value="">選擇商品</option>
                {newProducts.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="單價"
                value={newUnitPrice}
                onChange={(event) => setNewUnitPrice(event.target.value)}
                required
                style={{ width: "6rem" }}
              />
              <input
                type="number"
                min="1"
                placeholder="接單上限"
                value={newMaxQuantity}
                onChange={(event) => setNewMaxQuantity(event.target.value)}
                required
                style={{ width: "6rem" }}
              />
              <Button type="submit">新增</Button>
            </div>
          </form>
        )}
      </section>

      {groupBuy.status === "open" && (
        <div className="group-buy-card-row" style={{ marginTop: "1.5rem" }}>
          <Button variant="danger" onClick={() => setConfirmClose(true)}>
            提前結單
          </Button>
        </div>
      )}

      {confirmClose && (
        <ConfirmModal
          title="提前結單"
          message="結單後將無法重新開啟，確定要提前結單嗎？"
          confirmLabel="確定結單"
          danger
          loading={closing}
          onCancel={() => setConfirmClose(false)}
          onConfirm={handleClose}
        />
      )}
    </>
  );
}
