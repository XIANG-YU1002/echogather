import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getActivities } from "../../api/activities.js";
import {
  createAdminCharacter,
  deleteAdminCharacter,
  getCharacterSuggestions,
} from "../../api/adminCharacters.js";
import {
  addAdminProductImage,
  deleteAdminProductImage,
  getAdminProductDetail,
  reorderAdminProductImages,
  updateAdminProduct,
} from "../../api/adminProducts.js";
import { uploadImage } from "../../api/uploads.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import FormField from "../../components/common/FormField.jsx";
import ImageCropper from "../../components/common/ImageCropper.jsx";
import Modal from "../../components/common/Modal.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import { TrashIcon } from "../../components/common/icons.jsx";

export default function ProductFormPage() {
  const { productId } = useParams();
  // 這一頁只服務編輯（路由是 /admin/products/:productId）。
  // 新增改走 ProductBatchCreatePage，可一次建立多項（使用者 2026-07-30 需求）。
  // isEdit 保留是因為額外圖片等區塊都以它為條件，且語意仍然清楚。
  const isEdit = Boolean(productId);
  const { token } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(isEdit);
  const [error, setError] = useState(false);

  const [activities, setActivities] = useState([]);
  const [activityId, setActivityId] = useState("");
  const [name, setName] = useState("");
  const [officialPrice, setOfficialPrice] = useState("");
  const [officialCurrency, setOfficialCurrency] = useState("TWD");
  // 同活動其他商品已在使用的幣別（後端排除自己算出）；有值代表不可更改
  const [lockedCurrency, setLockedCurrency] = useState(null);
  const [primaryImageUrl, setPrimaryImageUrl] = useState("");
  const [selectedCharacters, setSelectedCharacters] = useState([]);
  const [characterQuery, setCharacterQuery] = useState("");
  const [characterSuggestions, setCharacterSuggestions] = useState([]);
  // 本次在這一頁新建的角色 id；只有這些提供「刪除角色」，避免誤刪既有角色
  const [createdIds, setCreatedIds] = useState(new Set());

  const [extraImages, setExtraImages] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  // 選好但還沒裁切的圖：{ file, target: "primary" | "extra" }
  const [pendingImage, setPendingImage] = useState(null);
  const primaryFileInputRef = useRef(null);
  const extraFileInputRef = useRef(null);

  useEffect(() => {
    getActivities({ pageSize: 50 }).then((response) => setActivities(response.data));
  }, []);

  function load() {
    setError(false);
    setLoading(true);
    getAdminProductDetail(productId, token)
      .then((response) => {
        const data = response.data;
        setActivityId(data.activity.id);
        setName(data.name);
        setOfficialPrice(data.official_price ?? "");
        // 同活動其他商品已有幣別時，這裡就鎖定，不讓改到送出才被後端擋
        setLockedCurrency(data.activity_currency ?? null);
        setOfficialCurrency(data.official_currency ?? data.activity_currency ?? "TWD");
        setPrimaryImageUrl(data.primary_image_url);
        setSelectedCharacters(data.characters.map((c) => ({ id: c.id, name: c.name })));
        setExtraImages(data.images);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (isEdit) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  useEffect(() => {
    if (!characterQuery.trim()) {
      setCharacterSuggestions([]);
      return;
    }
    getCharacterSuggestions(characterQuery.trim(), 10, token)
      .then((response) => setCharacterSuggestions(response.data))
      .catch(() => setCharacterSuggestions([]));
  }, [characterQuery, token]);

  function addCharacter(character) {
    if (selectedCharacters.some((c) => c.id === character.id)) return;
    setSelectedCharacters((prev) => [...prev, character]);
    setCharacterQuery("");
    setCharacterSuggestions([]);
  }

  /**
   * 立即建立角色（使用者 2026-07-30 要求：不等商品送出）。
   * 記進 createdIds，標籤才知道要不要提供「刪除角色」。
   */
  async function createAndAddCharacter(name) {
    setSubmitError(null);
    try {
      const response = await createAdminCharacter(name, token);
      const created = { id: response.data.id, name: response.data.name };
      setCreatedIds((prev) => new Set(prev).add(created.id));
      addCharacter(created);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "新增角色失敗，請稍後再試。");
    }
  }

  /** 從這個商品移除角色關聯（角色本身留在資料庫）。 */
  function removeCharacter(character) {
    setSelectedCharacters((prev) => prev.filter((c) => c.id !== character.id));
  }

  /**
   * 刪除角色本身（供打錯字時清掉）。只對本次新建的角色顯示入口；
   * 後端會擋下已有商品關聯的角色，不會誤刪使用中的角色。
   */
  async function deleteCharacter(character) {
    setSubmitError(null);
    try {
      await deleteAdminCharacter(character.id, token);
      setCreatedIds((prev) => {
        const next = new Set(prev);
        next.delete(character.id);
        return next;
      });
      setSelectedCharacters((prev) => prev.filter((c) => c.id !== character.id));
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "刪除角色失敗，請稍後再試。");
    }
  }

  const hasExactSuggestionMatch = characterSuggestions.some(
    (suggestion) => suggestion.name.toLowerCase() === characterQuery.trim().toLowerCase(),
  );

  /**
   * 圖片一律先裁切再上傳（使用者 2026-07-30 要求）。
   * pendingImage.target 記住這張是要當主圖還是額外圖片，兩者共用同一個裁切器。
   */
  function handleImagePick(event, target) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setSubmitError(null);
    setPendingImage({ file, target });
  }

  async function handleCropConfirm(croppedFile) {
    setUploading(true);
    try {
      const uploadResponse = await uploadImage(croppedFile, "product", token);
      if (pendingImage.target === "primary") {
        setPrimaryImageUrl(uploadResponse.data.url);
      } else {
        const addResponse = await addAdminProductImage(
          productId,
          uploadResponse.data.url,
          token,
        );
        setExtraImages(addResponse.data.images);
      }
      setPendingImage(null);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "圖片上傳失敗，請稍後再試。");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteExtraImage(imageId) {
    try {
      const response = await deleteAdminProductImage(productId, imageId, token);
      setExtraImages(response.data.images);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "刪除圖片時發生錯誤。");
    }
  }

  async function handleMoveImage(index, direction) {
    const newOrder = [...extraImages];
    const target = index + direction;
    if (target < 0 || target >= newOrder.length) return;
    [newOrder[index], newOrder[target]] = [newOrder[target], newOrder[index]];
    setExtraImages(newOrder);
    try {
      const response = await reorderAdminProductImages(
        productId,
        newOrder.map((image) => image.id),
        token,
      );
      setExtraImages(response.data.images);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "調整順序時發生錯誤。");
      load();
    }
  }

  function buildCharacterPayload() {
    // 角色在選擇時就已建立（見 createAndAddCharacter），一律以 id 關聯
    return selectedCharacters.map((c) => ({ id: c.id }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSubmitError(null);
    try {
      const payload = {
        name,
        official_price: officialPrice === "" ? null : officialPrice,
        official_currency: officialPrice === "" ? null : officialCurrency,
        primary_image_url: primaryImageUrl,
        characters: buildCharacterPayload(),
      };
      await updateAdminProduct(productId, payload, token);
      navigate("/admin/products", { replace: true });
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "儲存時發生錯誤，請稍後再試。");
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (loading) {
    return <PageLoader />;
  }

  return (
    <>
      <div className="page-header">
        <h1>商品編輯</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-two-col">
          <FormField label="活動選擇" htmlFor="product-activity" required>
            <select
              id="product-activity"
              value={activityId}
              disabled={isEdit}
              onChange={(event) => setActivityId(event.target.value)}
              required
            >
              <option value="">請選擇活動</option>
              {activities.map((activity) => (
                <option key={activity.id} value={activity.id}>
                  {activity.name}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="商品名稱" htmlFor="product-name" required>
            <input id="product-name" value={name} onChange={(event) => setName(event.target.value)} required />
          </FormField>
        </div>

        <FormField label="官方價格（選填）" htmlFor="product-price">
          <div className="price-currency-row">
            <input
              id="product-price"
              type="number"
              min="0"
              step="0.01"
              placeholder="請輸入金額"
              value={officialPrice}
              onChange={(event) => setOfficialPrice(event.target.value)}
            />
            <select
              className="price-currency-select"
              value={officialCurrency}
              onChange={(event) => setOfficialCurrency(event.target.value)}
              // 同活動已有其他標價商品時唯讀：幣別必須一致，
              // 讓它可改再到送出才報錯是白費工
              disabled={officialPrice === "" || Boolean(lockedCurrency)}
              aria-label="幣別"
            >
              <option value="TWD">TWD 新台幣</option>
              <option value="CNY">CNY 人民幣</option>
              <option value="JPY">JPY 日圓</option>
              <option value="KRW">KRW 韓元</option>
              <option value="USD">USD 美金</option>
            </select>
          </div>
          <p className="helper-text">
            {lockedCurrency
              ? `選填官方定價。此活動的商品幣別為 ${lockedCurrency}，同一活動必須一致，因此無法更改。`
              : "選填官方定價；填入金額後可選擇幣別。同一活動的商品幣別必須一致。"}
          </p>
        </FormField>

        <FormField label="主圖" htmlFor="product-primary-image" required>
          {/* contain 而非 cover：商品圖是自由比例，裁切預覽會讓人誤以為圖被裁掉 */}
          {primaryImageUrl && (
            <MediaImage
              src={primaryImageUrl}
              alt=""
              className="pf-product-preview"
            />
          )}
          <input
            ref={primaryFileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style={{ display: "none" }}
            onChange={(event) => handleImagePick(event, "primary")}
          />
          <Button type="button" variant="secondary" loading={uploading} onClick={() => primaryFileInputRef.current?.click()}>
            {primaryImageUrl ? "更換主圖" : "上傳主圖"}
          </Button>
        </FormField>

        {isEdit && (
          <FormField label="額外圖片" htmlFor="product-extra-images">
            <div className="group-buy-card-row">
              {extraImages.map((image, index) => (
                <div key={image.id} style={{ position: "relative" }}>
                  <MediaImage
                    src={image.image_url}
                    alt=""
                    style={{ width: "5rem", height: "5rem", objectFit: "cover", borderRadius: "var(--radius)" }}
                  />
                  <div className="group-buy-card-row" style={{ marginTop: "0.25rem" }}>
                    <button type="button" className="btn btn-ghost" disabled={index === 0} onClick={() => handleMoveImage(index, -1)}>
                      ↑
                    </button>
                    <button type="button" className="btn btn-ghost" disabled={index === extraImages.length - 1} onClick={() => handleMoveImage(index, 1)}>
                      ↓
                    </button>
                    <button type="button" className="btn btn-ghost" onClick={() => handleDeleteExtraImage(image.id)}>
                      刪除
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <input
              ref={extraFileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              style={{ display: "none" }}
              onChange={(event) => handleImagePick(event, "extra")}
            />
            <Button type="button" variant="secondary" loading={uploading} onClick={() => extraFileInputRef.current?.click()}>
              + 上傳圖片
            </Button>
          </FormField>
        )}

        <FormField label="關聯角色" htmlFor="product-character-search">
          <div className="group-buy-card-row" style={{ marginBottom: "0.5rem" }}>
            {selectedCharacters.map((character) => (
              <span key={character.id} className="status-badge status-badge-info">
                {character.name}
                {/* ✕ 只從這個商品移除關聯 */}
                <button
                  type="button"
                  aria-label={`從此商品移除 ${character.name}`}
                  title="從此商品移除"
                  onClick={() => removeCharacter(character)}
                  style={{ marginLeft: "0.35rem", background: "none", border: "none", cursor: "pointer" }}
                >
                  ✕
                </button>
                {/* 本次新建的角色才給「刪除角色」，用來清掉打錯字的標籤 */}
                {createdIds.has(character.id) && (
                  <button
                    type="button"
                    className="pb-tag-delete"
                    aria-label={`刪除角色 ${character.name}`}
                    title="從資料庫刪除這個角色"
                    onClick={() => deleteCharacter(character)}
                    style={{ marginLeft: "0.2rem", background: "none", border: "none", cursor: "pointer" }}
                  >
                    <TrashIcon />
                  </button>
                )}
              </span>
            ))}
          </div>
          <input
            id="product-character-search"
            placeholder="搜尋或新增角色"
            value={characterQuery}
            onChange={(event) => setCharacterQuery(event.target.value)}
          />
          {characterQuery.trim() && (
            <div className="group-buy-card" style={{ marginTop: "0.4rem" }}>
              {characterSuggestions.map((suggestion) => (
                <div key={suggestion.id}>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => addCharacter({ id: suggestion.id, name: suggestion.name })}
                  >
                    {suggestion.name}（關聯商品 {suggestion.related_product_count} 項）
                  </button>
                </div>
              ))}
              {!hasExactSuggestionMatch && (
                <button
                  type="button"
                  className="btn btn-link"
                  onClick={() => createAndAddCharacter(characterQuery.trim())}
                >
                  找不到想要的角色？新增角色「{characterQuery.trim()}」（立即建立）
                </button>
              )}
            </div>
          )}
        </FormField>

        {submitError && <Alert type="error">{submitError}</Alert>}

        <Button type="submit" loading={saving} disabled={!primaryImageUrl || !activityId}>
          儲存商品
        </Button>
      </form>

      {pendingImage && (
        <Modal
          title={pendingImage.target === "primary" ? "裁切商品主圖" : "裁切商品圖片"}
          onClose={() => setPendingImage(null)}
        >
          {/* 商品圖不鎖比例，也可以直接用原圖（使用者 2026-07-30 要求） */}
          <ImageCropper
            file={pendingImage.file}
            aspectRatio={null}
            allowOriginal
            loading={uploading}
            confirmLabel="套用裁切並上傳"
            onCancel={() => setPendingImage(null)}
            onPickAnother={() =>
              (pendingImage.target === "primary"
                ? primaryFileInputRef
                : extraFileInputRef
              ).current?.click()
            }
            onConfirm={handleCropConfirm}
          />
        </Modal>
      )}
    </>
  );
}
