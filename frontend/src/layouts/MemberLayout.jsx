import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import LogoutButton from "../components/common/LogoutButton.jsx";

const NAV_ITEMS = [
  { to: "/profile", label: "個人資料" },
  { to: "/orders", label: "我的訂單" },
  { to: "/favorites", label: "收藏商品" },
  { to: "/notifications", label: "通知中心" },
  { to: "/group-leader-application", label: "團主申請" },
];

export default function MemberLayout() {
  const { isAuthenticated, initializing } = useAuth();

  if (initializing) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="member-layout">
      <aside className="member-sidebar">
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <LogoutButton className="member-sidebar-logout" />
      </aside>
      <div className="member-content">
        <Outlet />
      </div>
    </div>
  );
}
