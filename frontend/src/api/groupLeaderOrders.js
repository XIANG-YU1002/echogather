import { apiRequest } from "./client.js";

export function getGroupLeaderOrders(token, params = {}) {
  const { groupBuyId, activityId, status, hasPendingCancellation, keyword, page = 1, pageSize = 20 } = params;
  return apiRequest("/group-leader/orders", {
    token,
    params: {
      group_buy_id: groupBuyId,
      activity_id: activityId,
      status,
      has_pending_cancellation: hasPendingCancellation,
      keyword,
      page,
      page_size: pageSize,
    },
  });
}

export function getGroupLeaderOrderDetail(orderId, token) {
  return apiRequest(`/group-leader/orders/${orderId}`, { token });
}

export function acceptOrder(orderId, token) {
  return apiRequest(`/group-leader/orders/${orderId}/accept`, { method: "POST", token });
}

export function rejectOrder(orderId, reason, token) {
  return apiRequest(`/group-leader/orders/${orderId}/reject`, {
    method: "POST",
    body: { reason },
    token,
  });
}

export function markOrderPaid(orderId, token) {
  return apiRequest(`/group-leader/orders/${orderId}/mark-paid`, { method: "POST", token });
}

export function markOrderShipped(orderId, token) {
  return apiRequest(`/group-leader/orders/${orderId}/mark-shipped`, { method: "POST", token });
}

/** 一鍵將該開團所有「已付款」訂單標記為已出貨。 */
export function markAllOrdersShipped(groupBuyId, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/orders/mark-all-shipped`, {
    method: "POST",
    token,
  });
}

export function completeOrder(orderId, token) {
  return apiRequest(`/group-leader/orders/${orderId}/complete`, { method: "POST", token });
}

export function approveCancellationRequest(requestId, responseNote, token) {
  return apiRequest(`/group-leader/cancellation-requests/${requestId}/approve`, {
    method: "POST",
    body: { response_note: responseNote || null },
    token,
  });
}

export function rejectCancellationRequest(requestId, responseNote, token) {
  return apiRequest(`/group-leader/cancellation-requests/${requestId}/reject`, {
    method: "POST",
    body: { response_note: responseNote || null },
    token,
  });
}
