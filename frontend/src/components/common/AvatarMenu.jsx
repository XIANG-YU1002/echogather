import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { resolveMediaUrl } from "../../api/client.js";
import LogoutButton from "./LogoutButton.jsx";

export default function AvatarMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (event.target.closest(".modal-overlay")) {
        return;
      }
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initial = user.nickname?.[0]?.toUpperCase() ?? "?";
  const isAdmin = user.permissions?.is_admin ?? false;

  return (
    <div className="avatar-menu" ref={containerRef}>
      <button
        type="button"
        className="avatar-menu-trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        {user.avatar_url ? (
          <img className="avatar-circle" src={resolveMediaUrl(user.avatar_url)} alt="" />
        ) : (
          <span className="avatar-circle" aria-hidden="true">
            {initial}
          </span>
        )}
        <span>{user.nickname}</span>
      </button>
      {open && (
        <div className="avatar-menu-dropdown" role="menu">
          {isAdmin ? (
            <Link to="/admin" role="menuitem" onClick={() => setOpen(false)}>
              管理員後台
            </Link>
          ) : (
            <>
              <Link to="/profile" role="menuitem" onClick={() => setOpen(false)}>
                個人資料
              </Link>
              <Link to="/favorites" role="menuitem" onClick={() => setOpen(false)}>
                收藏的商品
              </Link>
              <Link to="/orders" role="menuitem" onClick={() => setOpen(false)}>
                我的訂單
              </Link>
              {!user.group_leader && (
                <Link
                  to="/group-leader-application"
                  role="menuitem"
                  onClick={() => setOpen(false)}
                >
                  申請成為團主
                </Link>
              )}
              {user.group_leader && (
                <Link to="/group-leader" role="menuitem" onClick={() => setOpen(false)}>
                  團主後台
                </Link>
              )}
            </>
          )}
          <LogoutButton role="menuitem" onBeforeConfirm={() => setOpen(false)} />
        </div>
      )}
    </div>
  );
}
