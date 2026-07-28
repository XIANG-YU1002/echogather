import { useEffect, useRef } from "react";

/**
 * 定時在背景重新載入資料，並在使用者切回這個分頁／視窗時立即重載。
 *
 * 用於需要「看起來即時」的頁面（例如管理員的待審申請列表）。
 * 專案沒有推送機制，改以輪詢達成；Supabase 在 ap-south-1，每次往返約 700ms，
 * 因此預設間隔拉到 30 秒，並在分頁不可見時跳過請求，避免無意義的負載。
 *
 * 傳入的 callback 必須是「靜默」刷新——不清空既有資料、不切換 loading 狀態，
 * 否則畫面每次輪詢都會閃動。
 */
export function useAutoRefresh(callback, { intervalMs = 30000, enabled = true } = {}) {
  // 用 ref 保存最新的 callback，避免 callback 每次 render 變動就重設計時器
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return undefined;

    function refreshIfVisible() {
      if (document.visibilityState === "visible") {
        callbackRef.current();
      }
    }

    const timer = setInterval(refreshIfVisible, intervalMs);
    // 切回分頁或視窗重新取得焦點時不等下一次輪詢，立刻更新
    document.addEventListener("visibilitychange", refreshIfVisible);
    window.addEventListener("focus", refreshIfVisible);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshIfVisible);
      window.removeEventListener("focus", refreshIfVisible);
    };
  }, [intervalMs, enabled]);
}
