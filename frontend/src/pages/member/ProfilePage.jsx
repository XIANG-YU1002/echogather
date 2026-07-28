import { useEffect, useRef, useState } from "react";
import { getMyProfile, updateMyContacts, updateMyProfile } from "../../api/users.js";
import { uploadImage } from "../../api/uploads.js";
import { resolveMediaUrl } from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import FormField from "../../components/common/FormField.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";

export default function ProfilePage() {
  const { token, refreshSession } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(false);

  const [nickname, setNickname] = useState("");
  const [facebookContact, setFacebookContact] = useState("");
  const [discordContact, setDiscordContact] = useState("");
  const [lineContact, setLineContact] = useState("");

  const [avatarUrl, setAvatarUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function load() {
    setError(false);
    setProfile(null);
    getMyProfile(token)
      .then((response) => {
        const data = response.data;
        setProfile(data);
        setNickname(data.nickname);
        setFacebookContact(data.facebook_contact ?? "");
        setDiscordContact(data.discord_contact ?? "");
        setLineContact(data.line_contact ?? "");
        setAvatarUrl(data.avatar_url);
      })
      .catch(() => setError(true));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleAvatarChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const response = await uploadImage(file, "avatar", token);
      setAvatarUrl(response.data.url);
    } catch {
      setFeedback({ type: "error", message: "頭像上傳失敗，請稍後再試。" });
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await updateMyProfile({ nickname, avatar_url: avatarUrl }, token);
      await updateMyContacts(
        {
          facebook_contact: facebookContact || null,
          discord_contact: discordContact || null,
          line_contact: lineContact || null,
        },
        token,
      );
      setFeedback({ type: "success", message: "資料已儲存。" });
      await refreshSession();
      load();
    } catch (err) {
      setFeedback({ type: "error", message: err.message ?? "儲存時發生錯誤，請稍後再試。" });
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
      <div className="page-header">
        <h1>個人資料與聯絡方式</h1>
        <p className="helper-text">管理您的個人資料與聯絡方式，讓團主與其他成員能更方便地與您聯繫。</p>
      </div>

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      <form onSubmit={handleSave}>
        <div className="group-buy-card-row" style={{ marginBottom: "1.5rem" }}>
          {avatarUrl ? (
            <img className="avatar-circle" style={{ width: "4.5rem", height: "4.5rem", fontSize: "1.5rem" }} src={resolveMediaUrl(avatarUrl)} alt="" />
          ) : (
            <span className="avatar-circle" style={{ width: "4.5rem", height: "4.5rem", fontSize: "1.5rem" }} aria-hidden="true">
              {nickname?.[0]?.toUpperCase() ?? "?"}
            </span>
          )}
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleAvatarChange}
            />
            <Button
              type="button"
              variant="secondary"
              loading={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              更換頭像
            </Button>
          </div>
        </div>

        <FormField label="暱稱" htmlFor="profile-nickname" required>
          <input
            id="profile-nickname"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            required
          />
        </FormField>

        <FormField label="Email（不可修改）" htmlFor="profile-email">
          <input id="profile-email" value={profile.email} disabled />
        </FormField>

        <FormField label="Facebook" htmlFor="profile-facebook">
          <input
            id="profile-facebook"
            placeholder="請輸入 Facebook 連結"
            value={facebookContact}
            onChange={(event) => setFacebookContact(event.target.value)}
          />
        </FormField>

        <FormField label="Discord" htmlFor="profile-discord">
          <input
            id="profile-discord"
            placeholder="username#1234"
            value={discordContact}
            onChange={(event) => setDiscordContact(event.target.value)}
          />
        </FormField>

        <FormField label="LINE" htmlFor="profile-line">
          <input
            id="profile-line"
            placeholder="@your_line_id"
            value={lineContact}
            onChange={(event) => setLineContact(event.target.value)}
          />
        </FormField>

        <p className="helper-text">請至少提供一種聯絡方式，方便團主或其他成員與您聯繫。</p>

        <Button type="submit" fullWidth loading={saving}>
          儲存資料
        </Button>
      </form>
    </>
  );
}
