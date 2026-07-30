import { useEffect, useRef, useState } from "react";
import {
  getMyGroupLeaderProfile,
  updateMyDefaultRules,
  updateMyGroupLeaderProfile,
} from "../../api/groupLeaderProfile.js";
import { uploadImage } from "../../api/uploads.js";
import { resolveMediaUrl } from "../../api/client.js";
import { getMyProfile, updateMyProfile } from "../../api/users.js";
import { useAuth } from "../../context/AuthContext.jsx";
import Alert from "../../components/common/Alert.jsx";
import Button from "../../components/common/Button.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import FormField from "../../components/common/FormField.jsx";
import PageLoader from "../../components/common/PageLoader.jsx";
import {
  DiscordIcon,
  FacebookIcon,
  InfoIcon,
  LineIcon,
  LockIcon,
  SaveIcon,
  ShieldIcon,
  UploadIcon,
} from "../../components/common/icons.jsx";

const INTRO_MAX_LENGTH = 300;
const RULES_MAX_LENGTH = 500;

export default function ProfilePage() {
  const { token, refreshSession } = useAuth();
  const [profile, setProfile] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [error, setError] = useState(false);

  const [displayName, setDisplayName] = useState("");
  const [introduction, setIntroduction] = useState("");
  const [facebookUrl, setFacebookUrl] = useState("");
  const [discordContact, setDiscordContact] = useState("");
  const [lineContact, setLineContact] = useState("");
  const [defaultRules, setDefaultRules] = useState("");
  const [avatarUrl, setAvatarUrl] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const fileInputRef = useRef(null);

  function load() {
    setError(false);
    setProfile(null);
    Promise.all([getMyGroupLeaderProfile(token), getMyProfile(token)])
      .then(([profileResponse, userResponse]) => {
        const data = profileResponse.data;
        setProfile(data);
        setUserProfile(userResponse.data);
        setDisplayName(data.display_name ?? "");
        setIntroduction(data.introduction ?? "");
        setFacebookUrl(data.facebook_url ?? "");
        setDiscordContact(data.discord_contact ?? "");
        setLineContact(data.line_contact ?? "");
        setDefaultRules(data.default_rules ?? "");
        setAvatarUrl(userResponse.data.avatar_url);
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
      const uploadResponse = await uploadImage(file, "avatar", token);
      await updateMyProfile({ avatar_url: uploadResponse.data.url }, token);
      setAvatarUrl(uploadResponse.data.url);
    } catch {
      setFeedback({ type: "error", message: "頭像上傳失敗，請稍後再試。" });
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  /**
   * 依圖 28 只有一顆「儲存變更」，但後端是兩支 API（基本資料、預設團規），
   * 因此依序呼叫。基本資料成功而團規失敗時要說清楚只有團規沒存到——
   * 否則團主會以為整份都沒儲存而重打一次。
   */
  async function handleSaveAll(event) {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);

    try {
      await updateMyGroupLeaderProfile(
        {
          display_name: profile.display_name ? undefined : displayName,
          introduction,
          facebook_url: facebookUrl || null,
          discord_contact: discordContact || null,
          line_contact: lineContact || null,
        },
        token,
      );
    } catch (err) {
      setFeedback({
        type: "error",
        message: `基本資料儲存失敗，預設團規也尚未儲存：${err.message ?? "請稍後再試。"}`,
      });
      setSaving(false);
      return;
    }

    try {
      await updateMyDefaultRules(defaultRules, token);
    } catch (err) {
      setFeedback({
        type: "error",
        message: `基本資料已儲存，但預設團規儲存失敗：${err.message ?? "請稍後再試。"}`,
      });
      await refreshSession();
      load();
      setSaving(false);
      return;
    }

    setFeedback({ type: "success", message: "團主資料已儲存。" });
    await refreshSession();
    load();
    setSaving(false);
  }

  if (error) {
    return <ErrorState onRetry={load} />;
  }

  if (!profile || !userProfile) {
    return <PageLoader />;
  }

  const nameLocked = Boolean(profile.display_name);
  const isComplete = profile.is_profile_complete;
  const hasAnyContact = Boolean(facebookUrl || discordContact || lineContact);

  const contactRows = [
    {
      key: "facebook",
      label: "Facebook",
      Icon: FacebookIcon,
      value: facebookUrl,
      setValue: setFacebookUrl,
      // 團主資料的 Facebook 必須是連結（後端以 is_facebook_url 驗證）
      placeholder: "請輸入 Facebook 連結（例如：facebook.com/yourname）",
    },
    {
      key: "discord",
      label: "Discord",
      Icon: DiscordIcon,
      value: discordContact,
      setValue: setDiscordContact,
      placeholder: "請輸入 Discord 帳號（例如：yourname_2025）",
    },
    {
      key: "line",
      label: "LINE",
      Icon: LineIcon,
      value: lineContact,
      setValue: setLineContact,
      placeholder: "請輸入 LINE ID（例如：@xxxx）",
    },
  ];

  return (
    <>
      <div className="page-header">
        <h1>團主資料管理</h1>
        <p className="helper-text">完善您的公開資料，讓團員更了解您並信任您的開團服務。</p>
      </div>

      {feedback && <Alert type={feedback.type}>{feedback.message}</Alert>}

      <form className="glp-layout" onSubmit={handleSaveAll}>
        <div className="glp-card">
          <div className="glp-basic">
            <div className="glp-avatar-col">
              <h2 className="section-title plain">基本資料</h2>

              <div className="glp-avatar-box">
                {avatarUrl ? (
                  <img className="glp-avatar" src={resolveMediaUrl(avatarUrl)} alt="" />
                ) : (
                  <span className="glp-avatar glp-avatar-fallback" aria-hidden="true">
                    {displayName?.[0] ?? "?"}
                  </span>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  style={{ display: "none" }}
                  onChange={handleAvatarChange}
                />
                <Button
                  type="button"
                  variant="secondary"
                  loading={uploading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadIcon />
                  更換頭像
                </Button>

                {/* 參考圖寫「2MB」，但後端上限實際是 10MB 且接受 WebP，
                    文案以實際限制為準（使用者 2026-07-30 裁決） */}
                <p className="glp-avatar-hint">
                  建議尺寸 512x512px，支援 JPG、PNG、WebP，檔案不超過 10MB。
                </p>
              </div>

              {/* 公開資料狀態：已啟用為綠卡，未啟用為紅卡並寫明缺什麼、影響什麼 */}
              <div className={`glp-status${isComplete ? " is-ok" : " is-warn"}`}>
                <span className="glp-status-icon">
                  <ShieldIcon />
                </span>
                <span className="glp-status-text">
                  <strong>公開資料狀態：{isComplete ? "已啟用" : "未啟用"}</strong>
                  {isComplete ? (
                    <span>您的團主公開頁面已啟用，團員可以查看並聯絡您。</span>
                  ) : (
                    <>
                      <span>
                        尚未完成
                        {!nameLocked && "「團主公開名稱」"}
                        {!nameLocked && !hasAnyContact && "與"}
                        {!hasAnyContact && "「公開聯絡方式」"}
                        設定。
                      </span>
                      <span>完成後才能開團與發布公告，公開頁面也才會對團員顯示。</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            <div className="glp-fields-col">
              <FormField
                label={`團主公開名稱${nameLocked ? "（不可修改）" : ""}`}
                htmlFor="gl-display-name"
                required={!nameLocked}
                helperText="公開名稱一旦設定後將無法更改，請謹慎設定。"
              >
                <span className="glp-locked-input">
                  <input
                    id="gl-display-name"
                    value={displayName}
                    disabled={nameLocked}
                    placeholder="請輸入團主公開名稱"
                    onChange={(event) => setDisplayName(event.target.value)}
                    required
                  />
                  {nameLocked && (
                    <span className="glp-lock-icon" aria-label="不可修改">
                      <LockIcon />
                    </span>
                  )}
                </span>
              </FormField>

              <div className="form-field glp-counted-field">
                <label htmlFor="gl-intro">自我介紹</label>
                <textarea
                  id="gl-intro"
                  rows={7}
                  maxLength={INTRO_MAX_LENGTH}
                  placeholder="向團員介紹自己、開團經驗與服務範圍。"
                  value={introduction}
                  onChange={(event) => setIntroduction(event.target.value)}
                />
                <span className="glp-char-count">
                  {introduction.length} / {INTRO_MAX_LENGTH}
                </span>
              </div>
            </div>
          </div>

          <div className="glp-contacts">
            <h2 className="section-title plain">
              公開聯絡方式
              <span className="glp-section-sub">（至少需填寫一項）</span>
            </h2>

            {contactRows.map((row) => (
              <div className="glp-contact-row" key={row.key}>
                <span className="glp-contact-label">
                  <row.Icon />
                  {row.label}
                </span>
                <input
                  value={row.value}
                  placeholder={row.placeholder}
                  aria-label={row.label}
                  onChange={(event) => row.setValue(event.target.value)}
                />
                <button
                  type="button"
                  className="glp-contact-clear"
                  aria-label={`清除 ${row.label}`}
                  disabled={!row.value}
                  onClick={() => row.setValue("")}
                >
                  ×
                </button>
              </div>
            ))}

            {/* 用 SVG icon 而非 ⓘ 文字字元：文字字元會被選取複製，也無法統一大小與顏色 */}
            <p className={`glp-contact-hint${hasAnyContact ? "" : " is-warn"}`}>
              <InfoIcon />
              請至少提供一種公開聯絡方式，方便團員與您聯繫。
            </p>
          </div>
        </div>

        {/* 右欄用一個容器把「預設團規」與「儲存變更」上下堆疊：
            若讓儲存卡自己去佔 grid 的第二列，它會被推到最高那張卡（基本資料）的
            底線之下，看起來就與這兩張卡片脫節（使用者 2026-07-30 指出）。 */}
        <div className="glp-side-col">
          <div className="glp-card glp-rules-card">
            <h2 className="section-title plain">預設團規</h2>
            <p className="helper-text">此內容將顯示於您的開團頁面，請清楚說明您的開團規則。</p>

            <div className="form-field glp-counted-field glp-rules-field">
              <textarea
                rows={14}
                maxLength={RULES_MAX_LENGTH}
                placeholder="例如：先匯款／可取付、可能需二補、出貨時間依到貨情況通知…"
                value={defaultRules}
                onChange={(event) => setDefaultRules(event.target.value)}
                aria-label="預設團規"
              />
              <span className="glp-char-count">
                {defaultRules.length} / {RULES_MAX_LENGTH}
              </span>
            </div>
          </div>

          {/* 儲存按鈕獨立一張卡片：放在「預設團規」卡內會被誤認為只儲存團規，
              實際上這一顆同時儲存基本資料與預設團規（使用者 2026-07-30 指出）。 */}
          <div className="glp-card glp-save-card">
            <p className="glp-save-note">將同時儲存基本資料、公開聯絡方式與預設團規。</p>
            <Button type="submit" fullWidth loading={saving} className="glp-save-btn">
              <SaveIcon />
              儲存變更
            </Button>
          </div>
        </div>
      </form>
    </>
  );
}
