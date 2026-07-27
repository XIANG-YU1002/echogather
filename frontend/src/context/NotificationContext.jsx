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
    if (!initializing) {
      refresh();
    }
  }, [initializing, refresh]);

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
