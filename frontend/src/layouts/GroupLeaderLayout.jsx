import { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import LogoutButton from "../components/common/LogoutButton.jsx";
import {
  ChevronDownIcon,
  ClipboardIcon,
  FolderIcon,
  HomeIcon,
  LogoutIcon,
  MegaphoneIcon,
  PlusCircleIcon,
  UserIcon,
} from "../components/common/icons.jsx";

// 依 docs/03 §26.1（使用者 2026-07-28 提供的文字規格，為此區塊最高依據）：
// 「開團管理」是分組標題而非頁面，底下才是我的開團／建立開團。
const NAV_ITEMS = [
  { to: "/group-leader", label: "儀表板", icon: HomeIcon, end: true },
  {
    label: "開團管理",
    icon: FolderIcon,
    children: [
      {
        to: "/group-leader/group-buys",
        label: "我的開團",
        icon: FolderIcon,
        // 開團設定頁（/group-buys/:id）屬於「我的開團」脈絡也要亮，但「建立開團」除外，
        // 否則兩個子項會同時亮。
        isActive: (pathname) =>
          pathname.startsWith("/group-leader/group-buys") &&
          pathname !== "/group-leader/group-buys/new",
      },
      { to: "/group-leader/group-buys/new", label: "建立開團", icon: PlusCircleIcon },
    ],
  },
  { to: "/group-leader/orders", label: "訂單管理", icon: ClipboardIcon },
  { to: "/group-leader/announcements", label: "公告管理", icon: MegaphoneIcon },
  { to: "/group-leader/profile", label: "團主資料", icon: UserIcon },
];

function NavItem({ item, pathname }) {
  const Icon = item.icon;
  const forcedActive = item.isActive ? item.isActive(pathname) : null;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => ((forcedActive ?? isActive) ? "active" : "")}
    >
      <Icon />
      {item.label}
    </NavLink>
  );
}

/** 可展開的選單分組：點標題才顯示子項；目前正在子項頁面時預設展開。 */
function NavGroup({ item, pathname }) {
  const containsCurrent = item.children.some((child) =>
    child.isActive ? child.isActive(pathname) : pathname === child.to
  );
  const [open, setOpen] = useState(containsCurrent);

  // 由其他選單導覽進子項時（例如儀表板的「管理開團」），分組要自動展開
  useEffect(() => {
    if (containsCurrent) {
      setOpen(true);
    }
  }, [containsCurrent]);

  const Icon = item.icon;
  return (
    <div className="sidebar-group">
      <button
        type="button"
        className={`sidebar-group-title${open ? " is-open" : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <Icon />
        <span className="sidebar-group-label">{item.label}</span>
        <ChevronDownIcon className="sidebar-group-chevron" />
      </button>
      {open && (
        <div className="sidebar-subnav">
          {item.children.map((child) => (
            <NavItem key={child.to} item={child} pathname={pathname} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function GroupLeaderLayout() {
  const { user, initializing, isAuthenticated } = useAuth();
  const location = useLocation();

  if (initializing) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ redirectPath: location.pathname }} />;
  }

  if (!user.group_leader) {
    return <Navigate to="/" replace />;
  }

  if (!user.group_leader.is_profile_complete && location.pathname !== "/group-leader/profile") {
    return <Navigate to="/group-leader/profile" replace />;
  }

  return (
    <div className="member-layout">
      <aside className="member-sidebar">
        <p className="helper-text" style={{ margin: "0.25rem 0.5rem", fontWeight: 700 }}>
          團主後台
        </p>
        <nav>
          {NAV_ITEMS.map((item) =>
            item.children ? (
              <NavGroup key={item.label} item={item} pathname={location.pathname} />
            ) : (
              <NavItem key={item.to} item={item} pathname={location.pathname} />
            )
          )}
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
