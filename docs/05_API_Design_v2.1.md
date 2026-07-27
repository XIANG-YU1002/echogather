# 05_API_Design_v2.1

**Project Name:** WuWaGroup  
**Document Type:** API Design  
**API Style:** REST  
**Backend:** Python、FastAPI  
**Database:** PostgreSQL  
**Authentication:** JWT Bearer Access Token  
**Version:** 2.1  
**Last Updated:** 2026-07-18  

---

# Change Log

| Version | Date | Description |
|---|---|---|
| 1.0 | Initial Draft | 建立初始 API 規格 |
| 1.1 | Previous Version | 補充活動、商品、開團、訂單、公告與通知 API |
| 1.2 | Previous Version | 新增團主申請、會員聯絡方式、跟團清單、取消申請、特定開團公告及訂單拒絕原因 |
| 2.0 | 2026-07-18 | 配合 React + Vite 前端重新整理 API，統一 Response、Pagination、錯誤格式、權限及交易鎖定規格 |
| 2.1 | 2026-07-18 | 同步前四份 v2.1：移除帳號、團主及公告停用 API；調整團主申請、活動、角色、開團編輯、訂單排隊、取消申請、公告範圍、搜尋與開團比較規格 |

---

# Table of Contents

1. Document Purpose  
2. API Overview  
3. General Conventions  
4. Authentication and Authorization  
5. Response Format  
6. Error Format  
7. Pagination, Filtering and Sorting  
8. Image Upload API  
9. Authentication API  
10. Current User API  
11. Group Leader Application API  
12. Public Search API  
13. Public Activity API  
14. Public Product API  
15. Public Group Buy API  
16. Product Favorite API  
17. Follow List API  
18. Member Order API  
19. Cancellation Request API  
20. Notification API  
21. Public Group Leader API  
22. Group Leader Profile and Dashboard API  
23. Group Leader Group Buy API  
24. Group Leader Order API  
25. Group Leader Announcement API  
26. Administrator Dashboard API  
27. Admin Activity API  
28. Admin Product API  
29. Admin Character Support API  
30. Admin Group Leader Application API  
31. Admin Platform Announcement API  
32. Permission Matrix  
33. Transaction and Lock Requirements  
34. CORS and Frontend Integration  
35. Security Requirements  
36. HTTP Status Code Rules  
37. Error Code Reference  
38. Complete Endpoint Overview  
39. Final API Decisions

---

# 1. Document Purpose

本文件定義 WuWaGroup 第一版 FastAPI REST API。

本文件用途：

- 作為 FastAPI Router 建立依據
- 作為 Pydantic Request Schema 建立依據
- 作為 Pydantic Response Schema 建立依據
- 作為 React Service Layer 串接依據
- 定義 API Route、Method、Request、Response 與錯誤
- 定義 Visitor、Member、Group Leader 與 Administrator 權限
- 定義訂單與開團狀態操作
- 定義 Transaction 及 Row Lock 使用時機
- 統一 Pagination、日期、金額與錯誤格式
- 避免 React 前端自行推測後端規則

本文件不定義：

- 實際 Python Class 名稱
- SQLAlchemy 查詢完整程式碼
- 部署平台
- 前端 CSS
- React Component 細節

---

# 2. API Overview

## 2.1 Base URL

```text
/api/v1
```

完整範例：

```http
GET /api/v1/activities
```

---

## 2.2 Content Type

一般 API 使用：

```http
Content-Type: application/json
```

圖片上傳使用：

```http
Content-Type: multipart/form-data
```

---

## 2.3 Data Format

欄位名稱統一使用：

```text
snake_case
```

例如：

```json
{
  "group_buy_id": "uuid",
  "requires_second_payment": false,
  "deadline_at": "2026-08-10T15:00:00Z"
}
```

---

## 2.4 UUID

UUID 以字串回傳：

```json
{
  "id": "a8efbb25-126e-47e1-bbb1-812b36bb1290"
}
```

---

## 2.5 Datetime

時間使用 ISO 8601 UTC：

```text
2026-08-10T07:30:00Z
```

API 不直接回傳：

```text
2026/08/10 15:30
```

Asia/Taipei 顯示格式由 React 前端轉換。

---

## 2.6 Money

金額使用字串回傳，避免 JavaScript 浮點精度問題：

```json
{
  "unit_price": "390.00",
  "subtotal": "780.00",
  "product_total_amount": "1170.00"
}
```

Request 也建議使用字串：

```json
{
  "unit_price": "390.00"
}
```

Pydantic 解析為：

```text
Decimal
```

---

## 2.7 Boolean

Boolean 使用：

```json
true
false
```

不得使用：

```text
0
1
yes
no
```

---

## 2.8 Null

無資料時使用：

```json
null
```

不使用空字串代替沒有資料。

聯絡方式空字串由後端轉換為：

```text
null
```

---

# 3. General Conventions

## 3.1 Resource Naming

Route 使用複數名詞：

```text
/activities
/products
/orders
/notifications
```

單一目前使用者資源可使用：

```text
/users/me
/group-leader/profile
/follow-list
```

---

## 3.2 HTTP Method

| Method | Purpose |
|---|---|
| GET | 取得資料 |
| POST | 建立資源或執行明確狀態操作 |
| PATCH | 部分更新 |
| DELETE | 刪除允許刪除的資源、暫存資料或關聯 |

---

## 3.3 Status Actions

訂單狀態及活動、開團狀態不使用通用 `status` 欄位直接跳轉。

使用明確 Action Endpoint：

```http
POST /group-leader/orders/{id}/accept
POST /group-leader/orders/{id}/reject
POST /group-leader/orders/{id}/mark-paid
POST /group-leader/orders/{id}/mark-shipped
POST /group-leader/orders/{id}/complete

POST /admin/activities/{id}/end
POST /admin/activities/{id}/reopen
POST /group-leader/group-buys/{id}/close
```

商品上架狀態同樣使用：

```http
POST /admin/products/{id}/deactivate
POST /admin/products/{id}/reactivate
```

---

## 3.4 Controlled Delete

公告使用真正刪除，不使用停用狀態：

```http
DELETE /group-leader/announcements/{announcement_id}
DELETE /admin/announcements/{announcement_id}
```

刪除公告時只刪除該公告及其產生的通知，不影響其他系統通知。

---

## 3.5 Idempotency

下列操作應設計為 Idempotent：

- 收藏已收藏商品
- 取消不存在的收藏
- 通知標記已讀
- 全部通知標記已讀
- 清空不存在的跟團清單
- 商品重複上架或下架時回傳目前狀態，或以 409 明確提示狀態衝突

重複呼叫不得建立重複資料。

涉及訂單、申請及數量的敏感操作應回傳 Conflict，提示前端重新取得最新資料。

---

# 4. Authentication and Authorization

## 4.1 Authentication Method

使用：

```text
JWT Bearer Access Token
```

Header：

```http
Authorization: Bearer <access_token>
```

---

## 4.2 Access Token Storage

React 將 Token 保存於：

```text
sessionStorage
```

後端不管理前端儲存位置。

---

## 4.3 Token Lifetime

第一版 Access Token 有效時間：

```text
8 小時
```

第一版不提供 Refresh Token。

Token 過期後，前端導向登入頁並保留原始 `redirectPath`。登入成功後返回原頁；敏感操作不自動重新送出。

---

## 4.4 Token Claims

Access Token 至少包含：

```json
{
  "sub": "user_uuid",
  "exp": 1786388400
}
```

可包含 `role`，但受保護 API 不可只相信 Token 內角色，每次仍查詢資料庫。

---

## 4.5 Member Authentication

所有會員 API 必須確認：

```text
Access Token 有效
AND
app_user 存在
```


---

## 4.6 Group Leader Authentication

團主資料設定 API 必須確認：

```text
Access Token 有效
AND
目前使用者擁有 group_leader_profile
```

建立開團、管理訂單及發布公告等 API 還必須確認團主公開資料已完成：

```text
display_name 已設定
AND
至少一項公開聯絡方式已設定
```

---

## 4.7 Administrator Authentication

所有 `/admin/*` API 必須確認：

```text
Access Token 有效
AND
app_user.role = admin
```

管理員不會因 `role = admin` 自動取得團主功能。

---

## 4.8 Resource Ownership

後端必須驗證：

- 會員只能查看自己的訂單
- 會員只能修改自己的跟團清單
- 會員只能對自己的訂單提出取消申請
- 團主只能管理自己的開團
- 團主只能管理自己開團的訂單及取消申請
- 團主只能管理自己的公告
- 團主只能查看自己訂單中的會員聯絡快照

對非擁有者建議回傳 `404 Not Found`，避免透露資源是否存在。

---

# 5. Response Format

## 5.1 Single Resource

```json
{
  "data": {
    "id": "uuid",
    "name": "資料名稱"
  }
}
```

---

## 5.2 Resource List

```json
{
  "data": [
    {
      "id": "uuid",
      "name": "資料一"
    },
    {
      "id": "uuid",
      "name": "資料二"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 42,
    "total_pages": 3,
    "has_previous": false,
    "has_next": true
  }
}
```

---

## 5.3 Action Success

可回傳更新後的資源：

```json
{
  "data": {
    "id": "uuid",
    "status": "paid",
    "updated_at": "2026-08-10T07:30:00Z"
  }
}
```

不建議只回傳：

```json
{
  "success": true
}
```

除非操作沒有需要更新的資源內容。

---

## 5.4 Delete Success

可使用：

```http
204 No Content
```

例如：

```http
DELETE /api/v1/follow-list/items/{item_id}
```

---

# 6. Error Format

統一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "供使用者理解的訊息。",
    "details": null
  }
}
```

---

## 6.1 Field Validation Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "輸入資料格式不正確。",
    "details": {
      "fields": {
        "email": [
          "請輸入有效的 Email。"
        ],
        "discord_contact": [
          "至少需要提供一項聯絡方式。"
        ]
      }
    }
  }
}
```

---

## 6.2 Conflict Error

```json
{
  "error": {
    "code": "ORDER_STATUS_CONFLICT",
    "message": "訂單狀態已變更，請重新載入資料。",
    "details": {
      "current_status": "paid"
    }
  }
}
```

---

## 6.3 Quantity Error

```json
{
  "error": {
    "code": "INSUFFICIENT_AVAILABLE_QUANTITY",
    "message": "部分商品的可接受數量不足。",
    "details": {
      "items": [
        {
          "group_buy_product_id": "uuid",
          "requested_quantity": 3,
          "available_quantity": 1
        }
      ]
    }
  }
}
```

---

# 7. Pagination, Filtering and Sorting

## 7.1 Pagination Parameters

所有分頁列表統一使用：

```text
page
page_size
```

預設：

```text
page = 1
page_size = 20
```

最大：

```text
page_size = 100
```

---

## 7.2 Invalid Pagination

以下情況回傳 422：

```text
page < 1
page_size < 1
page_size > 100
```

---

## 7.3 Sorting

除非 Endpoint 另外說明，預設排序：

```text
created_at DESC
```

待處理申請可使用：

```text
created_at ASC
```

讓較早的申請優先顯示。

---

## 7.4 Filters

Query Parameter 未提供時，不套用該篩選。

範例：

```http
GET /api/v1/orders?status=paid&page=1&page_size=20
```

---

## 7.5 Invalid Enum Filter

傳入不存在的 Enum：

```http
GET /orders?status=unknown
```

回傳：

```http
422 Unprocessable Entity
```

---

# 8. Image Upload API

## 8.1 Upload Image

```http
POST /api/v1/uploads/images
```

權限：

```text
Member
```

但可使用的 Category 依角色限制。

Content Type：

```text
multipart/form-data
```

Form Data：

| Field | Type | Required | Description |
|---|---|---:|---|
| file | File | Yes | 圖片檔案 |
| category | String | Yes | avatar、activity 或 product |

---

## Category Permission

| Category | Permission |
|---|---|
| avatar | 已登入會員 |
| activity | 管理員 |
| product | 管理員 |

---

## Success Response

```http
201 Created
```

```json
{
  "data": {
    "url": "/uploads/avatar/2026/08/uuid.webp",
    "category": "avatar",
    "content_type": "image/webp",
    "size": 183245
  }
}
```

---

## Rules

後端必須驗證：

- Content Type
- 副檔名
- 實際檔案格式
- 檔案大小
- Category 權限
- 檔名不可直接使用使用者原始檔名
- 不得允許路徑穿越

圖片限制由 Business Rules 定義。

---

# 9. Authentication API

# 9.1 Register

```http
POST /api/v1/auth/register
```

權限：`Public`

Request：

```json
{
  "email": "member@example.com",
  "password": "ExamplePassword123",
  "password_confirmation": "ExamplePassword123",
  "nickname": "小游",
  "facebook_contact": null,
  "discord_contact": "member_name",
  "line_contact": "member_line"
}
```

## Validation

- Email 正規化為小寫並移除前後空白
- 密碼與確認密碼一致
- 暱稱不可為空
- 至少提供一項私人聯絡方式
- 空白聯絡方式轉為 `null`
- 頭像不必於註冊時提供；未上傳時由前端顯示預設頭像

## Success

```http
201 Created
```

```json
{
  "data": {
    "id": "uuid",
    "email": "member@example.com",
    "nickname": "小游",
    "avatar_url": null,
    "created_at": "2026-08-01T03:00:00Z"
  }
}
```

註冊成功後不自動登入，前端導向登入頁。

Errors：

```text
EMAIL_ALREADY_EXISTS
PASSWORD_CONFIRMATION_MISMATCH
CONTACT_REQUIRED
VALIDATION_ERROR
```

---

# 9.2 Login

```http
POST /api/v1/auth/login
```

權限：`Public`

Request：

```json
{
  "email": "member@example.com",
  "password": "ExamplePassword123"
}
```

Success：

```http
200 OK
```

```json
{
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "expires_in": 28800
  }
}
```

登入成功後呼叫：

```http
GET /api/v1/auth/me
```

若登入頁具有 `redirectPath`，驗證完成後返回該頁。

Invalid Credentials：

```http
401 Unauthorized
```

```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Email 或密碼錯誤。",
    "details": null
  }
}
```

不得透露 Email 是否存在、密碼哪一項錯誤或帳號角色。

---

# 9.3 Get Current Session

```http
GET /api/v1/auth/me
```

權限：`Member`

```json
{
  "data": {
    "id": "uuid",
    "email": "member@example.com",
    "nickname": "小游",
    "avatar_url": null,
    "role": "member",
    "group_leader": {
      "id": "uuid",
      "display_name": "月影團",
      "is_profile_complete": true
    },
    "permissions": {
      "is_admin": false,
      "has_group_leader_profile": true,
      "can_manage_group_buys": true
    }
  }
}
```

申請剛通過但資料未完成：

```json
{
  "group_leader": {
    "id": "uuid",
    "display_name": null,
    "is_profile_complete": false
  },
  "permissions": {
    "is_admin": false,
    "has_group_leader_profile": true,
    "can_manage_group_buys": false
  }
}
```

沒有團主資料時 `group_leader` 為 `null`。

---

## No Logout Endpoint

第一版不提供後端 Logout API。登出由 React 移除 `sessionStorage` Token 並清除 AuthContext。

---

# 10. Current User API

# 10.1 Get My Profile

```http
GET /api/v1/users/me
```

權限：`Member`

```json
{
  "data": {
    "id": "uuid",
    "email": "member@example.com",
    "nickname": "小游",
    "avatar_url": null,
    "facebook_contact": null,
    "discord_contact": "member_name",
    "line_contact": "member_line",
    "role": "member",
    "created_at": "2026-07-18T02:00:00Z",
    "latest_group_leader_application": {
      "id": "uuid",
      "status": "approved",
      "created_at": "2026-07-20T03:00:00Z",
      "reviewed_at": "2026-07-21T04:00:00Z"
    },
    "group_leader_profile": {
      "id": "uuid",
      "display_name": null,
      "is_profile_complete": false
    }
  }
}
```

Email 第一版只讀。

---

# 10.2 Update My Profile

```http
PATCH /api/v1/users/me
```

Request：

```json
{
  "nickname": "翔宇",
  "avatar_url": "/uploads/avatar/new-avatar.webp"
}
```

所有欄位皆為選填，但至少需傳入一個欄位。

不可修改：

- email
- role
- group leader fields

Success 回傳更新後的個人資料摘要。

---

# 10.3 Update My Contacts

```http
PATCH /api/v1/users/me/contacts
```

Request：

```json
{
  "facebook_contact": null,
  "discord_contact": "new_discord",
  "line_contact": "new_line"
}
```

空字串或純空白轉為 `null`，更新後至少保留一項私人聯絡方式。

Error：`CONTACT_REQUIRED`。

---

# 11. Group Leader Application API

## Application Eligibility

會員不可申請的情況：

- 已有待審核申請
- 已存在 `group_leader_profile`

申請被拒絕後，只要沒有待審核申請即可再次申請。

---

# 11.1 Submit Application

```http
POST /api/v1/group-leader-applications
```

權限：`Member`

Request Body：無。

第一版申請不要求申請原因、團主名稱或公開聯絡方式。

Success：

```http
201 Created
```

```json
{
  "data": {
    "id": "uuid",
    "status": "pending",
    "reviewed_at": null,
    "created_at": "2026-08-01T03:00:00Z"
  }
}
```

Errors：

```text
GROUP_LEADER_APPLICATION_PENDING
GROUP_LEADER_PROFILE_ALREADY_EXISTS
```

---

# 11.2 Get My Application

```http
GET /api/v1/group-leader-applications/me
```

回傳最新一筆申請：

```json
{
  "data": {
    "id": "uuid",
    "status": "rejected",
    "reviewed_at": "2026-08-03T04:00:00Z",
    "created_at": "2026-08-01T03:00:00Z",
    "can_reapply": true
  }
}
```

從未申請時：

```json
{
  "data": null
}
```

---

# 12. Public Search API

# 12.1 Global Search Preview

```http
GET /api/v1/search?q=今汐&limit_per_type=5
```

權限：`Public`

只搜尋：

- 活動名稱
- 商品名稱
- 角色名稱

不搜尋會員、團主、訂單、公告、團規或聯絡方式。

Response：

```json
{
  "data": {
    "activities": {
      "items": [
        {
          "id": "uuid",
          "name": "3.4 官方周邊",
          "image_url": "/uploads/activity/activity.webp",
          "status": "open"
        }
      ],
      "total_count": 1,
      "has_more": false
    },
    "products": {
      "items": [
        {
          "id": "uuid",
          "name": "今汐壓克力立牌",
          "primary_image_url": "/uploads/product/product.webp",
          "activity": {
            "id": "uuid",
            "name": "3.4 官方周邊"
          }
        }
      ],
      "total_count": 18,
      "has_more": true
    },
    "characters": {
      "items": [
        {
          "id": "uuid",
          "name": "今汐",
          "related_product_count": 8
        }
      ],
      "total_count": 1,
      "has_more": false
    }
  }
}
```

三種類型各自計算筆數，不共用一組 Pagination。

Trim 後空白回傳 `SEARCH_QUERY_REQUIRED`。

---

# 12.2 Search Activities

```http
GET /api/v1/search/activities?q=官方&page=1&page_size=20
```

---

# 12.3 Search Products

```http
GET /api/v1/search/products?q=今汐&page=1&page_size=20
GET /api/v1/search/products?character_id={character_id}&page=1&page_size=20
```

公開搜尋只回傳 `product.is_active = true`。

---

# 12.4 Search Characters

```http
GET /api/v1/search/characters?q=今&page=1&page_size=20
```

角色結果回傳 `related_product_count`。

---

# 13. Public Activity API

# 13.1 Get Activities

```http
GET /api/v1/activities
```

權限：`Public`

Query：

| Parameter | Description |
|---|---|
| status | `open` 或 `ended` |
| page | 頁碼 |
| page_size | 每頁數量 |

不使用固定活動分類。

首頁分別呼叫 `status=open` 與 `status=ended`，各區預設 `created_at DESC`。

Response Item：

```json
{
  "id": "uuid",
  "name": "3.4 官方周邊",
  "image_url": "/uploads/activity/activity.webp",
  "status": "open",
  "has_full_gift": true,
  "created_at": "2026-08-01T03:00:00Z"
}
```

---

# 13.2 Get Activity Detail

```http
GET /api/v1/activities/{activity_id}
```

```json
{
  "data": {
    "id": "uuid",
    "name": "3.4 官方周邊",
    "description": "官方 3.4 版本周邊。",
    "image_url": "/uploads/activity/activity.webp",
    "status": "open",
    "has_full_gift": true,
    "created_at": "2026-08-01T03:00:00Z",
    "updated_at": "2026-08-01T03:00:00Z"
  }
}
```

---

# 13.3 Get Activity Products

```http
GET /api/v1/activities/{activity_id}/products
```

只回傳 `product.is_active = true`。

活動頁商品卡片回傳圖片與名稱，不需要官方價格或角色標籤。

---

# 14. Public Product API

# 14.1 Get Product Detail

```http
GET /api/v1/products/{product_id}
```

權限：`Public`

```json
{
  "data": {
    "id": "uuid",
    "name": "壓克力立牌",
    "official_price": "390.00",
    "primary_image_url": "/uploads/product/product.webp",
    "is_active": true,
    "activity": {
      "id": "uuid",
      "name": "3.4 官方周邊",
      "status": "open",
      "has_full_gift": true
    },
    "images": [
      {
        "id": "uuid",
        "image_url": "/uploads/product/extra.webp",
        "sort_order": 0
      }
    ],
    "characters": [
      {"id": "uuid", "name": "今汐"},
      {"id": "uuid", "name": "長離"}
    ],
    "is_favorited": false
  }
}
```


商品已下架時不顯示於公開活動列表及搜尋；收藏頁仍可取得下架商品摘要。

---

# 14.2 Get Product Group Buys

```http
GET /api/v1/products/{product_id}/group-buys
```

Query：

| Parameter | Description |
|---|---|
| sort | `newest`、`price_asc`、`price_desc`、`deadline_asc`、`deadline_desc` |
| available_only | 是否只顯示目前可跟團 |
| payment_method | 依付款方式篩選：`bank_transfer`、`cash_on_delivery`；未帶則不篩選 |
| requires_second_payment | 是否需要二補 |
| includes_full_gift | 是否包含滿贈 |
| page | 頁碼 |
| page_size | 每頁數量 |

預設：

```text
sort = newest
```

即開團時間由新到舊。

Response Item：

```json
{
  "id": "group_buy_uuid",
  "group_buy_product_id": "group_buy_product_uuid",
  "group_leader": {
    "id": "group_leader_uuid",
    "display_name": "月影團"
  },
  "unit_price": "390.00",
  "payment_method": "cash_on_delivery",
  "payment_method_note": null,
  "requires_second_payment": false,
  "includes_full_gift": true,
  "deadline_at": "2026-08-10T15:00:00Z",
  "contact_platform": "discord",
  "effective_status": "open",
  "is_available": true,
  "available_quantity": 3,
  "created_at": "2026-08-01T03:00:00Z"
}
```

`available_quantity` 為查詢當下結果，不代表已保留；正式送單仍需重新驗證。

Effective Status：

```text
open
closed
expired
activity_ended
full
```

`effective_status` 為計算欄位，不保存於資料庫。

---

# 15. Public Group Buy API

# 15.1 Get Group Buy Detail

```http
GET /api/v1/group-buys/{group_buy_id}
```

權限：`Public`

Response 包含活動、團主、付款方式、團規、主要聯絡方式、商品與查詢當下剩餘數量。

```json
{
  "data": {
    "id": "uuid",
    "activity": {
      "id": "uuid",
      "name": "3.4 官方周邊",
      "status": "open"
    },
    "group_leader": {
      "id": "uuid",
      "display_name": "月影團"
    },
    "payment_method": "bank_transfer",
    "payment_method_note": "團費確認後再私訊告知匯款帳號",
    "requires_second_payment": false,
    "includes_full_gift": true,
    "deadline_at": "2026-08-10T15:00:00Z",
    "rules": "完整團規內容",
    "contact_platform": "discord",
    "contact_value": "moon_group",
    "status": "open",
    "effective_status": "open",
    "is_available": true,
    "products": [
      {
        "group_buy_product_id": "uuid",
        "product": {
          "id": "uuid",
          "name": "壓克力立牌",
          "primary_image_url": "/uploads/product/product.webp"
        },
        "unit_price": "390.00",
        "available_quantity": 3,
        "is_available": true
      }
    ],
    "created_at": "2026-08-01T03:00:00Z"
  }
}
```

---

# 15.2 Get Group Buy Rules

```http
GET /api/v1/group-buys/{group_buy_id}/rules
```

回傳完整團規及 `updated_at`。

---

# 15.3 Get Group Buy Public Announcements

```http
GET /api/v1/group-buys/{group_buy_id}/announcements
```

只回傳：

```text
announcement_type = group_leader
AND audience_scope = group_buy_unfinished
AND is_public = true
```

依 `published_at DESC` 排序。

---

# 15.4 Get Group Buy Product Availability

```http
GET /api/v1/group-buy-products/{group_buy_product_id}/availability
```

```json
{
  "data": {
    "group_buy_product_id": "uuid",
    "is_available": true,
    "available_quantity": 3,
    "effective_status": "open"
  }
}
```

精確數量仍可能因其他會員同時送單而改變。

---

# 16. Product Favorite API

# 16.1 Get Favorite Products

```http
GET /api/v1/favorites/products
```

權限：

```text
Member
```

Response：

```json
{
  "data": [
    {
      "favorite_id": "uuid",
      "product": {
        "id": "uuid",
        "name": "壓克力立牌",
        "primary_image_url": "/uploads/product/product.webp",
        "is_active": false,
        "activity": {
          "id": "uuid",
          "name": "3.4 官方周邊"
        }
      },
      "created_at": "2026-08-01T03:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_previous": false,
    "has_next": false
  }
}
```

下架商品仍可顯示於收藏列表。

---

# 16.2 Add Favorite

```http
POST /api/v1/favorites/products/{product_id}
```

權限：

```text
Member
```

Request Body：

```text
無
```

Success：

```http
201 Created
```

```json
{
  "data": {
    "product_id": "uuid",
    "is_favorited": true
  }
}
```

已收藏時可回傳 200：

```json
{
  "data": {
    "product_id": "uuid",
    "is_favorited": true
  }
}
```

不得建立重複資料。

---

# 16.3 Remove Favorite

```http
DELETE /api/v1/favorites/products/{product_id}
```

權限：

```text
Member
```

Success：

```http
204 No Content
```

未收藏時仍可回傳 204。

---

# 17. Follow List API

# 17.1 Get Follow List

```http
GET /api/v1/follow-list
```

權限：

```text
Member
```

Response：

```json
{
  "data": {
    "id": "uuid",
    "group_buy": {
      "id": "uuid",
      "group_leader": {
        "id": "uuid",
        "display_name": "月影團"
      },
      "activity": {
        "id": "uuid",
        "name": "3.4 官方周邊"
      },
      "payment_method": "bank_transfer",
      "payment_method_note": null,
      "requires_second_payment": false,
      "includes_full_gift": true,
      "deadline_at": "2026-08-10T15:00:00Z",
      "rules": "完整團規",
      "contact_platform": "discord",
      "contact_value": "moon_group",
      "effective_status": "open",
      "is_available": true
    },
    "items": [
      {
        "id": "uuid",
        "group_buy_product_id": "uuid",
        "product": {
          "id": "uuid",
          "name": "壓克力立牌",
          "primary_image_url": "/uploads/product/product.webp"
        },
        "unit_price": "390.00",
        "quantity": 2,
        "estimated_subtotal": "780.00",
        "is_available": true
      }
    ],
    "estimated_product_total": "780.00",
    "is_submittable": true,
    "invalid_reasons": [],
    "created_at": "2026-08-01T03:00:00Z",
    "updated_at": "2026-08-01T03:00:00Z"
  }
}
```

沒有清單：

```json
{
  "data": null
}
```

---

# 17.2 Add Follow List Item

```http
POST /api/v1/follow-list/items
```

權限：

```text
Member
```

Request：

```json
{
  "group_buy_product_id": "uuid",
  "quantity": 2,
  "replace_existing": false
}
```

---

## Same Group Buy

若目前清單屬於相同開團：

- 新商品：建立項目
- 相同商品：增加原數量

例如原數量為 2，新加入 3：

```text
新數量 = 5
```

---

## Different Group Buy

`replace_existing = false`：

```http
409 Conflict
```

```json
{
  "error": {
    "code": "FOLLOW_LIST_GROUP_BUY_CONFLICT",
    "message": "目前跟團清單屬於其他開團。",
    "details": {
      "current_group_buy_id": "uuid",
      "requested_group_buy_id": "uuid"
    }
  }
}
```

React 顯示替換確認 Modal。

---

## Replace Existing

確認後重新呼叫：

```json
{
  "group_buy_product_id": "uuid",
  "quantity": 2,
  "replace_existing": true
}
```

後端必須在同一 Transaction 中：

```text
刪除舊清單
建立新清單
建立新項目
```

不得先讓前端分開刪除再建立，以免建立失敗後遺失原清單。

---

## Success

```http
201 Created
```

回傳更新後完整跟團清單。

---

# 17.3 Update Item Quantity

```http
PATCH /api/v1/follow-list/items/{item_id}
```

權限：

```text
Member
```

Request：

```json
{
  "quantity": 3
}
```

此 Endpoint 使用絕對數量，不是增加量。

Response：

```json
{
  "data": {
    "id": "uuid",
    "quantity": 3,
    "unit_price": "390.00",
    "estimated_subtotal": "1170.00",
    "estimated_product_total": "1170.00"
  }
}
```

---

# 17.4 Remove Item

```http
DELETE /api/v1/follow-list/items/{item_id}
```

權限：

```text
Member
```

刪除最後一項時，同時刪除：

```text
follow_list
```

Success：

```http
204 No Content
```

---

# 17.5 Clear Follow List

```http
DELETE /api/v1/follow-list
```

權限：

```text
Member
```

Success：

```http
204 No Content
```

沒有清單時仍可回傳 204。

---

## Invalid Follow List Retention

當開團已結單、截止、活動結束、商品下架或數量不足時，既有跟團清單不自動刪除。

`GET /follow-list` 回傳：

```json
{
  "is_submittable": false,
  "invalid_reasons": ["GROUP_BUY_NOT_AVAILABLE"]
}
```

會員仍可修改、移除項目或清空清單；不可正式送出。

---

## Follow List Errors

```text
GROUP_BUY_NOT_AVAILABLE
GROUP_BUY_PRODUCT_NOT_FOUND
FOLLOW_LIST_GROUP_BUY_CONFLICT
INVALID_QUANTITY
INSUFFICIENT_AVAILABLE_QUANTITY
```

跟團清單數量檢查只代表當下可接受，不保留數量。

---

# 18. Member Order API

# 18.1 Create Order

```http
POST /api/v1/orders
```

權限：`Member`

Request：

```json
{
  "rules_accepted": true
}
```

前端不得提交商品價格、小計、商品總額、名稱、圖片或任何快照。

後端從目前 `follow_list` 重新查詢及計算。

## Transaction

```text
1. 鎖定跟團清單
2. 鎖定開團
3. 依 UUID 固定順序鎖定所有 group_buy_product
4. 驗證開團仍可接受訂單
5. 重新計算占用與剩餘數量
6. 重新取得商品價格
7. 計算 subtotal 與 product_total_amount
8. 建立全新 group_order
9. 建立所有 order_item 與快照
10. 清除跟團清單
11. Commit
```

同一會員對同一開團再次送單時，必須建立第二張獨立訂單，不得與先前訂單合併。

排序及先喊順序：

```text
created_at ASC, id ASC
```

Success：

```http
201 Created
```

```json
{
  "data": {
    "id": "uuid",
    "order_number": "WG260801-000001",
    "status": "pending_confirmation",
    "product_total_amount": "1170.00",
    "created_at": "2026-08-01T03:00:00Z"
  }
}
```

Failure：

- 不建立部分訂單
- 跟團清單完整保留
- 回傳最新可接受數量

Errors：

```text
FOLLOW_LIST_EMPTY
RULES_NOT_ACCEPTED
GROUP_BUY_NOT_AVAILABLE
INSUFFICIENT_AVAILABLE_QUANTITY
ORDER_CREATION_CONFLICT
```

---

# 18.2 Get My Orders

```http
GET /api/v1/orders
```

Query：

| Parameter | Description |
|---|---|
| status | 訂單狀態；未帶則不篩選 |
| activity_name | 活動名稱快照的部分比對（不分大小寫），最長 150 字 |
| group_leader_name | 團主名稱快照的部分比對（不分大小寫），最長 50 字 |
| created_within_days | 只顯示近 N 天內建立的訂單，1～365；未帶則不限時間 |
| page | 頁碼 |
| page_size | 每頁數量 |

預設 `created_at DESC`。

Response Item：

```json
{
  "id": "uuid",
  "order_number": "WG260801-000001",
  "group_leader_name": "月影團",
  "activity_name": "3.4 官方周邊",
  "representative_image_url": "https://<project-ref>.supabase.co/storage/v1/object/public/media/product/2026/08/product.webp",
  "item_summary": "壓克力立牌等 2 項",
  "item_count": 2,
  "product_total_amount": "1170.00",
  "status": "pending_confirmation",
  "rejection_reason": null,
  "created_at": "2026-08-01T03:00:00Z"
}
```

代表圖片使用第一筆訂單明細圖片。

`item_count` 為訂單明細筆數（圖 07 的「N 項商品」）。
`rejection_reason` 僅在 `status = rejected` 時有值，供列表顯示「查看原因」入口。

---

# 18.3 Get My Order Detail

```http
GET /api/v1/orders/{order_id}
```

權限：`Order Owner`

Response 包含：

- 訂單狀態
- 不可修改的拒絕原因
- 商品總額
- 團主、活動、付款方式、團規及聯絡快照
- 下單當時的會員聯絡方式快照
- 收單期限（取自開團即時值）
- 商品明細
- 狀態異動歷史
- 所有取消申請歷史
- 目前待處理取消申請

```json
{
  "data": {
    "id": "uuid",
    "order_number": "WG260801-000001",
    "status": "pending_payment",
    "rejection_reason": null,
    "product_total_amount": "1170.00",
    "group_leader_id": "uuid",
    "group_leader_name": "月影團",
    "activity_name": "3.4 官方周邊",
    "payment_method": "bank_transfer",
    "payment_method_note": "團費確認後再私訊告知匯款帳號",
    "requires_second_payment": false,
    "includes_full_gift": true,
    "rules": "下單時完整團規",
    "contact_platform": "discord",
    "contact_value": "moon_group",
    "deadline_at": "2026-08-10T15:59:00Z",
    "member_facebook_contact": null,
    "member_discord_contact": "member_discord",
    "member_line_contact": "@member_line",
    "items": [],
    "status_history": [
      {
        "status": "pending_confirmation",
        "note": null,
        "created_at": "2026-08-01T03:00:00Z"
      },
      {
        "status": "pending_payment",
        "note": null,
        "created_at": "2026-08-01T05:00:00Z"
      }
    ],
    "pending_cancellation_request": null,
    "cancellation_requests": [],
    "created_at": "2026-08-01T03:00:00Z",
    "updated_at": "2026-08-01T05:00:00Z"
  }
}
```

`group_leader_id` 供前端連往團主公開頁。

`deadline_at` 取自開團本體（`group_buy.deadline_at`），**非下單當時快照**；
依使用者決議採即時值，團主延期後訂單頁會一併更新。

`member_*_contact` 為下單當時保存的聯絡方式快照，後續修改個人資料不影響本訂單。

`status_history` 依 `created_at` 由舊到新排序，訂單建立時即寫入第一筆
`pending_confirmation`；`note` 於拒絕時存拒絕原因、取消核准時存團主回覆。

商品總額不包含二補、國際運費、國內運費及其他後續費用。

其他會員存取回傳 `404 Not Found`。

---

# 19. Cancellation Request API

# 19.1 Create Cancellation Request

```http
POST /api/v1/orders/{order_id}/cancellation-requests
```

權限：`Order Owner`

Request：

```json
{
  "reason": "臨時無法完成付款。"
}
```

`reason` 選填；空白字串轉為 `null`。

同一訂單同時最多一筆 `pending` 取消申請。先前申請被拒絕後，只要訂單仍符合取消條件即可再次提出。

不可對 `completed`、`cancelled`、`rejected` 訂單建立。

Success：

```http
201 Created
```

```json
{
  "data": {
    "id": "uuid",
    "order_id": "uuid",
    "reason": "臨時無法完成付款。",
    "status": "pending",
    "response_note": null,
    "processed_at": null,
    "created_at": "2026-08-04T03:00:00Z"
  }
}
```

建立申請時訂單狀態保持原狀。

Errors：

```text
CANCELLATION_NOT_ALLOWED
CANCELLATION_REQUEST_PENDING
ORDER_NOT_FOUND
```

---

# 20. Notification API

# 20.1 Get Notifications

```http
GET /api/v1/notifications
```

Query：`notification_type`、`is_read`、`page`、`page_size`。

Response Item：

```json
{
  "id": "uuid",
  "notification_type": "group_leader",
  "title": "官方出貨時間調整",
  "message": "官方出貨時間延後至九月。",
  "is_read": false,
  "read_at": null,
  "source": {
    "type": "announcement",
    "id": "uuid"
  },
  "target_url": "/group-leaders/group_leader_uuid",
  "actor_name": "月影團",
  "actor_avatar_url": "https://<project-ref>.supabase.co/storage/v1/object/public/media/avatar/2026/08/xxx.webp",
  "created_at": "2026-08-05T03:00:00Z"
}
```

點擊通知時由 `target_url` 導向相關訂單、團主頁、開團頁或團主申請結果。

`actor_name` / `actor_avatar_url` 為**團主公告**的發布團主名稱與頭像（依圖 10 於通知
列表顯示團主頭像）。平台公告與系統通知皆為 `null`。

訂單通知的 `target_url` 會依收件人判斷：收件人為下單會員時導向 `/orders/{id}`，
收件人為該團團主時導向 `/group-leader/orders/{id}`。

團主公告導向規則：

- 公開的團主整體公告：團主公開頁
- 公開的特定開團公告：開團公開頁
- 不公開公告：通知中心中的該則通知，由通知 `message` 顯示完整內容
- 平台公告：通知中心中的該則通知

---

# 20.2 Get Unread Count

```http
GET /api/v1/notifications/unread-count
```

供 Header 鈴鐺顯示紅點數量。

---

# 20.2b Get Notification Summary

```http
GET /api/v1/notifications/summary
```

供圖 10 通知中心右側「通知摘要」卡使用。

```json
{
  "data": {
    "unread_count": 3,
    "system_count": 3,
    "group_leader_count": 3
  }
}
```

`unread_count` 為未讀總數；`system_count` 與 `group_leader_count` 為該類型的
**總筆數（含已讀）**，依使用者決議採此定義。

---

# 20.3 Mark Notification Read

```http
PATCH /api/v1/notifications/{notification_id}/read
```

重複呼叫時保持原 `read_at`。

---

# 20.4 Mark All Notifications Read

```http
PATCH /api/v1/notifications/read-all
```

第一版不提供會員刪除通知 API。公告被刪除時，該公告產生的通知由後端一併刪除。

---

# 21. Public Group Leader API

# 21.1 Get Public Group Leader Profile

```http
GET /api/v1/group-leaders/{group_leader_id}
```

權限：`Public`

只有公開資料完成的團主可以取得。

```json
{
  "data": {
    "id": "uuid",
    "display_name": "月影團",
    "avatar_url": null,
    "introduction": "主要協助官方周邊開團。",
    "public_contacts": {
      "facebook": null,
      "discord": "moon_group",
      "line": "moon_line"
    },
    "created_at": "2026-07-20T03:00:00Z",
    "statistics": {
      "group_buy_count": 8,
      "completed_order_count": 46
    },
    "default_rules": "公開顯示的預設團規內容"
  }
}
```

團主名稱設定完成後不可修改。

公開 API 不回傳會員私人聯絡方式。

---

# 21.2 Get Public Group Leader Group Buys

```http
GET /api/v1/group-leaders/{group_leader_id}/group-buys
```

Query：`status`、`page`、`page_size`。

---

# 21.3 Get Public Group Leader Announcements

```http
GET /api/v1/group-leaders/{group_leader_id}/announcements
```

只回傳：

```text
announcement_type = group_leader
AND audience_scope = leader_unfinished
AND is_public = true
```

依 `published_at DESC` 排序。

---

# 22. Group Leader Profile and Dashboard API

# 22.1 Get Group Leader Profile

```http
GET /api/v1/group-leader/profile
```

權限：`Group Leader Profile Owner`

申請通過後，即使資料尚未完成也可取得。

```json
{
  "data": {
    "id": "uuid",
    "display_name": null,
    "introduction": null,
    "default_rules": null,
    "facebook_url": null,
    "discord_contact": null,
    "line_contact": null,
    "is_profile_complete": false,
    "created_at": "2026-07-20T03:00:00Z",
    "updated_at": "2026-07-20T03:00:00Z"
  }
}
```

---

# 22.2 Update Group Leader Profile

```http
PATCH /api/v1/group-leader/profile
```

第一次完成資料時：

```json
{
  "display_name": "月影團",
  "introduction": "主要協助官方周邊開團。",
  "facebook_url": null,
  "discord_contact": "moon_group",
  "line_contact": null
}
```

規則：

- `display_name` 尚未設定時必填
- 名稱設定後不可修改
- 至少保留一項公開聯絡方式
- 會員私人聯絡方式不自動複製

Errors：

```text
GROUP_LEADER_DISPLAY_NAME_UNAVAILABLE
GROUP_LEADER_DISPLAY_NAME_IMMUTABLE
CONTACT_REQUIRED
```

---

# 22.3 Update Default Rules

```http
PATCH /api/v1/group-leader/profile/default-rules
```

更新預設團規不影響既有開團。

---

# 22.4 Get Group Leader Dashboard

```http
GET /api/v1/group-leader/dashboard
```

權限：`Completed Group Leader Profile`

只回傳簡化統計與可點擊篩選條件：

```json
{
  "data": {
    "cards": [
      {
        "key": "open_group_buys",
        "label": "進行中開團",
        "count": 2,
        "target_url": "/group-leader/group-buys?status=open"
      },
      {
        "key": "pending_confirmation_orders",
        "label": "待確認訂單",
        "count": 4,
        "target_url": "/group-leader/orders?status=pending_confirmation"
      },
      {
        "key": "pending_payment_orders",
        "label": "待付款訂單",
        "count": 3,
        "target_url": "/group-leader/orders?status=pending_payment"
      },
      {
        "key": "pending_cancellation_requests",
        "label": "待處理取消申請",
        "count": 1,
        "target_url": "/group-leader/orders?has_pending_cancellation=true"
      }
    ]
  }
}
```

第一版 Dashboard 不回傳最近公告或複雜圖表。

---

# 23. Group Leader Group Buy API

# 23.1 Get My Group Buys

```http
GET /api/v1/group-leader/group-buys
```

Query：`status`、`page`、`page_size`。

---

# 23.2 Create Group Buy

```http
POST /api/v1/group-leader/group-buys
```

權限：`Completed Group Leader Profile`

前端流程先選擇一項 `open` 活動，再載入該活動可用商品。

Request：

```json
{
  "activity_id": "uuid",
  "products": [
    {
      "product_id": "uuid",
      "unit_price": "390.00",
      "max_quantity": 20
    }
  ],
  "payment_method": "bank_transfer",
  "payment_method_note": "團費確認後再私訊告知匯款帳號",
  "requires_second_payment": false,
  "includes_full_gift": true,
  "deadline_at": "2026-08-10T15:00:00Z",
  "rules": "本次完整團規。",
  "contact_platform": "discord",
  "contact_value": "moon_group"
}
```

Validation：

- 團主公開資料已完成
- 至少一項且不重複的商品
- 商品均屬於指定活動且為 active
- 活動為 open
- 截止時間晚於現在
- 滿贈設定符合活動
- 商品售價固定以 TWD
- `payment_method` 僅接受 `bank_transfer` 或 `cash_on_delivery`
- `payment_method_note` 為選填，任何付款方式皆可填寫；空白字串一律正規化為 `null`
- 同一團主對同一活動已有進行中的開團時，回 409 `GROUP_BUY_ALREADY_OPEN_FOR_ACTIVITY`

任一步失敗不得建立部分開團商品。

---

# 23.3 Get My Group Buy Detail

```http
GET /api/v1/group-leader/group-buys/{group_buy_id}
```

回傳完整設定、商品、`max_quantity`、`occupied_quantity`、`available_quantity`、正式訂單數及：

```json
{
  "has_orders": true,
  "editable_fields": [
    "deadline_at",
    "contact_platform",
    "contact_value",
    "max_quantity"
  ]
}
```

---

# 23.4 Update Group Buy Settings

```http
PATCH /api/v1/group-leader/group-buys/{group_buy_id}
```

沒有任何正式訂單時可修改：

- payment_method
- payment_method_note
- requires_second_payment
- includes_full_gift
- deadline_at
- rules
- contact_platform
- contact_value

已有正式訂單後只可修改：

- deadline_at
- contact_platform
- contact_value

違反凍結規則回傳 `GROUP_BUY_FIELDS_FROZEN`。

---

# 23.5 Add Group Buy Product

```http
POST /api/v1/group-leader/group-buys/{group_buy_id}/products
```

只允許開團尚無任何正式訂單時使用。

---

# 23.6 Update Group Buy Product

```http
PATCH /api/v1/group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id}
```

沒有正式訂單時可修改 `unit_price` 與 `max_quantity`。

已有正式訂單後只可修改 `max_quantity`，且：

```text
new_max_quantity >= occupied_quantity
```

---

# 23.7 Remove Group Buy Product

```http
DELETE /api/v1/group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id}
```

只允許無正式訂單時使用，並須確保開團仍至少保留一項商品，且沒有相關跟團清單項目。

---

# 23.8 Close Group Buy

```http
POST /api/v1/group-leader/group-buys/{group_buy_id}/close
```

第一版開團提前結單後不可重新開啟。

---

# 24. Group Leader Order API

# 24.1 Get Group Leader Orders

```http
GET /api/v1/group-leader/orders
```

Query：

| Parameter | Description |
|---|---|
| group_buy_id | 篩選開團 |
| activity_id | 篩選活動 |
| status | 訂單狀態 |
| has_pending_cancellation | 是否有待處理取消申請 |
| keyword | 訂單編號或會員暱稱 |
| page | 頁碼 |
| page_size | 每頁數量 |

預設排序：

```text
created_at ASC, id ASC
```

團主最早收到的訂單排在前面，以符合先喊先得。第二次加喊的獨立訂單必定排在原訂單後面。

---

# 24.2 Get Group Leader Order Detail

```http
GET /api/v1/group-leader/orders/{order_id}
```

回傳會員暱稱、下單時聯絡快照、商品總額、明細、取消申請歷史及 `available_actions`。

---

# 24.3 Accept Order

```http
POST /api/v1/group-leader/orders/{order_id}/accept
```

只允許 `pending_confirmation → pending_payment`。

---

# 24.4 Reject Order

```http
POST /api/v1/group-leader/orders/{order_id}/reject
```

Request：

```json
{
  "reason": "本次可接受數量不足。"
}
```

`reason` 必填且 Trim 後不可為空。

只允許 `pending_confirmation → rejected`。完成後拒絕原因不可修改，訂單不可恢復。

---

# 24.5 Mark Paid

```http
POST /api/v1/group-leader/orders/{order_id}/mark-paid
```

`pending_payment → paid`。

---

# 24.6 Mark Shipped

```http
POST /api/v1/group-leader/orders/{order_id}/mark-shipped
```

`paid → shipped`。

---

# 24.7 Complete Order

```http
POST /api/v1/group-leader/orders/{order_id}/complete
```

`shipped → completed`。

---

# 24.8 Approve Cancellation

```http
POST /api/v1/group-leader/cancellation-requests/{request_id}/approve
```

`response_note` 選填。成功後取消申請為 `approved`，訂單為 `cancelled`。

---

# 24.9 Reject Cancellation

```http
POST /api/v1/group-leader/cancellation-requests/{request_id}/reject
```

`response_note` 選填。成功後申請為 `rejected`，訂單狀態維持原狀；會員之後可重新申請。

Order Action Errors：

```text
ORDER_NOT_FOUND
ORDER_STATUS_CONFLICT
ORDER_NOT_OWNED_BY_GROUP_LEADER
ORDER_REJECTION_REASON_REQUIRED
CANCELLATION_REQUEST_NOT_FOUND
CANCELLATION_REQUEST_ALREADY_PROCESSED
CANCELLATION_NOT_ALLOWED
```

---

# 25. Group Leader Announcement API

# 25.1 Get My Announcements

```http
GET /api/v1/group-leader/announcements
```

Query：`audience_scope`、`group_buy_id`、`is_public`、`page`、`page_size`。

---

# 25.2 Create Announcement

```http
POST /api/v1/group-leader/announcements
```

權限：`Completed Group Leader Profile`

團主整體公告：

```json
{
  "audience_scope": "leader_unfinished",
  "group_buy_id": null,
  "title": "近期團務說明",
  "content": "完整公告內容。",
  "is_public": true
}
```

特定開團公告：

```json
{
  "audience_scope": "group_buy_unfinished",
  "group_buy_id": "uuid",
  "title": "出貨時間調整",
  "content": "官方出貨時間延後至九月。",
  "is_public": false
}
```

通知對象只包含至少有一筆未完成訂單的 distinct `user_id`：

```text
pending_confirmation
pending_payment
paid
shipped
```

不包含 `completed`、`cancelled`、`rejected`。

零通知對象：

- `is_public = true`：允許發布
- `is_public = false`：回傳 `ANNOUNCEMENT_NO_RECIPIENTS`

---

# 25.3 Get My Announcement Detail

```http
GET /api/v1/group-leader/announcements/{announcement_id}
```

權限：`Announcement Owner`。

---

# 25.4 Update Announcement

```http
PATCH /api/v1/group-leader/announcements/{announcement_id}
```

可修改：`title`、`content`、`is_public`。

不可修改：`audience_scope`、`group_buy_id`、`published_at`。

修改後：

- 更新公告
- 同步更新該公告既有通知的 title 與 message
- 不建立第二批通知

---

# 25.5 Delete Announcement

```http
DELETE /api/v1/group-leader/announcements/{announcement_id}
```

Success：`204 No Content`。

刪除公告時一併刪除該公告產生的通知，不影響其他通知。

---

# 26. Administrator Dashboard API

# 26.1 Get Admin Dashboard

```http
GET /api/v1/admin/dashboard
```

權限：`Administrator`

```json
{
  "data": {
    "cards": [
      {
        "key": "pending_group_leader_applications",
        "label": "待審核團主申請",
        "count": 3,
        "target_url": "/admin/group-leader-applications?status=pending"
      },
      {
        "key": "open_activities",
        "label": "目前活動",
        "count": 5,
        "target_url": "/admin/activities?status=open"
      },
      {
        "key": "active_products",
        "label": "上架商品",
        "count": 86,
        "target_url": "/admin/products?is_active=true"
      },
      {
        "key": "current_group_buys",
        "label": "目前開團",
        "count": 12,
        "target_url": "/admin?view=current-group-buys"
      }
    ]
  }
}
```

第一版不提供圖表或會員、團主停用統計。

---

# 26.2 Get Current Group Buys

```http
GET /api/v1/admin/dashboard/current-group-buys
```

此 Endpoint 只供 Dashboard 展開唯讀清單，不提供管理操作。

Query：`page`、`page_size`。

「目前開團」需同時符合：

```text
group_buy.status = open
AND deadline_at > current_time
AND activity.status = open
```

Response Item：

```json
{
  "id": "uuid",
  "activity_name": "3.4 官方周邊",
  "group_leader_name": "月影團",
  "deadline_at": "2026-08-10T15:00:00Z",
  "order_count": 12,
  "created_at": "2026-08-01T03:00:00Z"
}
```

---

# 27. Admin Activity API

# 27.1 Get Activities

```http
GET /api/v1/admin/activities
```

Query：`status`、`keyword`、`page`、`page_size`。


---

# 27.2 Create Activity

```http
POST /api/v1/admin/activities
```

```json
{
  "name": "3.4 官方周邊",
  "description": "官方周邊活動。",
  "image_url": "/uploads/activity/activity.webp",
  "has_full_gift": true
}
```

初始狀態為 `open`。新增後首頁目前活動區自動出現該活動。

---

# 27.3 Get Activity Detail

```http
GET /api/v1/admin/activities/{activity_id}
```

額外回傳 `product_count` 與 `group_buy_count`。

---

# 27.4 Update Activity

```http
PATCH /api/v1/admin/activities/{activity_id}
```

可修改名稱、說明、圖片及滿贈設定；狀態使用明確 Action Endpoint。

---

# 27.5 End Activity

```http
POST /api/v1/admin/activities/{activity_id}/end
```

更新為 `ended`。

---

# 27.6 Reopen Activity

```http
POST /api/v1/admin/activities/{activity_id}/reopen
```

將誤結束的活動重新設為 `open`。

重新開啟活動不會重新開啟已提前結單的開團，也不會延長已過期開團的截止時間。

---

# 28. Admin Product API

# 28.1 Get Products

```http
GET /api/v1/admin/products
```

Query：`activity_id`、`is_active`、`character_id`、`keyword`、`page`、`page_size`。

---

# 28.2 Create Product

```http
POST /api/v1/admin/products
```

角色欄位支援同時選擇既有角色或明確建立新角色：

```json
{
  "activity_id": "uuid",
  "name": "壓克力立牌",
  "official_price": "390.00",
  "primary_image_url": "/uploads/product/product.webp",
  "characters": [
    {"id": "existing_character_uuid"},
    {"new_name": "今汐"}
  ]
}
```

每筆角色選擇必須只提供 `id` 或 `new_name` 其中一項。

後端在同一 Transaction 中：

- 驗證既有角色
- 正規化新角色名稱
- 防止大小寫不敏感重複名稱
- 建立新角色及商品關聯
- 建立商品

商品價格固定為 TWD，不接受幣別欄位。

---

# 28.3 Get Product Detail

```http
GET /api/v1/admin/products/{product_id}
```

回傳完整商品、活動、額外圖片、關聯角色、開團關聯數及收藏數。

---

# 28.4 Update Product

```http
PATCH /api/v1/admin/products/{product_id}
```

可使用與建立相同的 `characters` 結構更新角色關聯，整筆操作使用 Transaction。

---

# 28.5 Deactivate Product

```http
POST /api/v1/admin/products/{product_id}/deactivate
```

不刪除收藏、歷史開團、訂單或圖片。

---

# 28.6 Reactivate Product

```http
POST /api/v1/admin/products/{product_id}/reactivate
```

---

# 28.7 Add Extra Image

```http
POST /api/v1/admin/products/{product_id}/images
```

新增後預設放在最後。

---

# 28.8 Update Extra Image

```http
PATCH /api/v1/admin/products/{product_id}/images/{image_id}
```

只修改圖片 URL。

---

# 28.9 Reorder Extra Images

```http
PATCH /api/v1/admin/products/{product_id}/images/reorder
```

Request：

```json
{
  "ordered_image_ids": [
    "image_uuid_2",
    "image_uuid_1"
  ]
}
```

前端的上移／下移按鈕更新陣列順序，後端重新寫入連續 `sort_order`。

---

# 28.10 Delete Extra Image

```http
DELETE /api/v1/admin/products/{product_id}/images/{image_id}
```

主要圖片不可透過此 Endpoint 刪除。

---

# 29. Admin Character Support API

第一版不建立獨立角色管理頁。本組 API 供商品表單的角色搜尋、新增及精簡維護 Modal 使用。

# 29.1 Get Character Suggestions

```http
GET /api/v1/admin/characters/suggestions?q=今&limit=10
```

回傳部分名稱符合的角色：

```json
{
  "data": [
    {
      "id": "uuid",
      "name": "今汐",
      "related_product_count": 12
    }
  ]
}
```

第一版不提供角色列表的分頁管理頁。

---

# 29.2 Create Character

```http
POST /api/v1/admin/characters
```

```json
{
  "name": "今汐"
}
```

重複名稱回傳 `CHARACTER_NAME_ALREADY_EXISTS`。

---

# 29.3 Update Character

```http
PATCH /api/v1/admin/characters/{character_id}
```

供修正錯字。新名稱不得與其他角色重複。

---

# 29.4 Delete Character

```http
DELETE /api/v1/admin/characters/{character_id}
```

只有 `related_product_count = 0` 時可刪除；否則回傳 `CHARACTER_HAS_PRODUCT_RELATIONS`.

---

# 30. Admin Group Leader Application API

# 30.1 Get Applications

```http
GET /api/v1/admin/group-leader-applications
```

Query：`status`、`keyword`、`page`、`page_size`。

待審核預設 `created_at ASC`。

---

# 30.2 Get Application Detail

```http
GET /api/v1/admin/group-leader-applications/{application_id}
```

```json
{
  "data": {
    "id": "uuid",
    "user": {
      "id": "uuid",
      "email": "member@example.com",
      "nickname": "小游"
    },
    "status": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "created_at": "2026-08-01T03:00:00Z"
  }
}
```

第一版申請沒有申請說明、預定團主名稱、公開聯絡方式或審核備註。

---

# 30.3 Approve Application

```http
POST /api/v1/admin/group-leader-applications/{application_id}/approve
```

Request Body：無。

後端確認：

- 申請仍為 pending
- 會員尚無 `group_leader_profile`

Success：

```json
{
  "data": {
    "application": {
      "id": "uuid",
      "status": "approved",
      "reviewed_at": "2026-08-03T03:00:00Z"
    },
    "group_leader_profile": {
      "id": "uuid",
      "display_name": null,
      "is_profile_complete": false
    }
  }
}
```

不從會員私人資料複製公開名稱或聯絡方式。

---

# 30.4 Reject Application

```http
POST /api/v1/admin/group-leader-applications/{application_id}/reject
```

Request Body：無。

拒絕後會員可以再次申請。

Review Errors：

```text
APPLICATION_ALREADY_REVIEWED
GROUP_LEADER_PROFILE_ALREADY_EXISTS
```

---

# 31. Admin Platform Announcement API

# 31.1 Get Platform Announcements

```http
GET /api/v1/admin/announcements
```

Query：`keyword`、`page`、`page_size`。

只管理 `announcement_type = platform`。

---

# 31.2 Create Platform Announcement

```http
POST /api/v1/admin/announcements
```

```json
{
  "title": "平台維護通知",
  "content": "平台將於週日進行維護。"
}
```

通知所有已註冊會員。平台公告不建立獨立公開列表或公開詳情頁。

---

# 31.3 Get Platform Announcement Detail

```http
GET /api/v1/admin/announcements/{announcement_id}
```

---

# 31.4 Update Platform Announcement

```http
PATCH /api/v1/admin/announcements/{announcement_id}
```

修改後同步更新該公告已建立通知的 title 與 message，不建立第二批通知。

---

# 31.5 Delete Platform Announcement

```http
DELETE /api/v1/admin/announcements/{announcement_id}
```

Success：`204 No Content`。

只刪除該平台公告產生的通知，不影響其他通知。

---

# 32. Permission Matrix

| Endpoint Group | Visitor | Member | Group Leader | Admin |
|---|---:|---:|---:|---:|
| Public Activity | Yes | Yes | Yes | Yes |
| Public Product | Yes | Yes | Yes | Yes |
| Public Group Buy | Yes | Yes | Yes | Yes |
| Public Group Leader | Yes | Yes | Yes | Yes |
| Global Search | Yes | Yes | Yes | Yes |
| Register / Login | Yes | Yes | Yes | Yes |
| Current User | No | Yes | Yes | Yes |
| Product Favorite | No | Yes | Yes | Yes |
| Follow List | No | Yes | Yes | Yes |
| Member Orders | No | Yes | Yes | Yes |
| Cancellation Request | No | Yes | Yes | Yes |
| Notifications | No | Yes | Yes | Yes |
| Group Leader Application | No | Yes | Existing profile cannot reapply | Existing profile cannot reapply |
| Group Leader Profile Setup | No | No | Yes | Only with own leader profile |
| Group Leader Operations | No | No | Completed profile only | Only with own completed leader profile |
| Admin Backend | No | No | No | Yes |

---

# 33. Transaction and Lock Requirements

## 33.1 Required Transactions

以下操作必須使用 Transaction：

- 註冊會員
- 通過或拒絕團主申請
- 完成團主公開資料
- 建立或編輯開團與商品集合
- 替換跟團清單
- 建立正式訂單
- 接受或拒絕訂單
- 更新訂單狀態
- 建立、同意或拒絕取消申請
- 發布、修改或刪除公告及其通知
- 建立或更新商品及角色關聯
- 排序商品額外圖片

## 33.2 Order Creation Lock

建立訂單時至少鎖定：

```text
group_buy
follow_list
group_buy_product
```

多筆 `group_buy_product` 依 UUID 排序鎖定。

## 33.3 Queue Order

同一開團的訂單先喊順序使用：

```text
created_at ASC, id ASC
```

每次加喊建立獨立訂單，不允許合併或回寫較早訂單時間。

## 33.4 Shared Lock Order

建議順序：

```text
app_user
↓
group_leader_profile
↓
activity
↓
group_buy
↓
follow_list
↓
group_buy_product
↓
group_order
↓
cancellation_request
```

涉及多筆相同資料時依 UUID 排序。

---

# 34. CORS and Frontend Integration

## 34.1 Development Origins

React 開發環境：

```text
http://localhost:5173
```

FastAPI：

```text
http://localhost:8000
```

後端設定：

```text
CORS_ALLOWED_ORIGINS
```

例如：

```text
http://localhost:5173
```

---

## 34.2 CORS Rules

不得在正式環境使用：

```text
allow_origins = ["*"]
```

同時開放敏感認證功能。

第一版 JWT 使用 Authorization Header，因此仍應明確限制 Origin。

---

## 34.3 React Environment Variable

React 使用：

```text
VITE_API_BASE_URL
```

例如：

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 34.4 API Client

React 共用 `apiClient` 應處理：

- Base URL
- Authorization Header
- JSON Parsing
- 401 Unauthorized
- Token 過期後保存 redirectPath 並導向登入頁
- 登入後返回原頁，但不自動重送敏感 Request
- Network Error
- 非 JSON 錯誤

---

# 35. Security Requirements

## 35.1 Password

密碼使用安全雜湊函式，不保存明文或可逆加密密碼。

## 35.2 JWT

JWT 必須驗證簽章與到期時間，使用安全 Secret，且不得在 Response Log 顯示完整 Token。

## 35.3 Authorization

不得只依賴 React 隱藏按鈕、Route Guard、AuthContext 或 Storage。所有權限及資源擁有權由 FastAPI 重新驗證。

## 35.4 SQL

使用 SQLAlchemy 參數化查詢，不直接拼接使用者輸入。

## 35.5 Text Content

公告、團規、付款方式說明、取消原因、處理回覆及訂單拒絕原因保存為純文字。

後端不接受任意 HTML；React 不使用 `dangerouslySetInnerHTML` 顯示這些內容。

## 35.6 Private Contact Information

會員私人聯絡方式只允許本人、該會員訂單所屬團主及管理員必要的申請審核資料查看。公開 API 不得回傳。

## 35.7 Immutable History

後端不得允許：

- 修改已完成拒絕的 `rejection_reason`
- 合併兩張已建立訂單
- 改寫訂單 `created_at` 以改變先喊順序
- 以目前團主名稱覆蓋歷史訂單快照

## 35.8 File Upload

需驗證 MIME Type、檔案內容、大小、路徑、Category 權限及檔名安全性。

---

# 36. HTTP Status Code Rules

| Status | Usage |
|---:|---|
| 200 | 成功取得或更新 |
| 201 | 成功建立 |
| 204 | 成功刪除且不回傳內容 |
| 400 | 一般無法處理的 Request |
| 401 | Token 不存在、無效或過期 |
| 403 | 已驗證但角色或操作權限不足 |
| 404 | 資源不存在或無權查看 |
| 409 | 狀態衝突、重複資料、凍結欄位或交易衝突 |
| 413 | 上傳檔案過大 |
| 415 | 不支援的圖片格式 |
| 422 | 欄位格式或 Enum 驗證錯誤 |
| 500 | 未預期伺服器錯誤 |

## 36.1 404 for Ownership

會員或團主存取不屬於自己的資源時建議回傳 `404 Not Found`，避免透露存在性。

## 36.2 409 for State Conflict

適用：

- 訂單狀態已改變
- 申請已被審核
- 開團已結單
- 開團已有訂單而嘗試修改凍結欄位
- 跟團清單屬於其他開團
- 接單上限低於占用數量
- 已有待處理取消申請
- 團主名稱已設定後嘗試修改
- 公告沒有收件人且未公開

---

# 37. Error Code Reference

## Authentication

```text
AUTH_TOKEN_MISSING
AUTH_TOKEN_INVALID
AUTH_TOKEN_EXPIRED
AUTH_INVALID_CREDENTIALS
```

## User

```text
EMAIL_ALREADY_EXISTS
CONTACT_REQUIRED
USER_NOT_FOUND
```

## Group Leader Application

```text
GROUP_LEADER_APPLICATION_PENDING
GROUP_LEADER_PROFILE_ALREADY_EXISTS
APPLICATION_ALREADY_REVIEWED
```

## Group Leader

```text
GROUP_LEADER_PROFILE_NOT_FOUND
GROUP_LEADER_PROFILE_INCOMPLETE
GROUP_LEADER_DISPLAY_NAME_UNAVAILABLE
GROUP_LEADER_DISPLAY_NAME_IMMUTABLE
```

## Activity and Product

```text
ACTIVITY_NOT_FOUND
ACTIVITY_ALREADY_ENDED
ACTIVITY_ALREADY_OPEN
ACTIVITY_NOT_OPEN
PRODUCT_NOT_FOUND
PRODUCT_INACTIVE
PRODUCT_ALREADY_INACTIVE
PRODUCT_ALREADY_ACTIVE
PRODUCT_ACTIVITY_MISMATCH
FULL_GIFT_NOT_SUPPORTED
```

## Character

```text
CHARACTER_NOT_FOUND
CHARACTER_NAME_ALREADY_EXISTS
CHARACTER_HAS_PRODUCT_RELATIONS
```

## Group Buy

```text
GROUP_BUY_NOT_FOUND
GROUP_BUY_NOT_OWNED
GROUP_BUY_NOT_AVAILABLE
GROUP_BUY_ALREADY_CLOSED
GROUP_BUY_PRODUCT_NOT_FOUND
GROUP_BUY_PRODUCT_DUPLICATED
GROUP_BUY_FIELDS_FROZEN
GROUP_BUY_HAS_ORDERS
GROUP_BUY_MUST_KEEP_ONE_PRODUCT
MAX_QUANTITY_BELOW_OCCUPIED
PAYMENT_METHOD_NOTE_REQUIRED
PAYMENT_METHOD_NOTE_NOT_ALLOWED
```

## Follow List

```text
FOLLOW_LIST_NOT_FOUND
FOLLOW_LIST_EMPTY
FOLLOW_LIST_ITEM_NOT_FOUND
FOLLOW_LIST_GROUP_BUY_CONFLICT
INVALID_QUANTITY
INSUFFICIENT_AVAILABLE_QUANTITY
```

## Order

```text
RULES_NOT_ACCEPTED
ORDER_NOT_FOUND
ORDER_STATUS_CONFLICT
ORDER_NOT_OWNED_BY_GROUP_LEADER
ORDER_CREATION_CONFLICT
ORDER_REJECTION_REASON_REQUIRED
INSUFFICIENT_AVAILABLE_QUANTITY
```

## Cancellation

```text
CANCELLATION_NOT_ALLOWED
CANCELLATION_REQUEST_PENDING
CANCELLATION_REQUEST_NOT_FOUND
CANCELLATION_REQUEST_ALREADY_PROCESSED
```

## Announcement

```text
ANNOUNCEMENT_NOT_FOUND
ANNOUNCEMENT_NOT_OWNED
ANNOUNCEMENT_GROUP_BUY_MISMATCH
ANNOUNCEMENT_NO_RECIPIENTS
```

## Search and Upload

```text
SEARCH_QUERY_REQUIRED
UPLOAD_CATEGORY_INVALID
UPLOAD_PERMISSION_DENIED
UPLOAD_FILE_TOO_LARGE
UPLOAD_FILE_TYPE_NOT_SUPPORTED
UPLOAD_FILE_INVALID
```

## Common

```text
VALIDATION_ERROR
RESOURCE_NOT_FOUND
PERMISSION_DENIED
CONFLICT
INTERNAL_SERVER_ERROR
```

---

# 38. Complete Endpoint Overview

## Upload

```http
POST   /uploads/images
```

## Authentication and Current User

```http
POST   /auth/register
POST   /auth/login
GET    /auth/me
GET    /users/me
PATCH  /users/me
PATCH  /users/me/contacts
```

## Group Leader Application

```http
POST   /group-leader-applications
GET    /group-leader-applications/me
```

## Search

```http
GET    /search
GET    /search/activities
GET    /search/products
GET    /search/characters
```

## Public Activity, Product and Group Buy

```http
GET    /activities
GET    /activities/{activity_id}
GET    /activities/{activity_id}/products
GET    /products/{product_id}
GET    /products/{product_id}/group-buys
GET    /group-buys/{group_buy_id}
GET    /group-buys/{group_buy_id}/rules
GET    /group-buys/{group_buy_id}/announcements
GET    /group-buy-products/{group_buy_product_id}/availability
```

## Favorites and Follow List

```http
GET    /favorites/products
POST   /favorites/products/{product_id}
DELETE /favorites/products/{product_id}
GET    /follow-list
POST   /follow-list/items
PATCH  /follow-list/items/{item_id}
DELETE /follow-list/items/{item_id}
DELETE /follow-list
```

## Member Orders, Cancellation and Notifications

```http
POST   /orders
GET    /orders
GET    /orders/{order_id}
POST   /orders/{order_id}/cancellation-requests
GET    /notifications
GET    /notifications/unread-count
GET    /notifications/summary
PATCH  /notifications/{notification_id}/read
PATCH  /notifications/read-all
```

## Public Group Leader

```http
GET    /group-leaders/{group_leader_id}
GET    /group-leaders/{group_leader_id}/group-buys
GET    /group-leaders/{group_leader_id}/announcements
```

## Group Leader Profile and Group Buys

```http
GET    /group-leader/profile
PATCH  /group-leader/profile
PATCH  /group-leader/profile/default-rules
GET    /group-leader/dashboard
GET    /group-leader/group-buys
POST   /group-leader/group-buys
GET    /group-leader/group-buys/{group_buy_id}
PATCH  /group-leader/group-buys/{group_buy_id}
POST   /group-leader/group-buys/{group_buy_id}/products
PATCH  /group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id}
DELETE /group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id}
POST   /group-leader/group-buys/{group_buy_id}/close
```

## Group Leader Orders and Announcements

```http
GET    /group-leader/orders
GET    /group-leader/orders/{order_id}
POST   /group-leader/orders/{order_id}/accept
POST   /group-leader/orders/{order_id}/reject
POST   /group-leader/orders/{order_id}/mark-paid
POST   /group-leader/orders/{order_id}/mark-shipped
POST   /group-leader/orders/{order_id}/complete
POST   /group-leader/cancellation-requests/{request_id}/approve
POST   /group-leader/cancellation-requests/{request_id}/reject
GET    /group-leader/announcements
POST   /group-leader/announcements
GET    /group-leader/announcements/{announcement_id}
PATCH  /group-leader/announcements/{announcement_id}
DELETE /group-leader/announcements/{announcement_id}
```

## Administrator

```http
GET    /admin/dashboard
GET    /admin/dashboard/current-group-buys
GET    /admin/activities
POST   /admin/activities
GET    /admin/activities/{activity_id}
PATCH  /admin/activities/{activity_id}
POST   /admin/activities/{activity_id}/end
POST   /admin/activities/{activity_id}/reopen
GET    /admin/products
POST   /admin/products
GET    /admin/products/{product_id}
PATCH  /admin/products/{product_id}
POST   /admin/products/{product_id}/deactivate
POST   /admin/products/{product_id}/reactivate
POST   /admin/products/{product_id}/images
PATCH  /admin/products/{product_id}/images/{image_id}
PATCH  /admin/products/{product_id}/images/reorder
DELETE /admin/products/{product_id}/images/{image_id}
GET    /admin/characters/suggestions
POST   /admin/characters
PATCH  /admin/characters/{character_id}
DELETE /admin/characters/{character_id}
GET    /admin/group-leader-applications
GET    /admin/group-leader-applications/{application_id}
POST   /admin/group-leader-applications/{application_id}/approve
POST   /admin/group-leader-applications/{application_id}/reject
GET    /admin/announcements
POST   /admin/announcements
GET    /admin/announcements/{announcement_id}
PATCH  /admin/announcements/{announcement_id}
DELETE /admin/announcements/{announcement_id}
```

---

# 39. Final API Decisions

1. API Base URL 使用 `/api/v1`。
2. API 使用 REST 風格，JSON 欄位使用 snake_case。
3. UUID 使用字串，日期使用 ISO 8601 UTC。
4. 金額使用字串傳輸並由後端解析為 Decimal。
5. 商品官方價格及團主售價固定使用 TWD。
6. 一般 Response 使用 `data`，列表使用 `data` 與 `pagination`。
7. 錯誤使用統一 `error` 格式。
8. 第一版 JWT 只有有效 8 小時的 Access Token，不提供 Refresh Token 或後端 Logout API。
9. Token 過期登入後返回原頁，但敏感操作不自動重送。
10. 第一版不提供會員帳號或團主權限停用 API。
11. 團主申請不要求原因、名稱、公開聯絡方式或審核備註。
12. 申請通過建立不完整團主資料，由團主之後自行完成。
13. 團主公開名稱設定後不可修改。
14. 團主公開資料完成後才可公開頁面、建立開團及發布公告。
15. 活動不使用固定分類；新增活動即新增首頁活動卡片。
16. 活動可由管理員結束及重新開啟。
17. 開團提前結單後不可重新開啟。
18. 商品頁開團預設按建立時間新到舊排序。
19. 開團比較支援價格升降序、截止時間近遠排序及可跟團、付款方式、二補、滿贈篩選。
20. 公開頁顯示查詢當下剩餘數量，但不代表保留。
21. 搜尋活動、商品、角色分開計數及分頁。
22. 跟團清單同一商品再次加入時增加數量；不同開團替換使用單一 Transaction。
23. 無效跟團清單仍保留並標示不可送出，會員可移除或清空。
24. 正式下單不信任前端價格、商品總額或快照。
25. 正式下單使用 Transaction 與 Row Lock。
26. 下單成功後才清空跟團清單，失敗時保留。
27. 同一會員可對同一開團建立多張獨立訂單，絕不合併。
28. 訂單先喊順序使用 `created_at ASC, id ASC`。
29. 訂單只顯示商品總額，不包含二補、國際運費、國內運費及其他後續費用。
30. 訂單拒絕原因必填、不可修改，拒絕訂單不可恢復。
31. 同一訂單同時最多一筆待處理取消申請；被拒絕後可重新申請。
32. 會員取消原因與團主處理回覆皆選填。
33. 團主公告支援團主整體未完成訂單範圍及指定開團未完成訂單範圍。
34. 公告可選擇是否公開；零通知對象時只有公開公告可發布。
35. 修改公告同步更新該公告通知內容，不重發通知。
36. 刪除公告只刪除該公告產生的通知。
37. 平台公告沒有獨立公開列表或詳情 Route。
38. 第一版不提供會員通知刪除 API。
39. 角色沒有獨立管理頁；商品表單支援輸入搜尋及明確新增角色。
40. 已有商品關聯的角色不可刪除。
41. 額外圖片以排列後 ID 陣列更新順序，對應前端上移／下移按鈕。
42. 管理員第一版保留 Dashboard、團主申請、活動、商品、角色支援及平台公告相關 API。
43. 第一版不加入付款、退款、物流、聊天或評價 API。
44. 本文件作為第六份 Business Rules 的 API 行為依據。

---

# End of Document
