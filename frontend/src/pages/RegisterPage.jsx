import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import logoIcon from "../assets/首頁icon.png";
import Alert from "../components/common/Alert.jsx";
import Button from "../components/common/Button.jsx";
import { register, sendVerificationCode } from "../api/auth.js";
import { ApiError } from "../api/client.js";
import { getToken } from "../api/tokenStorage.js";
import { uploadImage } from "../api/uploads.js";
import { updateMyProfile } from "../api/users.js";
import { useAuth } from "../context/AuthContext.jsx";
import {
  DiscordIcon,
  EyeIcon,
  EyeOffIcon,
  FacebookIcon,
  LineIcon,
  LockIcon,
  MailIcon,
  ShieldIcon,
  UserIcon,
} from "../components/common/icons.jsx";

const initialForm = {
  email: "",
  verification_code: "",
  password: "",
  password_confirmation: "",
  nickname: "",
  facebook_contact: "",
  discord_contact: "",
  line_contact: "",
};

/** 欄位錯誤：後端同一欄位可能回多筆訊息，全部逐行列出。 */
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

const CONTACT_FIELDS = [
  { name: "facebook_contact", label: "Facebook", icon: FacebookIcon, placeholder: "請輸入 Facebook 連結" },
  { name: "discord_contact", label: "Discord", icon: DiscordIcon, placeholder: "請輸入 Discord ID" },
  { name: "line_contact", label: "LINE", icon: LineIcon, placeholder: "請輸入 LINE ID" },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [codeNotice, setCodeNotice] = useState("");
  const [resendCountdown, setResendCountdown] = useState(0);
  const fileInputRef = useRef(null);

  // 重新發送驗證碼的倒數
  useEffect(() => {
    if (resendCountdown <= 0) return undefined;
    const timer = setTimeout(() => setResendCountdown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [resendCountdown]);

  // 預覽用的 object URL 需要在換圖／離開頁面時釋放
  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview("");
      return undefined;
    }
    const objectUrl = URL.createObjectURL(avatarFile);
    setAvatarPreview(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [avatarFile]);

  function updateField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSendCode() {
    setFormError("");
    setCodeNotice("");
    setFieldErrors((prev) => ({ ...prev, email: undefined, verification_code: undefined }));

    const email = form.email.trim();
    if (!email) {
      setFieldErrors((prev) => ({ ...prev, email: "請先輸入 Email。" }));
      return;
    }

    setSendingCode(true);
    try {
      const response = await sendVerificationCode(email);
      setResendCountdown(response.data.resend_available_in_seconds);
      const minutes = Math.round(response.data.expires_in_seconds / 60);
      setCodeNotice(`驗證碼已寄出，請至 ${email} 收信（${minutes} 分鐘內有效）。`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "EMAIL_ALREADY_EXISTS") {
          setFieldErrors((prev) => ({ ...prev, email: "此 Email 已被註冊。" }));
        } else if (err.code === "VALIDATION_ERROR") {
          setFieldErrors((prev) => ({ ...prev, email: "請輸入有效的 Email。" }));
        } else {
          setFormError(err.message || "驗證碼寄送失敗，請稍後再試。");
        }
      } else {
        setFormError("驗證碼寄送失敗，請稍後再試。");
      }
    } finally {
      setSendingCode(false);
    }
  }

  /**
   * 頭像在註冊當下無法上傳：POST /uploads/images 需要登入，而此時還沒有 token。
   * 因此等自動登入取得 token 之後再上傳並寫回個人資料。
   * 裁切功能依既有決議延後，等所有頁面改版完成後統一實作。
   */
  async function uploadAvatar() {
    const token = getToken();
    const uploaded = await uploadImage(avatarFile, "avatar", token);
    await updateMyProfile({ nickname: form.nickname, avatar_url: uploaded.data.url }, token);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setFieldErrors({});
    setSubmitting(true);

    try {
      await register({
        email: form.email,
        verification_code: form.verification_code,
        password: form.password,
        password_confirmation: form.password_confirmation,
        nickname: form.nickname,
        facebook_contact: form.facebook_contact || null,
        discord_contact: form.discord_contact || null,
        line_contact: form.line_contact || null,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "VALIDATION_ERROR" && err.details?.fields) {
          // 同一欄位可能有多筆錯誤，全部保留；不要只取第一筆
          const flattened = {};
          const generalMessages = [];
          Object.entries(err.details.fields).forEach(([field, messages]) => {
            // "_" 是跨欄位檢查（密碼不一致、聯絡方式至少一項）——沒有對應的
            // 輸入框可以掛，必須提到表單頂端顯示，否則使用者看不到任何提示
            if (field === "_") {
              generalMessages.push(...messages);
            } else {
              flattened[field] = messages;
            }
          });
          setFieldErrors(flattened);
          if (generalMessages.length > 0) {
            setFormError(generalMessages);
          } else if (Object.keys(flattened).length === 0) {
            setFormError("輸入資料格式不正確，請檢查後再送出。");
          }
        } else if (err.code === "EMAIL_ALREADY_EXISTS") {
          setFieldErrors({ email: "此 Email 已被註冊。" });
        } else if (err.code === "VERIFICATION_CODE_INVALID") {
          setFieldErrors({ verification_code: err.message });
        } else {
          setFormError(err.message || "註冊時發生錯誤，請稍後再試。");
        }
      } else {
        setFormError("註冊時發生錯誤，請稍後再試。");
      }
      setSubmitting(false);
      return;
    }

    // 帳號已建立成功，之後任何失敗都不能讓使用者以為註冊失敗。
    // 這裡刻意不解除 submitting：自動登入與頭像上傳合計約 1～2 秒
    // （Supabase 在 ap-south-1，每次往返延遲高，bcrypt 驗證也慢），
    // 若提早解除 loading，按鈕會恢復正常但頁面還沒跳轉，看起來像沒反應。
    // 所有分支都會 navigate 離開本頁，不需要復原這個狀態。
    try {
      await login(form.email, form.password);
    } catch {
      navigate("/login", { state: { message: "註冊成功，請登入。" } });
      return;
    }

    if (!avatarFile) {
      navigate("/", { replace: true });
      return;
    }

    try {
      await uploadAvatar();
      navigate("/", { replace: true });
    } catch {
      navigate("/profile", {
        state: { message: "註冊成功，但頭像設定失敗，請在此重新上傳。" },
      });
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card auth-card-wide">
        <div className="auth-brand">
          <img src={logoIcon} className="auth-brand-icon" alt="" />
          <span className="auth-brand-text">
            <span className="auth-brand-title">EchoGather</span>
            <span className="auth-brand-subtitle">鳴潮周邊團購平台</span>
          </span>
        </div>

        <h1 className="auth-title">建立帳號</h1>
        <div className="auth-divider" aria-hidden="true">
          <span className="auth-divider-star">✦</span>
        </div>
        <p className="auth-lead">請填寫以下資訊來建立您的帳號</p>

        {formError && (
          <Alert type="error">
            {Array.isArray(formError)
              ? formError.map((message) => (
                  <span key={message} className="auth-error-line">
                    {message}
                  </span>
                ))
              : formError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label htmlFor="register-email">Email</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <MailIcon />
              </span>
              <input
                id="register-email"
                type="email"
                required
                placeholder="請輸入您的 Email"
                value={form.email}
                onChange={(event) => updateField("email", event.target.value)}
                autoComplete="email"
              />
            </div>
            <FieldError error={fieldErrors.email} />
          </div>

          <div className="auth-field">
            <label htmlFor="register-verification-code">Email 驗證碼</label>
            <div className="auth-code-row">
              <div className="auth-input">
                <span className="auth-input-icon">
                  <ShieldIcon />
                </span>
                <input
                  id="register-verification-code"
                  type="text"
                  required
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="請輸入 6 位數驗證碼"
                  value={form.verification_code}
                  onChange={(event) => updateField("verification_code", event.target.value)}
                  autoComplete="one-time-code"
                />
              </div>
              <Button
                variant="secondary"
                className="auth-code-btn"
                loading={sendingCode}
                disabled={resendCountdown > 0}
                onClick={handleSendCode}
              >
                {resendCountdown > 0 ? `${resendCountdown} 秒後可重寄` : "發送驗證碼"}
              </Button>
            </div>
            {fieldErrors.verification_code ? (
              <FieldError error={fieldErrors.verification_code} />
            ) : codeNotice ? (
              <span className="auth-code-notice">{codeNotice}</span>
            ) : (
              <span className="auth-hint">請先取得驗證碼，確認信箱可正常收信後再完成註冊</span>
            )}
          </div>

          <div className="auth-field">
            <label htmlFor="register-password">密碼</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <LockIcon />
              </span>
              <input
                id="register-password"
                type={showPassword ? "text" : "password"}
                required
                placeholder="請輸入密碼"
                value={form.password}
                onChange={(event) => updateField("password", event.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="auth-input-toggle"
                aria-label={showPassword ? "隱藏密碼" : "顯示密碼"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((previous) => !previous)}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            {fieldErrors.password ? (
              <FieldError error={fieldErrors.password} />
            ) : (
              <span className="auth-hint">長度 8-72 個字元，至少包含一個英文字母及一個數字</span>
            )}
          </div>

          <div className="auth-field">
            <label htmlFor="register-password-confirmation">確認密碼</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <LockIcon />
              </span>
              <input
                id="register-password-confirmation"
                type={showPasswordConfirmation ? "text" : "password"}
                required
                placeholder="請再次輸入密碼"
                value={form.password_confirmation}
                onChange={(event) => updateField("password_confirmation", event.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="auth-input-toggle"
                aria-label={showPasswordConfirmation ? "隱藏密碼" : "顯示密碼"}
                aria-pressed={showPasswordConfirmation}
                onClick={() => setShowPasswordConfirmation((previous) => !previous)}
              >
                {showPasswordConfirmation ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            {fieldErrors.password_confirmation && (
              <FieldError error={fieldErrors.password_confirmation} />
            )}
          </div>

          <div className="auth-field">
            <label htmlFor="register-nickname">暱稱</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <UserIcon />
              </span>
              <input
                id="register-nickname"
                type="text"
                required
                placeholder="請輸入您的暱稱"
                value={form.nickname}
                onChange={(event) => updateField("nickname", event.target.value)}
                autoComplete="nickname"
              />
            </div>
            <FieldError error={fieldErrors.nickname} />
          </div>

          <div className="auth-field">
            <label>頭像（非必填）</label>
            <span className="auth-hint">上傳頭像讓其他團員更容易認出你</span>
            <div className="auth-avatar">
              {avatarPreview ? (
                <img className="auth-avatar-preview" src={avatarPreview} alt="頭像預覽" />
              ) : (
                <span className="auth-avatar-preview auth-avatar-empty" aria-hidden="true">
                  <UserIcon />
                </span>
              )}
              <div className="auth-avatar-actions">
                <input
                  ref={fileInputRef}
                  id="register-avatar"
                  type="file"
                  accept="image/*"
                  className="auth-avatar-input"
                  onChange={(event) => setAvatarFile(event.target.files?.[0] ?? null)}
                />
                <Button
                  variant="secondary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  選擇圖片
                </Button>
                {avatarFile && (
                  <Button
                    variant="muted"
                    onClick={() => {
                      setAvatarFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                  >
                    移除
                  </Button>
                )}
                <span className="auth-hint">建議使用 1:1 的圖片</span>
              </div>
            </div>
          </div>

          <div className="auth-field">
            <label>社群帳號</label>
            <span className="auth-hint">至少填寫一項，用於聯繫或發送團購通知</span>
            <div className="auth-contacts">
              {CONTACT_FIELDS.map((contact) => {
                const Icon = contact.icon;
                return (
                  <div key={contact.name} className="auth-contact">
                    <label className="auth-contact-head" htmlFor={`register-${contact.name}`}>
                      <Icon />
                      {contact.label}
                    </label>
                    <input
                      id={`register-${contact.name}`}
                      type="text"
                      placeholder={contact.placeholder}
                      value={form[contact.name]}
                      onChange={(event) => updateField(contact.name, event.target.value)}
                    />
                    <FieldError error={fieldErrors[contact.name]} />
                  </div>
                );
              })}
            </div>
          </div>

          <p className="auth-info-note">請至少填寫一項社群帳號，以便其他會員在團購時與您聯繫。</p>

          <Button type="submit" fullWidth loading={submitting} className="auth-submit">
            註冊
          </Button>
        </form>

        <p className="auth-after-note">
          {avatarFile
            ? "註冊成功後會自動登入並套用頭像。"
            : "註冊成功後會自動登入，直接開始使用。"}
        </p>

        <p className="auth-switch-line">
          已有帳號？
          <Link to="/login">前往登入</Link>
        </p>
      </div>
    </div>
  );
}
