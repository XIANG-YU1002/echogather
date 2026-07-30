import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { getMyProfile, updateMyContacts, updateMyProfile } from "../../api/users.js";
import { uploadImage } from "../../api/uploads.js";
import { ApiError, resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Alert from "../../components/common/Alert.jsx";
import Breadcrumb from "../../components/common/Breadcrumb.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import ImageCropper from "../../components/common/ImageCropper.jsx";
import Modal from "../../components/common/Modal.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  CameraIcon,
  DiscordIcon,
  FacebookIcon,
  LineIcon,
  SaveIcon,
  UploadIcon,
} from "../../components/common/icons.jsx";

const CONTACT_FIELDS = [
  { key: "facebook", label: "Facebook", icon: FacebookIcon, placeholder: "請輸入 Facebook 連結" },
  { key: "discord", label: "Discord", icon: DiscordIcon, placeholder: "username#1234" },
  { key: "line", label: "LINE", icon: LineIcon, placeholder: "@your_line_id" },
];

/** 後端同一欄位可能回多筆訊息，全部逐行列出。 */
function FieldError({ error }) {
  if (!error) return null;
  const messages = Array.isArray(error) ? error : [error];
  return (
    <span className="auth-error">
      {messages.map((message) => (
        <span key={message} className="auth-error-line">
          {message}
        </span>
      ))}
    </span>
  );
}

export default function ProfilePage() {
  const { token, refreshSession } = useAuth();
  const location = useLocation();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(false);

  const [nickname, setNickname] = useState("");
  const [contacts, setContacts] = useState({ facebook: "", discord: "", line: "" });

  const [avatarUrl, setAvatarUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  // 選好但還沒裁切的頭像檔；有值時彈出裁切燈窗
  const [pendingAvatar, setPendingAvatar] = useState(null);
  const fileInputRef = useRef(null);

  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  // 註冊時頭像上傳失敗會導向本頁並帶入提示
  useEffect(() => {
    if (location.state?.message) {
      setFeedback({ type: "info", message: location.state.message });
    }
  }, [location.state]);

  function load() {
    setError(false);
    setProfile(null);
    getMyProfile(token)
      .then((response) => {
        const data = response.data;
        setProfile(data);
        setNickname(data.nickname);
        setContacts({
          facebook: data.facebook_contact ?? "",
          discord: data.discord_contact ?? "",
          line: data.line_contact ?? "",
        });
        setAvatarUrl(data.avatar_url);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateContact(key, value) {
    setContacts((previous) => ({ ...previous, [key]: value }));
  }

  function handleAvatarPick(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setFeedback(null);
    setPendingAvatar(file);
  }

  /** 裁切成 1:1 後才上傳：頭像各處都是圓形顯示，不裁切會被壓變形。 */
  async function handleAvatarCropConfirm(croppedFile) {
    setUploading(true);
    setFeedback(null);
    try {
      const response = await uploadImage(croppedFile, "avatar", token);
      setAvatarUrl(response.data.url);
      setPendingAvatar(null);
      setFeedback({ type: "info", message: "頭像已上傳，請按「儲存資料」完成套用。" });
    } catch {
      setFeedback({ type: "error", message: "頭像上傳失敗，請稍後再試。" });
    } finally {
      setUploading(false);
    }
  }

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);
    setFieldErrors({});
    try {
      await updateMyProfile({ nickname, avatar_url: avatarUrl }, token);
      await updateMyContacts(
        {
          facebook_contact: contacts.facebook || null,
          discord_contact: contacts.discord || null,
          line_contact: contacts.line || null,
        },
        token,
      );
      setFeedback({ type: "success", message: "資料已儲存。" });
      await refreshSession();
      load();
    } catch (err) {
      // 欄位層級錯誤（例如 Facebook 連結格式）掛回對應欄位，
      // 跨欄位錯誤（至少一項聯絡方式）提到頂端顯示
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR" && err.details?.fields) {
        const flattened = {};
        const generalMessages = [];
        Object.entries(err.details.fields).forEach(([field, messages]) => {
          if (field === "_") {
            generalMessages.push(...messages);
          } else {
            flattened[field] = messages;
          }
        });
        setFieldErrors(flattened);
        setFeedback(
          generalMessages.length > 0
            ? { type: "error", message: generalMessages.join("　") }
            : { type: "error", message: "輸入資料格式不正確，請檢查後再儲存。" },
        );
      } else {
        setFeedback({
          type: "error",
          message: err?.message ?? "儲存時發生錯誤，請稍後再試。",
        });
      }
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!profile) {
    return <PageLoader />;
  }

  return (
    <>
      <Breadcrumb items={[{ label: "首頁", to: "/" }, { label: "個人資料" }]} />

      <div className="pf-panel">
        <div className="pf-head">
          <h1>個人資料與聯絡方式</h1>
          <p>管理您的個人資料與聯絡方式，讓團主與其他成員能更方便地與您聯繫。</p>
        </div>

        {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

        <form onSubmit={handleSave}>
          <div className="pf-avatar-box">
            <div className="pf-avatar-wrap">
              {avatarUrl ? (
                <img className="pf-avatar" src={resolveMediaUrl(avatarUrl)} alt="" />
              ) : (
                <span className="pf-avatar pf-avatar-fallback" aria-hidden="true">
                  {nickname?.[0]?.toUpperCase() ?? "?"}
                </span>
              )}
              <button
                type="button"
                className="pf-avatar-camera"
                aria-label="更換頭像"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                <CameraIcon />
              </button>
            </div>
            <div className="pf-avatar-text">
              <h2>頭像</h2>
              <p>上傳個人頭像，讓其他成員更容易認出您。</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="pf-avatar-input"
                onChange={handleAvatarPick}
              />
              <Button
                type="button"
                variant="secondary"
                loading={uploading}
                className="pf-avatar-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadIcon />
                更換頭像
              </Button>
            </div>
          </div>

          <div className="pf-row">
            <label htmlFor="profile-nickname">暱稱</label>
            <div className="pf-row-input">
              <input
                id="profile-nickname"
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                required
              />
              <FieldError error={fieldErrors.nickname} />
            </div>
          </div>

          <div className="pf-row">
            <label htmlFor="profile-email">
              Email<span className="pf-row-note">（不可修改）</span>
            </label>
            <div className="pf-row-input">
              <input id="profile-email" value={profile.email} disabled />
            </div>
          </div>

          {CONTACT_FIELDS.map((contact) => {
            const Icon = contact.icon;
            return (
              <div key={contact.key} className="pf-row">
                <label htmlFor={`profile-${contact.key}`} className="pf-row-contact">
                  <Icon />
                  {contact.label}
                </label>
                <div className="pf-row-input">
                  <input
                    id={`profile-${contact.key}`}
                    placeholder={contact.placeholder}
                    value={contacts[contact.key]}
                    onChange={(event) => updateContact(contact.key, event.target.value)}
                  />
                  <FieldError error={fieldErrors[`${contact.key}_contact`]} />
                </div>
              </div>
            );
          })}

          <p className="auth-info-note pf-note">
            請至少提供一種聯絡方式，方便團主或其他成員與您聯繫。
          </p>

          <div className="pf-actions">
            <Button type="submit" loading={saving} className="pf-submit">
              <SaveIcon />
              儲存資料
            </Button>
          </div>
        </form>
      </div>

      {pendingAvatar && (
        <Modal title="裁切頭像" onClose={() => setPendingAvatar(null)}>
          <ImageCropper
            file={pendingAvatar}
            aspectRatio={1}
            aspectLabel="1:1"
            round
            loading={uploading}
            confirmLabel="套用並上傳"
            onCancel={() => setPendingAvatar(null)}
            onPickAnother={() => fileInputRef.current?.click()}
            onConfirm={handleAvatarCropConfirm}
          />
        </Modal>
      )}
    </>
  );
}
