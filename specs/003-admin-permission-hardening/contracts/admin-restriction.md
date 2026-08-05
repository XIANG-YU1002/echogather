# Contract: Admin 受限端點清單與拒絕回應

**Feature**: specs/003-admin-permission-hardening | **Date**: 2026-08-05
**盤點方法**: 逐檔讀取 `backend/app/api/v1/*.py` 的 Route 裝飾器（見 research.md 決策 3）。
本清單為 FR-001 的權威清單，SC-006 以此比對；實作與測試不得增減。

## 拒絕回應契約（全部 49 端點一致）

Admin 帳號（`app_user.role = admin`）附有效 Token 呼叫下列任一端點時：

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "ADMIN_MEMBER_ACCESS_FORBIDDEN",
    "message": "管理員帳號不可使用會員或團主功能。",
    "details": null
  }
}
```

- 未登入／Token 無效：維持既有 401 行為，不受本 feature 影響。
- 非 Admin 使用者：行為與修改前完全相同。
- 拒絕發生時零資料異動（FR-004）。
- 團主後台端點：Admin 一律先收到上述 403，不得先回 404 `GROUP_LEADER_PROFILE_NOT_FOUND` 或 403 `GROUP_LEADER_PROFILE_INCOMPLETE`（FR-006）。

Dependency 縮寫：`user` = `get_current_user`、`member` = `get_current_member_user`（新增）、
`glp` = `get_current_group_leader_profile`、`aglp` = `get_current_active_group_leader_profile`。
團主後台端點的「預定 Dependency」名稱不變，但 `glp` 改為依賴 `member`，故 Admin 會被前置拒絕。

## 類別 1：收藏（favorites.py，3 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 1 | GET | /api/v1/favorites/products | user | member |
| 2 | POST | /api/v1/favorites/products/{product_id} | user | member |
| 3 | DELETE | /api/v1/favorites/products/{product_id} | user | member |

## 類別 2：購物車（follow_list.py，5 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 4 | GET | /api/v1/follow-list | user | member |
| 5 | POST | /api/v1/follow-list/items | user | member |
| 6 | PATCH | /api/v1/follow-list/items/{item_id} | user | member |
| 7 | DELETE | /api/v1/follow-list/items/{item_id} | user | member |
| 8 | DELETE | /api/v1/follow-list | user | member |

## 類別 3：會員訂單、取消申請與拆單申請（orders.py，5 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 9 | POST | /api/v1/orders | user | member |
| 10 | GET | /api/v1/orders | user | member |
| 11 | GET | /api/v1/orders/{order_id} | user | member |
| 12 | POST | /api/v1/orders/{order_id}/cancellation-requests | user | member |
| 13 | POST | /api/v1/orders/{order_id}/unmerge-requests | user | member |

## 類別 4：團主申請（group_leader_applications.py，2 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 14 | POST | /api/v1/group-leader-applications | user | member |
| 15 | GET | /api/v1/group-leader-applications/me | user | member |

## 類別 5：團主後台（4 檔，34 端點）

### 5a. 團主資料與儀表板（group_leader_profile.py，4 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 16 | GET | /api/v1/group-leader/profile | glp | glp（鏈經 member） |
| 17 | PATCH | /api/v1/group-leader/profile | glp | glp（鏈經 member） |
| 18 | PATCH | /api/v1/group-leader/profile/default-rules | glp | glp（鏈經 member） |
| 19 | GET | /api/v1/group-leader/dashboard | aglp | aglp（鏈經 member） |

### 5b. 開團管理（group_leader_group_buys.py，10 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 20 | GET | /api/v1/group-leader/group-buys | aglp | aglp（鏈經 member） |
| 21 | GET | /api/v1/group-leader/group-buys/open | aglp | aglp（鏈經 member） |
| 22 | POST | /api/v1/group-leader/group-buys | aglp | aglp（鏈經 member） |
| 23 | GET | /api/v1/group-leader/group-buys/{group_buy_id} | aglp | aglp（鏈經 member） |
| 24 | GET | /api/v1/group-leader/group-buys/{group_buy_id}/product-orders | aglp | aglp（鏈經 member） |
| 25 | PATCH | /api/v1/group-leader/group-buys/{group_buy_id} | aglp | aglp（鏈經 member） |
| 26 | POST | /api/v1/group-leader/group-buys/{group_buy_id}/products | aglp | aglp（鏈經 member） |
| 27 | PATCH | /api/v1/group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id} | aglp | aglp（鏈經 member） |
| 28 | DELETE | /api/v1/group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id} | aglp | aglp（鏈經 member） |
| 29 | POST | /api/v1/group-leader/group-buys/{group_buy_id}/close | aglp | aglp（鏈經 member） |

### 5c. 團主訂單管理（group_leader_orders.py，14 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 30 | GET | /api/v1/group-leader/orders | aglp | aglp（鏈經 member） |
| 31 | GET | /api/v1/group-leader/orders/{order_id}/mergeable | aglp | aglp（鏈經 member） |
| 32 | POST | /api/v1/group-leader/orders/{order_id}/merge | aglp | aglp（鏈經 member） |
| 33 | GET | /api/v1/group-leader/orders/{order_id} | aglp | aglp（鏈經 member） |
| 34 | POST | /api/v1/group-leader/orders/{order_id}/accept | aglp | aglp（鏈經 member） |
| 35 | POST | /api/v1/group-leader/orders/{order_id}/reject | aglp | aglp（鏈經 member） |
| 36 | POST | /api/v1/group-leader/orders/{order_id}/mark-paid | aglp | aglp（鏈經 member） |
| 37 | POST | /api/v1/group-leader/group-buys/{group_buy_id}/orders/mark-all-shipped | aglp | aglp（鏈經 member） |
| 38 | POST | /api/v1/group-leader/orders/{order_id}/mark-shipped | aglp | aglp（鏈經 member） |
| 39 | POST | /api/v1/group-leader/orders/{order_id}/complete | aglp | aglp（鏈經 member） |
| 40 | POST | /api/v1/group-leader/cancellation-requests/{request_id}/approve | aglp | aglp（鏈經 member） |
| 41 | POST | /api/v1/group-leader/cancellation-requests/{request_id}/reject | aglp | aglp（鏈經 member） |
| 42 | POST | /api/v1/group-leader/unmerge-requests/{request_id}/approve | aglp | aglp（鏈經 member） |
| 43 | POST | /api/v1/group-leader/unmerge-requests/{request_id}/reject | aglp | aglp（鏈經 member） |

### 5d. 團主公告（group_leader_announcements.py，6 端點）

| # | Method | Path | 目前 | 預定 |
|---|---|---|---|---|
| 44 | GET | /api/v1/group-leader/announcements | aglp | aglp（鏈經 member） |
| 45 | GET | /api/v1/group-leader/announcements/recipient-preview | aglp | aglp（鏈經 member） |
| 46 | POST | /api/v1/group-leader/announcements | aglp | aglp（鏈經 member） |
| 47 | GET | /api/v1/group-leader/announcements/{announcement_id} | aglp | aglp（鏈經 member） |
| 48 | PATCH | /api/v1/group-leader/announcements/{announcement_id} | aglp | aglp（鏈經 member） |
| 49 | DELETE | /api/v1/group-leader/announcements/{announcement_id} | aglp | aglp（鏈經 member） |

## 明確不列入（維持現狀）

- `/api/v1/uploads`：管理後台上傳圖片必經之路，Admin 必須可用。
- `/api/v1/users/*`、`/api/v1/auth/*`：認證基礎能力，維持現狀。
- `/api/v1/notifications/*`：非 D-06 五類；現況 Admin 可呼叫，已記錄為待裁決差異（research.md〈盤點附帶發現〉）。
- 公開瀏覽與搜尋端點：不受限。
- `/api/v1/admin/*`：本來就要求 Admin。

## 前端 Route Guard 契約（FR-008）

受保護 Route（皆導向 `/admin`，不得短暫顯示內容）：

- MemberLayout：`/profile`、`/favorites`、`/notifications`、`/group-leader-application`、`/follow-list`、`/orders/confirm`、`/orders`、`/orders/:orderId`、`/orders/:orderId/cancel`
- GroupLeaderLayout：`/group-leader` 及其全部子路由（9 條）

未登入使用者仍導向 `/login`（既有行為）。
