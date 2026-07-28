import { apiRequest } from "./client.js";

export function getFavoriteProducts(token, { page = 1, pageSize = 20, sort } = {}) {
  return apiRequest("/favorites/products", {
    token,
    params: { page, page_size: pageSize, sort },
  });
}

export function addFavorite(productId, token) {
  return apiRequest(`/favorites/products/${productId}`, { method: "POST", token });
}

export function removeFavorite(productId, token) {
  return apiRequest(`/favorites/products/${productId}`, { method: "DELETE", token });
}
