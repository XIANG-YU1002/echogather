import { apiRequest } from "./client.js";

export function getCharacterSuggestions(q, limit, token) {
  return apiRequest("/admin/characters/suggestions", { token, params: { q, limit } });
}

/** 立即建立角色（使用者 2026-07-30：新增角色當下就寫入資料庫，不等商品送出）。 */
export function createAdminCharacter(name, token) {
  return apiRequest("/admin/characters", { method: "POST", body: { name }, token });
}

/**
 * 刪除角色。後端會擋下仍有商品關聯的角色（CHARACTER_HAS_PRODUCT_RELATIONS），
 * 因此這實際上只刪得掉還沒被使用的角色——正好用來清掉打錯字新增的標籤。
 */
export function deleteAdminCharacter(characterId, token) {
  return apiRequest(`/admin/characters/${characterId}`, { method: "DELETE", token });
}
