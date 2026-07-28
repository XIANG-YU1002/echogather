# 00_Requirements_Traceability_Matrix

**Project Name:** WuWaGroup
**Document Type:** Requirements Traceability Matrix（內部工作文件，非正式規格）
**依據文件優先順序：** Business Rules v1.0 → API Design v2.1 → Database Design v2.1 → Project Specification v2.1 → User Flow v2.1 → UI Wireframe Specification v2.1 → Testing and Acceptance Plan v1.0

**已確認的文件衝突與解法（使用者決議 2026-07-21）：**

| # | 衝突 | 解法 |
|---|---|---|
| 1 | Project Spec 提到「活動分類」篩選，但 Business Rules/DB Design 明定不使用固定分類 Enum | 依使用者決議採用 Project Spec：新增 `activity.category`，但實作為**自由文字欄位（VARCHAR，選填）**，不是固定 Enum，兼顧「動態活動」精神與 Project Spec 的分類篩選需求 |
| 2 | Project Spec 官方價格支援多幣別（CNY/JPY/TWD），Business Rules/DB/API 規定官方價格固定 TWD | 依使用者決議採用 Project Spec：`product.official_price` 保留，新增 `product.official_currency` Enum（TWD/CNY/JPY），兩者同為 NULL 或同時有值；**團主售價 `group_buy_product.unit_price` 仍固定 TWD**（各文件一致，無衝突） |
| 3 | ~~Project Spec 要求管理員可查看會員列表／詳情，Business Rules/API 明定第一版不提供~~ | **【2026-07-23 使用者撤回此決議】** Stage 5 曾依 Project Spec 新增只讀會員列表／詳情端點（`GET /admin/users(/{id})`），但使用者事後認定此為「未經充分確認就擴充規格外功能」，已於 2026-07-23 要求整支移除（API 路由、Service、Schema、Repository 查詢方法、對應測試皆已刪除，前端從未實作，無需異動）。**結論：第一版不提供此功能，與 Business Rules/API 原始規格一致。** |
| 4 | ~~Project Spec 要求管理員可查看團主列表／詳情／統計，Business Rules/API 明定第一版不提供~~ | **【2026-07-23 使用者撤回此決議】** 同上，Stage 5 曾新增的唯讀團主列表／詳情端點（`GET /admin/group-leaders(/{id})`）已於 2026-07-23 整支移除。**結論：第一版不提供此功能。** |
| 5 | UI Wireframe／User Flow 首頁畫了「活動分類篩選」下拉選單，但 API Design 的 `GET /activities` 沒有 `category` 查詢參數，回應也不含 `category`（管理員活動 API 建立/修改亦未包含此欄位，Stage 5 已依 API Design 原樣完成） | 依使用者決議（2026-07-22）：**移除**首頁活動分類下拉選單，Stage 6 不實作。`activity.category` 欄位保留在資料庫（供未來擴充），但目前無任何 API 讀寫，UI 亦不顯示相關篩選 |

**重要提醒（2026-07-23 新增）：** #3、#4 原本的解法已被撤回，見上方刪除線與說明——**日後若又看到 Project Spec／User Flow／UI Wireframe 提到「管理員可查看會員/團主列表」，一律視為不採用，不需要再重新詢問或重新實作**，這不是尚待處理事項，而是已經做過一次又被明確撤銷的功能。
以上五項中，#1、#2 為欄位擴充（後端與前端皆有實際串接使用中，尚未被要求移除），#3、#4 已撤回恢復原始規格，#5 為移除 UI Wireframe/User Flow 描述但 API Design 未支援的功能。凡未被撤回的項目，皆不影響訂單、金流、權限核心規則，且是使用者已對這些衝突做出明確裁示的部分。

---

## 1. 資料表總覽（Database Design v2.1 §6 + 本文件擴充）

| # | 資料表 | 來源 |
|---|---|---|
| 1 | app_user | DB Design |
| 2 | group_leader_application | DB Design |
| 3 | group_leader_profile | DB Design |
| 4 | activity（+ `category` 擴充欄位） | DB Design + 衝突解法#1 |
| 5 | product（+ `official_currency` 擴充欄位） | DB Design + 衝突解法#2 |
| 6 | product_image | DB Design |
| 7 | character | DB Design |
| 8 | product_character | DB Design |
| 9 | group_buy | DB Design |
| 10 | group_buy_product | DB Design |
| 11 | follow_list | DB Design |
| 12 | follow_list_item | DB Design |
| 13 | group_order | DB Design |
| 14 | order_item | DB Design |
| 15 | cancellation_request | DB Design |
| 16 | product_favorite | DB Design |
| 17 | announcement | DB Design |
| 18 | notification | DB Design |

共 18 張核心資料表（與規格一致），2 張含擴充欄位。

---

## 2. Enum 總覽（Database Design v2.1 §5 + 擴充）

| Enum | 值 | 用途 |
|---|---|---|
| UserRole | member, admin | app_user.role |
| GroupLeaderApplicationStatus | pending, approved, rejected | group_leader_application.status |
| ActivityStatus | open, ended | activity.status |
| GroupBuyStatus | open, closed | group_buy.status |
| PaymentMethod | bank_transfer, cash_on_delivery, other | group_buy.payment_method |
| ContactPlatform | facebook, discord, line | group_buy.contact_platform |
| OrderStatus | pending_confirmation, pending_payment, paid, shipped, completed, cancelled, rejected | group_order.status |
| CancellationStatus | pending, approved, rejected | cancellation_request.status |
| AnnouncementType | platform, group_leader | announcement.announcement_type |
| AnnouncementAudienceScope | leader_unfinished, group_buy_unfinished | announcement.audience_scope |
| NotificationType | system, group_leader | notification.notification_type |
| **Currency（擴充）** | TWD, CNY, JPY | product.official_currency（衝突解法#2） |

---

## 3. 模組 ↔ 頁面 ↔ API ↔ 資料表 ↔ Business Rule 對應

### 3.1 Authentication / Current User
- **頁面：** /login, /register, Header 使用者選單
- **API：** POST /auth/register、POST /auth/login、GET /auth/me、GET /users/me、PATCH /users/me、PATCH /users/me/contacts
- **資料表：** app_user
- **Business Rules：** §6 Registration and Authentication、§7 Member Profile and Private Contact

### 3.2 Group Leader Application
- **頁面：** /profile（申請成為團主）、團主申請狀態頁
- **API：** POST /group-leader-applications、GET /group-leader-applications/me
- **資料表：** group_leader_application, group_leader_profile
- **Business Rules：** §8 Group Leader Application Rules

### 3.3 Group Leader Profile
- **頁面：** 團主後台／團主資料
- **API：** GET/PATCH /group-leader/profile、PATCH /group-leader/profile/default-rules
- **資料表：** group_leader_profile
- **Business Rules：** §9 Group Leader Profile Rules

### 3.4 Activity（公開 + 管理員）
- **頁面：** 首頁、活動詳情、/admin/activities
- **API：** GET /activities、GET /activities/{id}、GET /activities/{id}/products、/admin/activities CRUD + end/reopen
- **資料表：** activity
- **Business Rules：** §10 Activity Rules

### 3.5 Product / Character（公開 + 管理員）
- **頁面：** 商品詳情、/admin/products、商品表單角色搜尋
- **API：** GET /products/{id}、/admin/products CRUD、deactivate/reactivate、images、/admin/characters
- **資料表：** product, product_image, character, product_character
- **Business Rules：** §11 Product Rules、§12 Character Rules、§13 Image Rules

### 3.6 Group Buy（公開比較 + 團主建立/編輯）
- **頁面：** 商品頁開團比較、開團詳情、建立開團 Wizard、團主開團列表/詳情
- **API：** GET /products/{id}/group-buys、GET /group-buys/{id}、/group-leader/group-buys CRUD、close
- **資料表：** group_buy, group_buy_product
- **Business Rules：** §15 Creation、§16 Edit and Status、§17 Comparison

### 3.7 Follow List
- **頁面：** 跟團清單頁
- **API：** GET/POST/PATCH/DELETE /follow-list*
- **資料表：** follow_list, follow_list_item
- **Business Rules：** §18 Follow List Rules

### 3.8 Order / Cancellation
- **頁面：** 確認訂單、我的訂單、訂單詳情、申請取消、團主訂單管理
- **API：** POST /orders、GET /orders、GET /orders/{id}、POST /orders/{id}/cancellation-requests、/group-leader/orders/* actions、/group-leader/cancellation-requests/* actions
- **資料表：** group_order, order_item, cancellation_request
- **Business Rules：** §19-22

### 3.9 Favorite
- **頁面：** 收藏頁
- **API：** GET/POST/DELETE /favorites/products*
- **資料表：** product_favorite
- **Business Rules：** §23

### 3.10 Announcement / Notification
- **頁面：** 團主公告管理、平台公告管理（Admin）、通知中心、公開公告顯示
- **API：** /group-leader/announcements*、/admin/announcements*、/notifications*
- **資料表：** announcement, notification
- **Business Rules：** §24-26

### 3.11 Dashboards
- **頁面：** 團主 Dashboard、管理員 Dashboard
- **API：** GET /group-leader/dashboard、GET /admin/dashboard、GET /admin/dashboard/current-group-buys
- **資料表：** 聚合查詢，無新資料表
- **Business Rules：** §27

### 3.12 Global Search
- **頁面：** 搜尋結果頁
- **API：** GET /search、/search/activities、/search/products、/search/characters
- **資料表：** activity, product, character（trigram index）
- **Business Rules：** §14
- **註（2026-07-23 使用者決議）：** 前台搜尋結果頁不顯示「活動」分區，只顯示商品與角色。
  `/search` 的 activities 區段與 `/search/activities` 端點皆保留，後端測試不變；
  詳見 03_UI_Wireframe_Specification_v2.1 §10.1。

### 3.13 Image Upload
- **API：** POST /uploads/images
- **Business Rules：** §13

### 3.14（已撤回，不實作）~~Admin User / Group Leader Read-Only Management~~
- **狀態：** Stage 5 曾實作 `GET /admin/users(/{id})`、`GET /admin/group-leaders(/{id})`，於 2026-07-23 使用者撤回並整支刪除（含 API、Service、Schema、Repository 方法、測試）。前端從未開始實作。
- **結論：管理員後台第一版不提供會員/團主列表查看功能，與 Business Rules/API 原始規格一致。** 日後不需再新增。

---

## 4. 開發階段對應

| Stage | 內容 | 主要對應章節 |
|---|---|---|
| 1 | DB Model、Migration、Enum、Constraint | 本文件 §1、§2；DB Design 全文 |
| 2 | 登入、會員、公開 API | §3.1, 3.2, 3.4, 3.5, 3.6(公開), 3.12, 3.13 |
| 3 | 訂單與交易邏輯 | §3.7, 3.8, 3.9, 3.10(會員通知讀取) |
| 4 | 團主後台 API | §3.3, 3.6(團主), 3.10(團主公告), 3.11(團主) |
| 5 | 管理員 API | §3.4(管理), 3.5(管理), 3.10(平台公告), 3.11(管理員)；3.14 已撤回不實作 |
| 6 | React 共用版型與公開頁 | Layout, Header, 首頁, 活動/商品/開團/搜尋/團主公開頁 |
| 7 | 會員/團主/管理員頁面 | 對應各後台頁面 |
| 8 | 測試與修正 | Testing and Acceptance Plan v1.0 |

---

## 5. 明確排除項目（避免誤加功能）

依 Business Rules §33.2 及使用者指示，以下**不得**實作：評價／星等、站內聊天、第三方社群登入、忘記密碼、收件地址、付款資料管理、商品規格/尺寸選項、Footer、退款、物流追蹤、Refresh Token、帳號/團主/公告停用、開團草稿與重新開啟。
