import { apiRequest } from "./client.js";

export function getProductDetail(productId, token) {
  return apiRequest(`/products/${productId}`, { token });
}

export function getProductGroupBuys(productId, query = {}) {
  const {
    sort,
    availableOnly,
    paymentMethod,
    requiresSecondPayment,
    includesFullGift,
    page = 1,
    pageSize = 20,
  } = query;
  return apiRequest(`/products/${productId}/group-buys`, {
    params: {
      sort,
      available_only: availableOnly,
      payment_method: paymentMethod || undefined,
      requires_second_payment: requiresSecondPayment,
      includes_full_gift: includesFullGift,
      page,
      page_size: pageSize,
    },
  });
}
