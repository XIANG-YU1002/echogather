import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import logoIcon from "../assets/首頁icon.png";
import Alert from "../components/common/Alert.jsx";
import Button from "../components/common/Button.jsx";
import PageLoader from "../components/common/PageLoader.jsx";
import { resetPassword, verifyPasswordResetToken } from "../api/auth.js";
import { ApiError } from "../api/client.js";
import {
  ArrowLeftIcon,
  EyeIcon,
  EyeOffIcon,
  LockIcon,
} from "../components/common/icons.jsx";

/** 錯誤訊息可能是多筆，逐行列出。 */
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

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [tokenValid, setTokenValid] = useState(null);
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 先確認連結有效再顯示表單，避免使用者填完才被拒
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
      return;
    }
    verifyPasswordResetToken(token)
      .then((response) => setTokenValid(response.data.is_valid))
      .catch(() => setTokenValid(false));
  }, [token]);

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setFieldErrors({});
    setSubmitting(true);

    try {
      await resetPassword({ token, password, passwordConfirmation });
      navigate("/login", {
        replace: true,
        state: { message: "密碼已重設完成，請使用新密碼登入。" },
      });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "VALIDATION_ERROR" && err.details?.fields) {
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
          if (generalMessages.length > 0) {
            setFormError(generalMessages);
          }
        } else if (err.code === "PASSWORD_RESET_TOKEN_INVALID") {
          // 連結在填表過程中過期或已被使用，切回失效畫面
          setTokenValid(false);
        } else {
          setFormError(err.message || "重設密碼時發生錯誤，請稍後再試。");
        }
      } else {
        setFormError("重設密碼時發生錯誤，請稍後再試。");
      }
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

        <h1 className="auth-title">設定新密碼</h1>
        <div className="auth-divider" aria-hidden="true">
          <span className="auth-divider-star">✦</span>
        </div>

        {tokenValid === null ? (
          <PageLoader label="正在確認重設連結..." />
        ) : tokenValid === false ? (
          <>
            <Alert type="error">
              這個重設連結無效、已過期或已經使用過了。請重新申請一次。
            </Alert>
            <Link className="btn btn-primary auth-submit" to="/forgot-password">
              重新申請重設連結
            </Link>
            <Link className="auth-switch" to="/login">
              <ArrowLeftIcon />
              返回登入
            </Link>
          </>
        ) : (
          <>
            <p className="auth-lead">請設定新的密碼，設定完成後即可使用新密碼登入。</p>

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
                <label htmlFor="reset-password">新密碼</label>
                <div className="auth-input">
                  <span className="auth-input-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="reset-password"
                    type={showPassword ? "text" : "password"}
                    required
                    placeholder="請輸入新密碼"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
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
                  <span className="auth-hint">
                    長度 8-72 個字元，至少包含一個英文字母及一個數字
                  </span>
                )}
              </div>

              <div className="auth-field">
                <label htmlFor="reset-password-confirmation">確認新密碼</label>
                <div className="auth-input">
                  <span className="auth-input-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="reset-password-confirmation"
                    type={showPasswordConfirmation ? "text" : "password"}
                    required
                    placeholder="請再次輸入新密碼"
                    value={passwordConfirmation}
                    onChange={(event) => setPasswordConfirmation(event.target.value)}
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
                <FieldError error={fieldErrors.password_confirmation} />
              </div>

              <Button type="submit" fullWidth loading={submitting} className="auth-submit">
                設定新密碼
              </Button>
            </form>

            <Link className="auth-switch" to="/login">
              <ArrowLeftIcon />
              返回登入
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
