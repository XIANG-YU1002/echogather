import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getFollowList } from "../api/followList.js";
import { useAuth } from "./AuthContext.jsx";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { isAuthenticated, token, user, initializing } = useAuth();
  const [count, setCount] = useState(0);
  const isAdmin = user?.permissions?.is_admin ?? false;

  const refresh = useCallback(async () => {
    if (!isAuthenticated || isAdmin || !token) {
      setCount(0);
      return;
    }
    try {
      const response = await getFollowList(token);
      const data = response.data;
      setCount(data && data.items ? data.items.length : 0);
    } catch {
      // 靜默失敗：購物車數量取得失敗不影響其他功能。
    }
  }, [isAuthenticated, isAdmin, token]);

  useEffect(() => {
    if (!initializing) {
      refresh();
    }
  }, [initializing, refresh]);

  const value = useMemo(() => ({ count, refresh }), [count, refresh]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === null) {
    throw new Error("useCart 必須在 CartProvider 內使用。");
  }
  return context;
}
