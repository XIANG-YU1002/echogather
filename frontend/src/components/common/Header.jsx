import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import logoIcon from "../../assets/首頁icon.png";
import AvatarMenu from "./AvatarMenu.jsx";
import NotificationBell from "./NotificationBell.jsx";
import SearchInput from "./SearchInput.jsx";
import { CartIcon } from "./icons.jsx";
import { useCart } from "../../context/CartContext.jsx";

export default function Header() {
  const { isAuthenticated, user } = useAuth();
  const isAdmin = user?.permissions?.is_admin ?? false;
  const { count: cartCount } = useCart();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link to="/" className="app-logo" aria-label="回到首頁">
          <img src={logoIcon} className="app-logo-icon" alt="" />
          <span className="app-logo-text">
            <span className="app-logo-title">EchoGather</span>
            <span className="app-logo-subtitle">鳴潮周邊團購平台</span>
          </span>
        </Link>
        <div className="app-header-search">
          <SearchInput />
        </div>
        <button
          type="button"
          className="btn btn-ghost mobile-menu-toggle"
          aria-label="開啟選單"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((prev) => !prev)}
        >
          選單
        </button>
        <nav className={`header-nav ${mobileOpen ? "mobile-open" : ""}`}>
          <Link to="/group-leaders" onClick={() => setMobileOpen(false)}>
            團主
          </Link>
          {isAuthenticated ? (
            <>
              {!isAdmin && (
                <Link
                  to="/follow-list"
                  className="notification-bell-trigger"
                  aria-label={`購物車${cartCount > 0 ? `，${cartCount} 項` : ""}`}
                  onClick={() => setMobileOpen(false)}
                >
                  <CartIcon className="icon-bell" />
                  {cartCount > 0 && (
                    <span className="notification-bell-badge">
                      {cartCount > 99 ? "99+" : cartCount}
                    </span>
                  )}
                </Link>
              )}
              {!isAdmin && <NotificationBell />}
              <AvatarMenu />
            </>
          ) : (
            <Link to="/login" onClick={() => setMobileOpen(false)}>
              登入/註冊
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
