import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import logoIcon from "../assets/首頁icon.png";
import Alert from "../components/common/Alert.jsx";
import Button from "../components/common/Button.jsx";
import { requestPasswordReset } from "../api/auth.js";
import { ApiError } from "../api/client.js";
import { ArrowLeftIcon, MailIcon } from "../components/common/icons.jsx";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [formError, setFormError] = useState("");
  const [sent, setSent] = useState(false);
  const [expiresInMinutes, setExpiresInMinutes] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(0);

  useEffect(() => {
    if (resendCountdown <= 0) return undefined;
    const timer = setTimeout(() => setResendCountdown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [resendCountdown]);

  async function handleSubmit(event) {
    event.preventDefault();
    setFieldError("");
    setFormError("");

    const trimmed = email.trim();
    if (!trimmed) {
      setFieldError("請輸入 Email。");
      return;
    }

    setSubmitting(true);
    try {
      const response = await requestPasswordReset(trimmed);
      setSent(true);
      setExpiresInMinutes(Math.round(response.data.expires_in_seconds / 60));
      setResendCountdown(60);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "VALIDATION_ERROR") {
          setFieldError("請輸入有效的 Email。");
        } else {
          setFormError(err.message || "重設信件寄送失敗，請稍後再試。");
        }
      } else {
        setFormError("重設信件寄送失敗，請稍後再試。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <img src={logoIcon} className="auth-brand-icon" alt="" />
          <span className="auth-brand-text">
            <span className="auth-brand-title">EchoGather</span>
            <span className="auth-brand-subtitle">鳴潮周邊團購平台</span>
          </span>
        </div>

        <h1 className="auth-title">忘記密碼</h1>
        <div className="auth-divider" aria-hidden="true">
          <span className="auth-divider-star">✦</span>
        </div>

        <p className="auth-lead">請輸入註冊時使用的 Email，我們會寄送密碼重設連結給你。</p>

        {formError && <Alert type="error">{formError}</Alert>}
        {sent && (
          <Alert type="info">
            若這個 Email 已註冊，重設連結已寄出，請至信箱收信（{expiresInMinutes} 分鐘內有效）。
            沒收到的話請檢查垃圾信件匣。
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label htmlFor="forgot-email">Email</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <MailIcon />
              </span>
              <input
                id="forgot-email"
                type="email"
                required
                placeholder="請輸入 Email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </div>
            {fieldError && <span className="auth-error">{fieldError}</span>}
          </div>

          <Button
            type="submit"
            fullWidth
            className="auth-submit"
            loading={submitting}
            disabled={resendCountdown > 0}
          >
            {resendCountdown > 0 ? `${resendCountdown} 秒後可重寄` : sent ? "重新寄送" : "寄送重設連結"}
          </Button>
        </form>

        <Link className="auth-switch" to="/login">
          <ArrowLeftIcon />
          返回登入
        </Link>
      </div>
    </div>
  );
}
