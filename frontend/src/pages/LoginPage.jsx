import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import logoIcon from "../assets/首頁icon.png";
import Alert from "../components/common/Alert.jsx";
import Button from "../components/common/Button.jsx";
import { ApiError } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import {
  ChevronRightIcon,
  EyeIcon,
  EyeOffIcon,
  LockIcon,
  MailIcon,
} from "../components/common/icons.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const redirectPath = location.state?.redirectPath ?? "/";
  const redirectNotice = location.state?.message;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const sessionUser = await login(email, password);
      if (sessionUser?.permissions?.is_admin) {
        navigate("/admin", { replace: true });
      } else {
        navigate(redirectPath, { replace: true });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "AUTH_INVALID_CREDENTIALS") {
        setError("Email 或密碼錯誤。");
      } else {
        setError("登入時發生錯誤，請稍後再試。");
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

        <h1 className="auth-title">登入</h1>
        <div className="auth-divider" aria-hidden="true">
          <span className="auth-divider-star">✦</span>
        </div>

        {redirectNotice && <Alert type="info">{redirectNotice}</Alert>}
        {error && <Alert type="error">{error}</Alert>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label htmlFor="login-email">Email</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <MailIcon />
              </span>
              <input
                id="login-email"
                type="email"
                required
                placeholder="請輸入 Email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </div>
          </div>

          <div className="auth-field">
            <label htmlFor="login-password">密碼</label>
            <div className="auth-input">
              <span className="auth-input-icon">
                <LockIcon />
              </span>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                required
                placeholder="請輸入密碼"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
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
            <Link className="auth-forgot" to="/forgot-password">
              忘記密碼？
            </Link>
          </div>

          <Button type="submit" fullWidth loading={submitting} className="auth-submit">
            登入
          </Button>
        </form>

        <Link className="auth-switch" to="/register">
          前往註冊
          <ChevronRightIcon />
        </Link>
      </div>
    </div>
  );
}
