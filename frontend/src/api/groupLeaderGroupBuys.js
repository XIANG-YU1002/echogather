import { apiRequest } from "./client.js";

export function getMyGroupBuys(token, { status, keyword, sort, page = 1, pageSize = 20 } = {}) {
  return apiRequest("/group-leader/group-buys", {
    token,
    params: { status, keyword, sort, page, page_size: pageSize },
  });
}

export function createGroupBuy(payload, token) {
  return apiRequest("/group-leader/group-buys", { method: "POST", body: payload, token });
}

export function getGroupBuyProductOrders(groupBuyId, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/product-orders`, { token });
}

export function getMyGroupBuyDetail(groupBuyId, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}`, { token });
}

export function updateGroupBuySettings(groupBuyId, payload, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}`, {
    method: "PATCH",
    body: payload,
    token,
  });
}

export function addGroupBuyProduct(groupBuyId, payload, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/products`, {
    method: "POST",
    body: payload,
    token,
  });
}

export function updateGroupBuyProduct(groupBuyId, groupBuyProductId, payload, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/products/${groupBuyProductId}`, {
    method: "PATCH",
    body: payload,
    token,
  });
}

export function removeGroupBuyProduct(groupBuyId, groupBuyProductId, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/products/${groupBuyProductId}`, {
    method: "DELETE",
    token,
  });
}

export function closeGroupBuy(groupBuyId, token) {
  return apiRequest(`/group-leader/group-buys/${groupBuyId}/close`, { method: "POST", token });
}
