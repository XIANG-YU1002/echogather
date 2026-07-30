import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getActivities } from "../../api/activities.js";
import { getAdminActivityDetail } from "../../api/adminActivities.js";
import {
  createAdminCharacter,
  deleteAdminCharacter,
  getCharacterSuggestions,
} from "../../api/adminCharacters.js";
import { createAdminProduct } from "../../api/adminProducts.js";
import { uploadImage } from "../../api/uploads.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ImageCropper from "../../components/common/ImageCropper.jsx";
import MediaImage from "../../components/common/MediaImage.jsx";
import Modal from "../../components/common/Modal.jsx";
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  PlusCircleIcon,
  TrashIcon,
  UploadIcon,
} from "../../components/common/icons.jsx";

/**
 * 商品批次新增（使用者 2026-07-30 要求：一次可建立多項，不必一項一項來回）。
 *
 * 與單項編輯頁分開成獨立頁面：編輯頁還要處理額外圖片的新增／排序／刪除，
 * 兩種模式塞在同一個元件會讓狀態難以理解。編輯仍走 ProductFormPage。
 *
 * 後端沒有批次建立端點，因此逐項呼叫 POST /admin/products。
 * 重點是部分失敗的處理：已成功的項目標記為完成且不再重送，
 * 失敗的保留在畫面上並顯示原因，讓管理員修正後只補送剩下的。
 */

const CURRENCIES = [
  { value: "TWD", label: "TWD 新台幣" },
  { value: "CNY", label: "CNY 人民幣" },
  { value: "JPY", label: "JPY 日圓" },
  { value: "KRW", label: "KRW 韓元" },
  { value: "USD", label: "USD 美金" },
];

let draftSeq = 0;

function createDraft() {
  draftSeq += 1;
  return {
    key: `draft-${draftSeq}`,
    name: "",
    officialPrice: "",
    primaryImageUrl: "",
    characters: [],
    status: "editing",
    error: null,
  };
}

export default function ProductBatchCreatePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [activities, setActivities] = useState([]);
  // 從活動建立流程帶進來的活動（見 ActivityFormPage 建立成功後的導向）
  const [activityId, setActivityId] = useState(searchParams.get("activity_id") ?? "");

  // 幣別是活動層級的設定：同一活動的商品必須用同一種幣別
  // （使用者 2026-07-30 規則，後端亦會驗證）。
  // 活動已有標價商品時鎖定為既有幣別，否則由這裡選一次、套用到本批全部商品。
  const [currency, setCurrency] = useState("TWD");
  const [lockedCurrency, setLockedCurrency] = useState(null);

  const [drafts, setDrafts] = useState([createDraft()]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  // 圖片：選好待裁切的檔案要記住是哪一項的
  const [pendingImage, setPendingImage] = useState(null);
  const [uploadingKey, setUploadingKey] = useState(null);
  const fileInputRef = useRef(null);
  const pickTargetRef = useRef(null);

  // 角色自動完成：整頁共用一組狀態，用 activeKey 記住是哪一項在輸入
  const [characterQuery, setCharacterQuery] = useState("");
  const [activeKey, setActiveKey] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  // 本次在這一頁新建的角色 id。只有這些才提供「刪除角色」，
  // 避免誤刪其他商品正在用的既有角色（後端也會擋，這是第一層防線）。
  const [createdIds, setCreatedIds] = useState(new Set());

  useEffect(() => {
    getActivities({ pageSize: 50 })
      .then((response) => setActivities(response.data))
      .catch(() => setActivities([]));
  }, []);

  // 選了活動就去問它現行的商品幣別；已有就鎖定，避免送出才被後端擋下來
  useEffect(() => {
    if (!activityId) {
      setLockedCurrency(null);
      return;
    }
    getAdminActivityDetail(activityId, token)
      .then((response) => {
        const existing = response.data.product_currency;
        setLockedCurrency(existing ?? null);
        if (existing) setCurrency(existing);
      })
      .catch(() => setLockedCurrency(null));
  }, [activityId, token]);

  useEffect(() => {
    if (!characterQuery.trim()) {
      setSuggestions([]);
      return;
    }
    getCharacterSuggestions(characterQuery.trim(), 10, token)
      .then((response) => setSuggestions(response.data))
      .catch(() => setSuggestions([]));
  }, [characterQuery, token]);

  function updateDraft(key, patch) {
    setDrafts((prev) =>
      prev.map((draft) => (draft.key === key ? { ...draft, ...patch } : draft)),
    );
  }

  function addDraft() {
    setDrafts((prev) => [...prev, createDraft()]);
  }

  function removeDraft(key) {
    setDrafts((prev) => (prev.length === 1 ? prev : prev.filter((d) => d.key !== key)));
  }

  function openFilePicker(key) {
    pickTargetRef.current = key;
    fileInputRef.current?.click();
  }

  function handleFilePick(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !pickTargetRef.current) return;
    setFormError(null);
    setPendingImage({ file, key: pickTargetRef.current });
  }

  async function handleCropConfirm(croppedFile) {
    const { key } = pendingImage;
    setUploadingKey(key);
    try {
      const response = await uploadImage(croppedFile, "product", token);
      updateDraft(key, { primaryImageUrl: response.data.url });
      setPendingImage(null);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "圖片上傳失敗，請稍後再試。");
    } finally {
      setUploadingKey(null);
    }
  }

  function addCharacter(key, character) {
    const draft = drafts.find((d) => d.key === key);
    if (!draft) return;
    if (draft.characters.some((c) => c.id === character.id)) return;
    updateDraft(key, { characters: [...draft.characters, character] });
    setCharacterQuery("");
    setSuggestions([]);
  }

  /**
   * 立即建立角色（使用者 2026-07-30 要求：不等商品送出）。
   * 建好的 id 記進 createdIds，這樣標籤上才知道要不要提供「刪除角色」。
   */
  async function createAndAddCharacter(key, name) {
    setFormError(null);
    try {
      const response = await createAdminCharacter(name, token);
      const created = { id: response.data.id, name: response.data.name };
      setCreatedIds((prev) => new Set(prev).add(created.id));
      addCharacter(key, created);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "新增角色失敗，請稍後再試。");
    }
  }

  /** 從這項商品移除角色關聯（角色本身留在資料庫）。 */
  function removeCharacter(key, character) {
    const draft = drafts.find((d) => d.key === key);
    if (!draft) return;
    updateDraft(key, {
      characters: draft.characters.filter((c) => c.id !== character.id),
    });
  }

  /**
   * 刪除角色本身（供打錯字時清掉）。只對本次新建的角色顯示入口；
   * 後端會擋下已有商品關聯的角色，因此不會誤刪正在使用中的角色。
   */
  async function deleteCharacter(key, character) {
    setFormError(null);
    try {
      await deleteAdminCharacter(character.id, token);
      setCreatedIds((prev) => {
        const next = new Set(prev);
        next.delete(character.id);
        return next;
      });
      // 這個角色可能已被加到多項商品上，全部一起移除
      setDrafts((prev) =>
        prev.map((draft) => ({
          ...draft,
          characters: draft.characters.filter((c) => c.id !== character.id),
        })),
      );
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "刪除角色失敗，請稍後再試。",
      );
    }
  }

  const pendingDrafts = drafts.filter((d) => d.status !== "done");
  const doneCount = drafts.length - pendingDrafts.length;

  async function handleSubmitAll(event) {
    event.preventDefault();
    setFormError(null);

    if (!activityId) {
      setFormError("請先選擇所屬活動。");
      return;
    }
    const incomplete = pendingDrafts.find((d) => !d.name.trim() || !d.primaryImageUrl);
    if (incomplete) {
      setFormError("每一項商品都需要填寫名稱並上傳主圖。");
      return;
    }

    setSaving(true);
    let failed = false;

    // 逐項送出（後端沒有批次端點）。用 for 而非 Promise.all：
    // 一次打十幾個建立請求容易踩到後端的角色去重與唯一性檢查，
    // 順序送出也讓失敗項的對應關係單純。
    for (const draft of pendingDrafts) {
      try {
        await createAdminProduct(
          {
            activity_id: activityId,
            name: draft.name.trim(),
            official_price: draft.officialPrice === "" ? null : draft.officialPrice,
            // 幣別統一取活動層級的設定
            official_currency: draft.officialPrice === "" ? null : currency,
            primary_image_url: draft.primaryImageUrl,
            // 角色在選擇時就已建立，這裡一律以 id 關聯
            characters: draft.characters.map((c) => ({ id: c.id })),
          },
          token,
        );
        updateDraft(draft.key, { status: "done", error: null });
      } catch (err) {
        failed = true;
        updateDraft(draft.key, {
          status: "error",
          error: err instanceof ApiError ? err.message : "建立失敗，請稍後再試。",
        });
      }
    }

    setSaving(false);

    if (failed) {
      setFormError("部分商品建立失敗，已成功的項目不會重複建立，請修正後再送出剩下的。");
    } else {
      navigate(`/admin/products?activity_id=${activityId}`, { replace: true });
    }
  }

  const activeActivity = activities.find((a) => a.id === activityId);

  return (
    <div className="admin-page">
      <div className="page-header af-header">
        <div>
          <h1>商品新增</h1>
          <Breadcrumb
            items={[{ label: "商品管理", to: "/admin/products" }, { label: "商品新增" }]}
          />
        </div>
        <Link className="btn btn-secondary" to="/admin/products">
          <ArrowLeftIcon />
          返回商品列表
        </Link>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: "none" }}
        onChange={handleFilePick}
      />

      <form className="pb-form" onSubmit={handleSubmitAll}>
        <div className="admin-panel pb-activity">
          <div className="form-field">
            <label htmlFor="pb-activity">
              所屬活動<span className="required-mark">*</span>
            </label>
            <select
              id="pb-activity"
              value={activityId}
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
            <span className="helper-text">
              以下所有商品都會建立在這個活動底下{activeActivity ? `：${activeActivity.name}` : ""}。
            </span>
          </div>

          {/* 幣別是活動層級的設定，不放在每項商品裡：同一活動必須一致 */}
          <div className="form-field">
            <label htmlFor="pb-currency">官方定價幣別</label>
            <select
              id="pb-currency"
              value={currency}
              disabled={Boolean(lockedCurrency)}
              onChange={(event) => setCurrency(event.target.value)}
            >
              {CURRENCIES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <span className="helper-text">
              {lockedCurrency
                ? `此活動已有商品使用 ${lockedCurrency}，同一活動的幣別必須一致，因此無法變更。`
                : "同一活動的商品幣別必須一致，這裡選定後會套用到本批所有商品。"}
            </span>
          </div>
        </div>

        {drafts.map((draft, index) => {
          const isDone = draft.status === "done";
          return (
            <div
              key={draft.key}
              className={`admin-panel pb-item${isDone ? " is-done" : ""}${
                draft.status === "error" ? " is-error" : ""
              }`}
            >
              <div className="pb-item-head">
                <h2>
                  商品 {index + 1}
                  {isDone && (
                    <span className="pb-done-tag">
                      <CheckCircleIcon />
                      已建立
                    </span>
                  )}
                </h2>
                {!isDone && drafts.length > 1 && (
                  <button
                    type="button"
                    className="pb-remove-btn"
                    onClick={() => removeDraft(draft.key)}
                  >
                    <TrashIcon />
                    移除
                  </button>
                )}
              </div>

              {draft.error && <Alert type="error">{draft.error}</Alert>}

              {/* 已建立的項目不再提供編輯：它已經是資料庫裡的商品，
                  要改就到商品管理頁編輯，避免這裡的欄位與實際資料不一致 */}
              {isDone ? (
                <p className="pb-done-note">
                  {draft.name} 已建立完成。若要調整內容，請至商品管理頁編輯。
                </p>
              ) : (
                <div className="pb-item-body">
                  <div className="pb-image-col">
                    {draft.primaryImageUrl ? (
                      <MediaImage className="pb-image" src={draft.primaryImageUrl} alt="" />
                    ) : (
                      <div className="pb-image-empty">尚未上傳主圖</div>
                    )}
                    <Button
                      type="button"
                      variant="secondary"
                      loading={uploadingKey === draft.key}
                      onClick={() => openFilePicker(draft.key)}
                    >
                      <UploadIcon />
                      {draft.primaryImageUrl ? "更換主圖" : "上傳主圖"}
                    </Button>
                  </div>

                  <div className="pb-fields-col">
                    <div className="form-field">
                      <label htmlFor={`${draft.key}-name`}>
                        商品名稱<span className="required-mark">*</span>
                      </label>
                      <input
                        id={`${draft.key}-name`}
                        value={draft.name}
                        placeholder="請輸入商品名稱"
                        onChange={(event) => updateDraft(draft.key, { name: event.target.value })}
                      />
                    </div>

                    <div className="form-field">
                      <label htmlFor={`${draft.key}-price`}>
                        官方定價（選填，{currency}）
                      </label>
                      <input
                        id={`${draft.key}-price`}
                        type="number"
                        min="0"
                        step="1"
                        placeholder="例如：850"
                        value={draft.officialPrice}
                        onChange={(event) =>
                          updateDraft(draft.key, { officialPrice: event.target.value })
                        }
                      />
                    </div>

                    <div className="form-field">
                      <label htmlFor={`${draft.key}-character`}>關聯角色（選填）</label>
                      {draft.characters.length > 0 && (
                        <div className="pb-character-tags">
                          {draft.characters.map((character) => (
                            <span className="char-tag" key={character.id}>
                              {character.name}
                              {/* × 只從這項商品移除關聯 */}
                              <button
                                type="button"
                                aria-label={`從此商品移除 ${character.name}`}
                                title="從此商品移除"
                                onClick={() => removeCharacter(draft.key, character)}
                              >
                                ×
                              </button>
                              {/* 本次新建的角色才給「刪除角色」，用來清掉打錯字的標籤 */}
                              {createdIds.has(character.id) && (
                                <button
                                  type="button"
                                  className="pb-tag-delete"
                                  aria-label={`刪除角色 ${character.name}`}
                                  title="從資料庫刪除這個角色"
                                  onClick={() => deleteCharacter(draft.key, character)}
                                >
                                  <TrashIcon />
                                </button>
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                      <input
                        id={`${draft.key}-character`}
                        value={activeKey === draft.key ? characterQuery : ""}
                        placeholder="輸入角色名稱搜尋或新增"
                        onFocus={() => {
                          setActiveKey(draft.key);
                          setCharacterQuery("");
                        }}
                        onChange={(event) => {
                          setActiveKey(draft.key);
                          setCharacterQuery(event.target.value);
                        }}
                      />
                      {activeKey === draft.key && characterQuery.trim() && (
                        <div className="pb-suggestions">
                          {suggestions.map((suggestion) => (
                            <button
                              type="button"
                              key={suggestion.id}
                              onClick={() =>
                                addCharacter(draft.key, {
                                  id: suggestion.id,
                                  name: suggestion.name,
                                })
                              }
                            >
                              {suggestion.name}
                            </button>
                          ))}
                          {/* 沒有完全同名的建議時才提供新增，避免建出重複角色 */}
                          {!suggestions.some(
                            (s) => s.name.toLowerCase() === characterQuery.trim().toLowerCase(),
                          ) && (
                            <button
                              type="button"
                              className="pb-suggestion-new"
                              onClick={() =>
                                createAndAddCharacter(draft.key, characterQuery.trim())
                              }
                            >
                              新增角色「{characterQuery.trim()}」（立即建立）
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        <button type="button" className="pb-add-btn" onClick={addDraft}>
          <PlusCircleIcon />
          再新增一項商品
        </button>

        {formError && <Alert type="error">{formError}</Alert>}

        <div className="pb-actions">
          {doneCount > 0 && (
            <span className="pb-progress">已建立 {doneCount} 項</span>
          )}
          <Link className="btn btn-secondary" to="/admin/products">
            取消
          </Link>
          <Button type="submit" loading={saving} disabled={pendingDrafts.length === 0}>
            {pendingDrafts.length > 1
              ? `建立 ${pendingDrafts.length} 項商品`
              : "建立商品"}
          </Button>
        </div>
      </form>

      {pendingImage && (
        <Modal title="裁切商品主圖" onClose={() => setPendingImage(null)}>
          {/* 商品圖不鎖比例，也可以直接用原圖（使用者 2026-07-30 要求） */}
          <ImageCropper
            file={pendingImage.file}
            aspectRatio={null}
            allowOriginal
            loading={uploadingKey === pendingImage.key}
            confirmLabel="套用裁切並上傳"
            onCancel={() => setPendingImage(null)}
            onPickAnother={() => openFilePicker(pendingImage.key)}
            onConfirm={handleCropConfirm}
          />
        </Modal>
      )}
    </div>
  );
}
