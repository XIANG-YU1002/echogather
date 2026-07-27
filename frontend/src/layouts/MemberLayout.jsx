import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import LogoutButton from "../components/common/LogoutButton.jsx";

const BASE_NAV_ITEMS = [
  { to: "/profile", label: "個人資料" },
  { to: "/orders", label: "我的訂單" },
  { to: "/favorites", label: "收藏商品" },
  { to: "/notifications", label: "通知中心" },
];

// 已是團主者顯示「團主後台」，尚未申請者才顯示「團主申請」（與 AvatarMenu 一致）
const LEADER_NAV_ITEM = { to: "/group-leader", label: "團主後台" };
const APPLICATION_NAV_ITEM = { to: "/group-leader-application", label: "團主申請" };

export default function MemberLayout() {
  const { isAuthenticated, initializing, user } = useAuth();

  if (initializing) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const navItems = [
    ...BASE_NAV_ITEMS,
    user?.group_leader ? LEADER_NAV_ITEM : APPLICATION_NAV_ITEM,
  ];

  return (
    <div className="member-layout">
      <aside className="member-sidebar">
        <nav>
          {navItems.map((item) => (
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
