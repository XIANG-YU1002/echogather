import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createAdminActivity,
  endAdminActivity,
  getAdminActivityDetail,
  reopenAdminActivity,
  updateAdminActivity,
} from "../../api/adminActivities.js";
import { uploadImage } from "../../api/uploads.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../api/client.js";
import MediaImage from "../../components/common/MediaImage.jsx";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import FormField from "../../components/common/FormField.jsx";
import ImageCropper from "../../components/common/ImageCropper.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import { ArrowLeftIcon, SaveIcon, UploadIcon } from "../../components/common/icons.jsx";

const NAME_MAX_LENGTH = 50;
const DESCRIPTION_MAX_LENGTH = 500;

export default function ActivityFormPage() {
  const { activityId } = useParams();
  const isEdit = Boolean(activityId);
  const { token } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(isEdit);
  const [error, setError] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [hasFullGift, setHasFullGift] = useState(false);
  // 活動狀態沒有放在 UpdateActivityRequest 裡，是由 /end 與 /reopen 兩支專用端點操作，
  // 因此這裡記住載入時的原始值，只有真的變動才呼叫對應端點。
  const [status, setStatus] = useState("open");
  const [originalStatus, setOriginalStatus] = useState("open");
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  // 選好但還沒裁切的檔案；有值時顯示裁切器
  const [pendingFile, setPendingFile] = useState(null);
  const fileInputRef = useRef(null);

  function load() {
    setError(false);
    setLoading(true);
    getAdminActivityDetail(activityId, token)
      .then((response) => {
        const data = response.data;
        setName(data.name);
        setDescription(data.description ?? "");
        setImageUrl(data.image_url);
        setHasFullGift(data.has_full_gift);
        setStatus(data.status);
        setOriginalStatus(data.status);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (isEdit) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityId]);

  function handleFilePick(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setSubmitError(null);
    setPendingFile(file);
  }

  /** 裁切完成後才真正上傳，因此存到 Storage 的已是裁切後的圖。 */
  async function handleCropConfirm(croppedFile) {
    setUploading(true);
    try {
      const response = await uploadImage(croppedFile, "activity", token);
      setImageUrl(response.data.url);
      setPendingFile(null);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "圖片上傳失敗，請稍後再試。");
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSubmitError(null);
    const payload = {
      name,
      description: description || null,
      image_url: imageUrl,
      has_full_gift: hasFullGift,
    };
    try {
      if (isEdit) {
        await updateAdminActivity(activityId, payload, token);
        // 狀態改變才呼叫，避免對沒變動的活動送出無意義的結束／重新開啟
        if (status !== originalStatus) {
          if (status === "ended") {
            await endAdminActivity(activityId, token);
          } else {
            await reopenAdminActivity(activityId, token);
          }
        }
        navigate("/admin/activities", { replace: true });
      } else {
        // 新活動建立後直接進「建立商品」並帶上活動（使用者 2026-07-30 要求）：
        // 剛開好的活動一定還沒有商品，回列表只是多一次點擊。
        const response = await createAdminActivity(payload, token);
        navigate(`/admin/products/new?activity_id=${response.data.id}`, { replace: true });
      }
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
    <div className="admin-page">
      <div className="page-header af-header">
        <div>
          <h1>{isEdit ? "活動編輯" : "活動新增"}</h1>
          <Breadcrumb
            items={[
              { label: "活動管理", to: "/admin/activities" },
              { label: isEdit ? "活動編輯" : "活動新增" },
            ]}
          />
        </div>
        <Link className="btn btn-secondary" to="/admin/activities">
          <ArrowLeftIcon />
          返回活動列表
        </Link>
      </div>

      <form className="admin-panel af-form" onSubmit={handleSubmit}>
        <div className="form-field af-counted">
          <label htmlFor="activity-name">
            活動名稱<span className="required-mark">*</span>
          </label>
          <input
            id="activity-name"
            value={name}
            maxLength={NAME_MAX_LENGTH}
            placeholder="請輸入活動名稱"
            onChange={(event) => setName(event.target.value)}
            required
          />
          <span className="af-count">
            {name.length} / {NAME_MAX_LENGTH}
          </span>
        </div>

        <div className="form-field af-counted">
          <label htmlFor="activity-description">活動說明</label>
          <textarea
            id="activity-description"
            rows={4}
            maxLength={DESCRIPTION_MAX_LENGTH}
            placeholder="說明本次活動的內容、商品範圍與注意事項。"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <span className="af-count">
            {description.length} / {DESCRIPTION_MAX_LENGTH}
          </span>
        </div>

        <div className="form-field">
          <label>
            活動封面圖片<span className="required-mark">*</span>
          </label>
          <p className="af-image-hint">
            建議封面比例為 16:9，支援 JPG、PNG、WebP，可自由拖曳、縮放與選擇裁切範圍。
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style={{ display: "none" }}
            onChange={handleFilePick}
          />

          {pendingFile ? (
            <ImageCropper
              file={pendingFile}
              aspectRatio={16 / 9}
              aspectLabel="16:9"
              loading={uploading}
              confirmLabel="套用裁切並上傳"
              onCancel={() => setPendingFile(null)}
              onPickAnother={() => fileInputRef.current?.click()}
              onConfirm={handleCropConfirm}
            />
          ) : (
            <div className="af-image-preview">
              {imageUrl ? (
                <MediaImage className="af-image" src={imageUrl} alt="" />
              ) : (
                <div className="af-image-empty">尚未上傳封面圖片</div>
              )}
              <Button
                type="button"
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadIcon />
                {imageUrl ? "更換圖片" : "上傳圖片"}
              </Button>
            </div>
          )}
        </div>

        <div className="af-row">
          <div className="form-field">
            <span className="gbe-label">是否有滿贈</span>
            {/* 選項橫向排列（依參考圖 33）。必須包一層：.form-field 是
                flex-direction: column，直接放 label 會被排成直的。 */}
            <div className="af-radio-row">
              <label className="af-radio">
                <input
                  type="radio"
                  name="af-gift"
                  checked={hasFullGift}
                  onChange={() => setHasFullGift(true)}
                />
                <span>有</span>
              </label>
              <label className="af-radio">
                <input
                  type="radio"
                  name="af-gift"
                  checked={!hasFullGift}
                  onChange={() => setHasFullGift(false)}
                />
                <span>無</span>
              </label>
            </div>
          </div>

          {/* 狀態只在編輯時出現：新活動一律是進行中，
              且狀態是靠 /end 與 /reopen 端點變更（見 handleSubmit） */}
          {isEdit && (
            <div className="form-field">
              <span className="gbe-label">狀態</span>
              <div className="af-radio-row">
                <label className="af-radio">
                  <input
                    type="radio"
                    name="af-status"
                    checked={status === "open"}
                    onChange={() => setStatus("open")}
                  />
                  <span>進行中</span>
                </label>
                <label className="af-radio">
                  <input
                    type="radio"
                    name="af-status"
                    checked={status === "ended"}
                    onChange={() => setStatus("ended")}
                  />
                  <span>已結束</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {submitError && <Alert type="error">{submitError}</Alert>}

        {/* 參考圖另有「儲存草稿」，但後端沒有草稿狀態（活動只有進行中／已結束），
            依使用者 2026-07-30 裁決不實作 */}
        <div className="af-actions">
          <Link className="btn btn-secondary" to="/admin/activities">
            取消
          </Link>
          <Button type="submit" loading={saving} disabled={!imageUrl}>
            <SaveIcon />
            {isEdit ? "儲存活動" : "建立活動"}
          </Button>
        </div>
      </form>
    </div>
  );
}
