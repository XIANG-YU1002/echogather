import { apiRequest } from "./client.js";

export function createOrder(rulesAccepted, token) {
  return apiRequest("/orders", { method: "POST", body: { rules_accepted: rulesAccepted }, token });
}

export function getMyOrders(
  token,
  { status, activityName, groupLeaderName, createdWithinDays, page = 1, pageSize = 20 } = {},
) {
  return apiRequest("/orders", {
    token,
    params: {
      status,
      activity_name: activityName || undefined,
      group_leader_name: groupLeaderName || undefined,
      created_within_days: createdWithinDays || undefined,
      page,
      page_size: pageSize,
    },
  });
}

export function getMyOrderDetail(orderId, token) {
  return apiRequest(`/orders/${orderId}`, { token });
}

export function createCancellationRequest(orderId, reason, token) {
  return apiRequest(`/orders/${orderId}/cancellation-requests`, {
    method: "POST",
    body: { reason: reason || null },
    token,
  });
}

/** 申請取消合併（拆單）。團主核准後訂單才會拆回合併前的多張。 */
export function createUnmergeRequest(orderId, reason, token) {
  return apiRequest(`/orders/${orderId}/unmerge-requests`, {
    method: "POST",
    body: { reason: reason || null },
    token,
  });
}
