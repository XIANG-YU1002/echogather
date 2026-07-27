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
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ConfirmModal from "../../components/common/ConfirmModal.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import FormField from "../../components/common/FormField.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import StatusBadge from "../../components/common/StatusBadge.jsx";

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

  function isEditable(field) {
    return groupBuy?.editable_fields.includes(field);
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

  return (
    <>
      <div className="group-buy-card-row">
        <div>
          <h1>開團管理</h1>
          <StatusBadge domain="groupBuyEffective" value={groupBuy.status === "open" ? "open" : "closed"} />
        </div>
        <Link className="btn btn-secondary" to="/group-leader/group-buys">
          返回我的開團
        </Link>
      </div>

      <p className="helper-text">
        {groupBuy.activity.name} — {groupBuy.products.map((item) => item.product.name).join("、")}
      </p>

      {groupBuy.has_orders && (
        <Alert type="info">已有訂單，部分欄位已鎖定無法修改。僅可調整收單日期、聯絡方式與商品接單上限。</Alert>
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

      <div className="two-col-section">
        <div className="section">
          <h2 className="section-title">商品管理</h2>
          <p className="helper-text">可調整接單上限，已鎖定的欄位無法修改。</p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>商品</th>
                  <th>團購單價</th>
                  <th>已下單數量</th>
                  <th>接單上限</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {groupBuy.products.map((item) => (
                  <tr key={item.id}>
                    <td>{item.product.name}</td>
                    <td>NT$ {item.unit_price}</td>
                    <td>{item.max_quantity - item.available_quantity}</td>
                    <td>
                      <input
                        type="number"
                        min={item.max_quantity - item.available_quantity}
                        style={{ width: "5rem" }}
                        value={productMaxQuantities[item.id] ?? item.max_quantity}
                        onChange={(event) =>
                          setProductMaxQuantities((prev) => ({ ...prev, [item.id]: event.target.value }))
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
            <form onSubmit={handleAddProduct} className="group-buy-card" style={{ marginTop: "1rem" }}>
              <h3 style={{ marginTop: 0 }}>新增商品</h3>
              <div className="group-buy-card-row">
                <select value={newProductId} onChange={(event) => setNewProductId(event.target.value)} required>
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
        </div>

        <form className="section" onSubmit={handleSaveSettings}>
          <h2 className="section-title">開團設定</h2>

          <FormField label="付款方式" htmlFor="edit-payment-method">
            <select
              id="edit-payment-method"
              value={settings.payment_method}
              disabled={!isEditable("payment_method")}
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
          </FormField>

          <FormField
            label="付款方式備註（選填）"
            htmlFor="edit-payment-method-note"
            helperText="可補充付款細節，例如：團費確認後再私訊告知匯款帳號、取貨地點與時間、可接受的分期方式等。不填則不會顯示。"
          >
            <input
              id="edit-payment-method-note"
              value={settings.payment_method_note}
              disabled={!isEditable("payment_method_note")}
              placeholder="例如：團費確認後再私訊告知匯款帳號"
              onChange={(event) =>
                setSettings((prev) => ({ ...prev, payment_method_note: event.target.value }))
              }
            />
          </FormField>

          <FormField label="是否二補" htmlFor="edit-second-payment">
            <select
              id="edit-second-payment"
              value={settings.requires_second_payment ? "true" : "false"}
              disabled={!isEditable("requires_second_payment")}
              onChange={(event) =>
                setSettings((prev) => ({ ...prev, requires_second_payment: event.target.value === "true" }))
              }
            >
              <option value="false">否</option>
              <option value="true">是</option>
            </select>
          </FormField>

          <FormField label="是否含滿贈" htmlFor="edit-full-gift">
            <select
              id="edit-full-gift"
              value={settings.includes_full_gift ? "true" : "false"}
              disabled={!isEditable("includes_full_gift")}
              onChange={(event) =>
                setSettings((prev) => ({ ...prev, includes_full_gift: event.target.value === "true" }))
              }
            >
              <option value="false">否</option>
              <option value="true">是</option>
            </select>
          </FormField>

          <FormField label="收單日期" htmlFor="edit-deadline">
            <input
              id="edit-deadline"
              type="datetime-local"
              value={settings.deadline_at}
              disabled={!isEditable("deadline_at")}
              onChange={(event) => setSettings((prev) => ({ ...prev, deadline_at: event.target.value }))}
            />
          </FormField>

          <FormField label="主要聯絡方式" htmlFor="edit-contact-platform">
            <select
              id="edit-contact-platform"
              value={settings.contact_platform}
              disabled={!isEditable("contact_platform")}
              onChange={(event) => setSettings((prev) => ({ ...prev, contact_platform: event.target.value }))}
            >
              {CONTACT_PLATFORMS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="聯絡資料" htmlFor="edit-contact-value">
            <input
              id="edit-contact-value"
              value={settings.contact_value}
              disabled={!isEditable("contact_value")}
              onChange={(event) => setSettings((prev) => ({ ...prev, contact_value: event.target.value }))}
            />
          </FormField>

          <FormField label="團規" htmlFor="edit-rules">
            <textarea
              id="edit-rules"
              rows={6}
              value={settings.rules}
              disabled={!isEditable("rules")}
              onChange={(event) => setSettings((prev) => ({ ...prev, rules: event.target.value }))}
            />
          </FormField>

          <Button type="submit" fullWidth loading={saving}>
            儲存變更
          </Button>
        </form>
      </div>

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
