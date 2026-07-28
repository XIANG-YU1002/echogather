import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import LogoutButton from "../components/common/LogoutButton.jsx";
import {
  BellIcon,
  CalendarIcon,
  HeartIcon,
  LogoutIcon,
  ShieldIcon,
  UserIcon,
} from "../components/common/icons.jsx";

const BASE_NAV_ITEMS = [
  { to: "/profile", label: "個人資料", icon: UserIcon },
  { to: "/orders", label: "我的訂單", icon: CalendarIcon },
  { to: "/favorites", label: "收藏商品", icon: HeartIcon },
  { to: "/notifications", label: "通知中心", icon: BellIcon },
];

// 已是團主者顯示「團主後台」，尚未申請者才顯示「團主申請」（與 AvatarMenu 一致）
const LEADER_NAV_ITEM = { to: "/group-leader", label: "團主後台", icon: ShieldIcon };
const APPLICATION_NAV_ITEM = {
  to: "/group-leader-application",
  label: "團主申請",
  icon: ShieldIcon,
};

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
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                <Icon />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <LogoutButton className="member-sidebar-logout">
          <LogoutIcon />
          登出
        </LogoutButton>
      </aside>
      <div className="member-content">
        <Outlet />
      </div>
    </div>
  );
}
