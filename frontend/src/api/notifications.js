import { apiRequest } from "./client.js";

export function getNotifications(
  token,
  { notificationType, isRead, page = 1, pageSize = 20 } = {},
) {
  return apiRequest("/notifications", {
    token,
    params: {
      notification_type: notificationType || undefined,
      is_read: isRead === undefined || isRead === "" ? undefined : isRead,
      page,
      page_size: pageSize,
    },
  });
}

export function getUnreadCount(token) {
  return apiRequest("/notifications/unread-count", { token });
}

/** 圖 10 右側「通知摘要」：未讀總數與各類型總筆數。 */
export function getNotificationSummary(token) {
  return apiRequest("/notifications/summary", { token });
}

export function markNotificationRead(notificationId, token) {
  return apiRequest(`/notifications/${notificationId}/read`, { method: "PATCH", token });
}

export function markAllNotificationsRead(token) {
  return apiRequest("/notifications/read-all", { method: "PATCH", token });
}
