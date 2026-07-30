import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getUnreadCount } from "../api/notifications.js";
import { useAuth } from "./AuthContext.jsx";

/**
 * 未讀通知數的共用狀態。
 *
 * Header 鈴鐺與通知中心頁都會改變已讀狀態，若各自維護一份計數，
 * 在一邊標記已讀後另一邊的紅點不會即時消失。統一由此 Context 持有。
 */
const NotificationContext = createContext(null);

// 未讀數的自動刷新間隔。後端沒有推播（無 WebSocket／SSE），新通知是由團主端的操作
// 產生的，前端無從得知，因此定時重新查詢。30 秒是「夠即時」與「別一直打 API」
// 之間的折衷；真正需要秒級更新時才值得引入推播。
const POLL_INTERVAL_MS = 30000;

export function NotificationProvider({ children }) {
  const { isAuthenticated, token, user, initializing } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const isAdmin = user?.permissions?.is_admin ?? false;

  const refresh = useCallback(async () => {
    if (!isAuthenticated || isAdmin || !token) {
      setUnreadCount(0);
      return;
    }
    try {
      const response = await getUnreadCount(token);
      setUnreadCount(response.data.unread_count);
    } catch {
      // 靜默失敗：未讀數取得失敗不影響其他功能。
    }
  }, [isAuthenticated, isAdmin, token]);

  useEffect(() => {
    if (initializing) return undefined;
    refresh();

    // 未登入／管理員不需要輪詢（refresh 本身也會直接歸零）
    if (!isAuthenticated || isAdmin || !token) return undefined;

    const timer = setInterval(refresh, POLL_INTERVAL_MS);

    // 切回這個分頁時立刻刷新，不必等下一次輪詢，也省掉背景分頁的無用請求
    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        refresh();
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", refresh);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", refresh);
    };
  }, [initializing, refresh, isAuthenticated, isAdmin, token]);

  const value = useMemo(
    () => ({ unreadCount, refresh, setUnreadCount }),
    [unreadCount, refresh],
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === null) {
    throw new Error("useNotifications 必須在 NotificationProvider 內使用。");
  }
  return context;
}
