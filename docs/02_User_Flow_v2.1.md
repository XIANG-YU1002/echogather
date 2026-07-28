# 02_User_Flow_v2.1

**Project Name:** WuWaGroup  
**Document Type:** User Flow  
**Frontend:** React、Vite、JavaScript  
**Backend:** Python、FastAPI  
**Version:** 2.1  
**Last Updated:** 2026-07-18  

---

# Change Log

| Version | Date | Description |
|---|---|---|
| 1.0 | Initial Draft | 建立初始使用者流程 |
| 1.1 | Previous Version | 補充會員、團主、訂單與公告流程 |
| 1.2 | Previous Version | 新增團主申請、會員聯絡資料、特定開團公告及取消申請流程 |
| 2.0 | 2026-07-18 | 配合 React 前端重新整理頁面導向、登入初始化、權限保護及主要操作流程 |
| 2.1 | 2026-07-18 | 配合 Project Specification v2.1，調整團主申請、開團編輯、取消申請、公告範圍、通知同步、角色刪除及管理員流程 |

---

# Table of Contents

1. Document Purpose  
2. User Flow Principles  
3. Role and Permission Overview  
4. React Application Initialization Flow  
5. Global Navigation Flow  
6. Visitor Browsing Flow  
7. Search Flow  
8. Registration Flow  
9. Login and Logout Flow  
10. Member Profile Flow  
11. Product Favorite Flow  
12. Group Leader Application Flow  
13. Follow List Flow  
14. Order Creation Flow  
15. Member Order Flow  
16. Cancellation Request Flow  
17. Notification Flow  
18. Group Leader Profile Flow  
19. Group Leader Dashboard Flow  
20. Create Group Buy Flow  
21. Manage Group Buy Flow  
22. Group Leader Order Flow  
23. Group Leader Cancellation Flow  
24. Group Leader Announcement Flow  
25. Administrator Entry Flow  
26. Admin Activity Flow  
27. Admin Product Flow  
28. Admin Character Flow  
29. Admin User Flow  
30. Admin Group Leader Application Flow  
31. Admin Group Leader Flow  
32. Admin Platform Announcement Flow  
33. Route Protection Flow  
34. Error and Exception Flow  
35. Loading and Submission Flow  
36. Session Expiration Flow  
37. Responsive Navigation Flow  
38. Complete Role Flow Summary  
39. Final Flow Decisions  

---

# 1. Document Purpose

本文件定義 WuWaGroup 第一版所有主要使用者操作流程。

本文件用途：

- 定義 Visitor、Member、Group Leader 與 Administrator 的操作順序
- 作為 React Router Route 規劃依據
- 作為 UI / Wireframe Specification 的互動依據
- 作為 API Design 的 Request 順序依據
- 作為 Business Rules 的流程來源
- 定義成功、失敗、權限不足及狀態衝突時的導向
- 確保前端流程不取代後端權限驗證
- 避免開發時出現沒有規格依據的頁面跳轉

---

# 2. User Flow Principles

## 2.1 Frontend and Backend Responsibility

React 前端負責：

- 顯示頁面
- 切換 Route
- 顯示 Loading
- 顯示表單錯誤
- 顯示成功訊息
- 顯示確認 Modal
- 根據目前使用者狀態顯示入口
- 呼叫 FastAPI
- 接收 API 結果後更新畫面

FastAPI 後端負責：

- 驗證身分
- 驗證帳號狀態
- 驗證角色
- 驗證團主資格
- 驗證資源擁有權
- 驗證訂單及開團狀態
- 驗證商品數量
- 執行 Transaction
- 建立通知
- 回傳正式結果

前端隱藏按鈕不代表使用者沒有權限。

所有敏感操作都必須由後端再次驗證。

---

## 2.2 Route Transition

React 使用：

```text
BrowserRouter
```

一般頁面切換使用前端路由，不重新載入整個網站。

例如：

```text
首頁
↓ 點擊活動卡片
活動詳情
↓ 點擊商品卡片
商品詳情
```

對應：

```text
/
↓
/activities/:activityId
↓
/products/:productId
```

---

## 2.3 Protected Route

需要登入的頁面：

```text
/favorites
/follow-list
/orders
/orders/:orderId
/notifications
/profile
/group-leader/*
/admin/*
```

進入受保護 Route 前，React 需先完成登入初始化。

---

## 2.4 Backend Validation Priority

即使 React 判定使用者已登入，呼叫受保護 API 時，後端仍需確認使用者資料存在且 Token 有效。

團主功能額外確認：

```text
group_leader_profile 存在
```

建立開團、公開團主頁或發布團主公告時，還需確認團主已完成：

- 團主公開名稱
- 至少一項團主公開聯絡方式

管理員功能額外確認：

```text
app_user.role = admin
```

---

# 3. Role and Permission Overview

## 3.1 Visitor

Visitor 可以：

```text
瀏覽
搜尋
查看活動
查看商品
查看團主公開資料
查看團主選擇公開的公告
註冊
登入
```

Visitor 嘗試使用會員功能時：

```text
顯示需要登入提示
↓
前往登入頁
```

---

## 3.2 Member

Member 為已登入會員。

Member 可以：

```text
使用一般瀏覽功能
修改個人資料
收藏商品
使用跟團清單
建立訂單
查看訂單
提出取消申請
查看通知
申請團主
```

---

## 3.3 Group Leader

Group Leader 必須具有：

```text
group_leader_profile
```

團主可以進入團主資料設定頁。

完成公開名稱與至少一項公開聯絡方式後，可以：

```text
公開團主頁
進入完整團主後台
建立開團
管理開團
管理訂單
處理取消申請
發布團主公告
```

---

## 3.4 Administrator

有效管理員必須符合：

```text
app_user.role = admin
```

管理員可以：

```text
進入管理員後台
管理活動
管理商品
管理角色
查看會員
審核團主申請
查看團主資料
管理平台公告
```

---

# 4. React Application Initialization Flow

當使用者首次開啟網站或重新整理頁面：

```text
開啟 React App
↓
AuthContext 進入 initializing
↓
檢查 sessionStorage 是否存在 Access Token
```

---

## 4.1 No Token

```text
sessionStorage 沒有 Token
↓
設定 user = null
↓
設定 isAuthenticated = false
↓
設定 initializing = false
↓
顯示目前 Route
```

公開 Route 可正常瀏覽。

受保護 Route 導向登入頁。

---

## 4.2 Token Exists

```text
sessionStorage 有 Token
↓
呼叫 GET /api/v1/auth/me
```

成功：

```text
取得目前使用者
↓
建立 AuthContext
↓
設定角色與團主資料狀態
↓
設定 initializing = false
↓
顯示目前 Route
```

---

## 4.3 Invalid or Expired Token

```text
/auth/me 回傳 401
↓
移除 sessionStorage Token
↓
清除 AuthContext
↓
設定為未登入
```

公開 Route：

```text
繼續顯示目前頁面
```

受保護 Route：

```text
導向 /login
```

---

## 4.4 Initialization Loading

`initializing = true` 時：

- 不立即判定使用者未登入
- 不立即導向登入頁
- 顯示全頁 Loading
- 等待 `/auth/me` 結果

避免重新整理受保護頁面時先錯誤跳轉。

---

# 5. Global Navigation Flow

## 5.1 Logo

```text
點擊 Logo
↓
Navigate("/")
↓
首頁
```

---

## 5.2 Visitor Header

顯示：

```text
Logo
搜尋
登入
註冊
```

點擊登入：

```text
/login
```

點擊註冊：

```text
/register
```

---

## 5.3 Member Header

顯示：

```text
Logo
搜尋
跟團清單
通知
收藏
頭像選單
```

對應 Route：

```text
跟團清單 → /follow-list
通知 → /notifications
收藏 → /favorites
```

沒有上傳頭像時顯示系統預設頭像。

---

## 5.4 Avatar Menu

一般會員顯示：

```text
個人資料
我的訂單
申請成為團主
登出
```

已有待審核團主申請時，「申請成為團主」改為顯示申請狀態入口。

具有團主資料者額外顯示：

```text
團主後台
```

管理員額外顯示：

```text
管理員後台
```

---

# 6. Visitor Browsing Flow

## 6.1 Homepage Flow

```text
Visitor 開啟首頁
↓
呼叫活動列表 API
↓
顯示目前活動
↓
顯示已結束活動
```

Visitor 可使用活動分類篩選。

---

## 6.2 Activity Flow

```text
首頁
↓ 點擊活動卡片
/activities/:activityId
↓
顯示活動資料與商品 Grid
```

活動不存在：

```text
顯示 404 頁面
```

---

## 6.3 Product Flow

```text
活動詳情
↓ 點擊商品卡片
/products/:productId
↓
顯示商品詳情
↓
顯示不同團主的開團卡片
```

---

## 6.4 Group Buy Rules Flow

```text
商品詳情
↓ 點擊查看團規
/group-buys/:groupBuyId
↓
顯示開團資訊與完整團規
↓
顯示團主選擇公開的特定開團公告
```

---

## 6.5 Group Leader Public Profile Flow

```text
商品開團卡片
↓ 點擊團主名稱
/group-leaders/:groupLeaderId
↓
顯示團主公開資料
↓
顯示團主選擇公開的整體公告
```

團主資料尚未完成公開名稱或公開聯絡方式時，不公開團主頁。

---

# 7. Search Flow

## 7.1 Search Submission

```text
使用者輸入搜尋文字
↓
按 Enter 或點擊搜尋
↓
Navigate("/search?q=關鍵字")
↓
呼叫搜尋 API
```

---

## 7.2 Search Result

結果分類：

```text
活動
商品
角色
```

---

## 7.3 Activity Result

```text
點擊活動結果
↓
/activities/:activityId
```

---

## 7.4 Product Result

```text
點擊商品結果
↓
/products/:productId
```

---

## 7.5 Character Result

```text
點擊角色結果
↓
/search?character_id=:characterId
↓
顯示該角色關聯商品
```

---

## 7.6 Empty Search

搜尋文字移除前後空白後為空：

```text
不呼叫 API
↓
提示請輸入搜尋內容
```

---

## 7.7 No Result

```text
沒有搜尋結果
↓
顯示 Empty State
```

建議文字：

```text
找不到符合條件的活動、商品或角色。
```

---

# 8. Registration Flow

## 8.1 Enter Registration Page

```text
Visitor
↓ 點擊註冊
/register
```

---

## 8.2 Fill Registration Form

會員填寫：

- Email
- 密碼
- 確認密碼
- 暱稱
- Facebook
- Discord
- LINE
- 頭像（非必填）

至少填寫一項外部聯絡方式。

未上傳頭像時使用系統預設頭像。

---

## 8.3 Frontend Validation

送出前驗證：

- Email 格式
- 密碼格式
- 確認密碼一致
- 暱稱不為空
- 至少一項聯絡方式
- 聯絡方式不可只有空白
- 若有上傳頭像，檔案格式與大小符合限制

前端驗證失敗：

```text
停留原頁面
↓
顯示欄位錯誤
```

---

## 8.4 Submit Registration

```text
點擊建立帳號
↓
按鈕進入 Loading
↓
必要時先完成頭像上傳
↓
POST /auth/register
```

---

## 8.5 Success

```text
註冊成功
↓
顯示成功訊息
↓
Navigate("/login")
```

註冊成功後自動登入並導向首頁（2026-07-28 使用者決議修訂，原為「不自動登入、導向登入頁」）。

修訂理由：註冊已改為必須通過 Email 驗證碼，帳號建立當下信箱已確認，再要求使用者
重新輸入一次帳號密碼並無額外安全效益；業界主流做法亦為註冊後自動登入。
若使用者在註冊表單選了頭像，會在自動登入後接著上傳並套用。

---

## 8.6 Email Conflict

```text
Email 已存在
↓
顯示此 Email 已被使用
↓
保留其他欄位
```

密碼欄位可清空，避免長時間保留敏感內容。

---

# 9. Login and Logout Flow

## 9.1 Login

```text
Visitor
↓
/login
↓
輸入 Email 與密碼
↓
點擊登入
↓
POST /auth/login
```

---

## 9.2 Login Success

```text
取得 Access Token
↓
保存 sessionStorage
↓
呼叫 GET /auth/me
↓
建立 AuthContext
↓
導向登入前頁面或首頁
```

登入前曾嘗試進入受保護頁面時，可保存：

```text
redirectPath
```

登入成功後回到原頁面。

---

## 9.3 Invalid Credentials

```text
Email 或密碼錯誤
↓
停留登入頁
↓
顯示通用錯誤
```

不得顯示 Email 是否存在。

---

## 9.4 Logout

```text
點擊登出
↓
移除 sessionStorage Token
↓
清除 AuthContext
↓
Navigate("/")
```

第一版不呼叫後端登出 API。

---

# 10. Member Profile Flow

## 10.1 View Profile

```text
Member
↓
頭像選單
↓
個人資料
↓
/profile
↓
GET /users/me
```

---

## 10.2 Display Information

顯示：

- Email
- 暱稱
- 頭像或預設頭像
- Facebook
- Discord
- LINE
- 帳號建立時間
- 團主申請狀態
- 是否具有團主資料

Email 第一版不允許自行修改。

一般會員頭像只對本人及其訂單所屬團主顯示，不公開給其他會員或訪客。

---

## 10.3 Edit Basic Profile

```text
修改暱稱或頭像
↓
前端驗證
↓
必要時先完成頭像上傳
↓
PATCH /users/me
↓
更新成功
↓
同步 AuthContext
```

頭像為非必填。移除自訂頭像後，改回系統預設頭像。

---

## 10.4 Edit Contact Information

```text
修改外部聯絡方式
↓
確認至少一項有效
↓
PATCH /users/me/contacts
```

若全部清空：

```text
阻止送出
↓
顯示至少保留一項聯絡方式
```

---

# 11. Product Favorite Flow

## 11.1 Visitor Clicks Favorite

```text
Visitor 點擊收藏
↓
顯示需要登入
↓
導向 /login
```

---

## 11.2 Member Adds Favorite

```text
Member 點擊收藏
↓
POST /favorites/products/:productId
↓
按鈕改為已收藏
```

---

## 11.3 Member Removes Favorite

```text
Member 點擊取消收藏
↓
DELETE /favorites/products/:productId
↓
按鈕改為未收藏
```

---

## 11.4 Favorite List

```text
Header 收藏
↓
/favorites
↓
GET /favorites/products
↓
顯示商品列表
```

已下架商品可保留顯示，但標記：

```text
商品已下架
```

---

# 12. Group Leader Application Flow

## 12.1 Entry

```text
Member
↓
個人資料或頭像選單
↓
申請成為團主
```

---

## 12.2 Existing Qualification

已有 `group_leader_profile`：

```text
不顯示申請入口
↓
導向團主資料或團主後台
```

---

## 12.3 Pending Application

已有待審核申請：

```text
不允許重複申請
↓
顯示 pending 狀態
```

同一會員同時最多只能存在一筆 `pending` 申請。

---

## 12.4 Submit Application

第一版不要求填寫申請說明或團主公開資料。

```text
點擊申請成為團主
↓
顯示確認內容
↓
確認送出
↓
POST /group-leader-applications
↓
建立 pending 申請
↓
顯示送出成功
```

---

## 12.5 Review Result

管理員通過：

```text
application.status = approved
↓
建立新的 group_leader_profile
↓
建立系統通知
↓
會員進入團主資料設定頁
```

管理員拒絕：

```text
application.status = rejected
↓
建立系統通知
```

申請被拒絕後，只要沒有新的 `pending` 申請，可以再次申請。

---

## 12.6 Initial Group Leader Setup

申請通過後，團主填寫：

- 團主公開名稱
- 至少一項公開聯絡方式
- 自我介紹（非必填）
- 預設團規（非必填）

完成前：

- 可以進入團主資料設定頁
- 不公開團主頁
- 不可建立開團
- 不可發布團主公告

會員私人聯絡方式不會自動複製為團主公開聯絡方式。

---

# 13. Follow List Flow

## 13.1 Add First Item

```text
Member 在商品頁選擇開團
↓
選擇數量
↓
點擊加入跟團清單
```

後端確認：

- 帳號有效
- 開團可跟團
- 商品屬於該開團
- 數量為正整數
- 目前可接受該數量

成功：

```text
建立 follow_list
↓
建立 follow_list_item
↓
更新 Header 清單狀態
```

---

## 13.2 Existing Same Group Buy

會員已有相同開團的跟團清單：

```text
加入另一項商品
↓
新增 follow_list_item
```

若商品已存在：

```text
原數量 + 本次加入數量
↓
更新原項目數量
```

更新前後端都需再次確認新總數量為正整數，且目前仍可接受該數量。

---

## 13.3 Existing Different Group Buy

會員已有其他開團的清單：

```text
點擊加入不同開團商品
↓
顯示衝突 Modal
```

Modal：

```text
目前跟團清單屬於其他開團。

建立新的跟團清單會清除目前內容。

[返回] [清除並更換]
```

確認：

```text
清除原 follow_list
↓
建立新 follow_list
↓
加入新商品
```

取消：

```text
保留原跟團清單
```

---

## 13.4 View Follow List

```text
Header 跟團清單
↓
/follow-list
↓
GET /follow-list
```

顯示：

- 團主
- 活動
- 開團資訊
- 商品項目
- 單價
- 數量
- 小計
- 預估總額
- 團規

---

## 13.5 Update Quantity

```text
修改數量
↓
PATCH /follow-list/items/:itemId
↓
重新取得小計與總額
```

前端顯示的總額只作預估。

---

## 13.6 Remove Item

```text
點擊移除
↓
確認
↓
DELETE /follow-list/items/:itemId
```

最後一項被移除後：

```text
跟團清單可一併刪除
↓
顯示空清單
```

---

## 13.7 Clear Follow List

```text
點擊清空
↓
確認 Modal
↓
DELETE /follow-list
↓
顯示 Empty State
```

---

## 13.8 Invalid Group Buy

開團已結單、過期、活動結束或團主失效：

```text
跟團清單顯示不可送出
↓
標示失效原因
↓
允許會員移除或清空
```

---

# 14. Order Creation Flow

## 14.1 Submit Entry

```text
/follow-list
↓
點擊送出訂單
↓
在跟團清單頁顯示完整訂單確認區塊
```

確認內容：

- 團主
- 活動
- 商品
- 數量
- 預估總額
- 付款方式
- 團規
- 團主聯絡方式
- 會員聯絡方式

確認內容較多，不使用小型 Modal 承載完整資料。

---

## 14.2 Confirm Order

```text
勾選已閱讀團規
↓
點擊確認送出
↓
按鈕進入 Loading
↓
POST /orders
```

前端只要求後端使用目前跟團清單建立訂單。

前端不提交正式價格或快照。

---

## 14.3 Backend Transaction

```text
鎖定開團商品
↓
驗證開團
↓
重新計算占用數量
↓
驗證數量
↓
重新讀取價格
↓
建立訂單
↓
建立訂單明細
↓
保存快照
↓
清空跟團清單
↓
Commit
```

---

## 14.4 Success

```text
建立成功
↓
顯示訂單編號
↓
Navigate("/orders/:orderId")
```

初始狀態：

```text
pending_confirmation
```

---

## 14.5 Quantity Conflict

送單期間數量已被其他會員占用：

```text
回傳數量不足
↓
訂單不建立
↓
跟團清單保留
↓
顯示需要調整的商品
```

---

## 14.6 Group Buy Invalid

若開團已失效：

```text
不建立訂單
↓
跟團清單保留
↓
顯示開團目前不可送單
```

---

# 15. Member Order Flow

## 15.1 Order List

```text
頭像選單
↓
我的訂單
↓
/orders
↓
GET /orders
```

可使用簡單下拉選單依訂單狀態篩選：

- 全部
- 待確認
- 待付款
- 已付款
- 已出貨
- 已完成
- 已取消
- 已拒絕

---

## 15.2 Order Detail

```text
點擊訂單
↓
/orders/:orderId
↓
GET /orders/:orderId
```

顯示：

- 訂單編號
- 訂單狀態
- 團主快照
- 活動快照
- 商品明細
- 總額
- 付款方式
- 團規
- 團主聯絡方式
- 取消申請
- 拒絕原因
- 建立時間

---

## 15.3 Pending Confirmation

顯示：

```text
等待團主確認
```

可用操作依 Business Rules 判定是否允許取消申請。

---

## 15.4 Pending Payment

顯示：

```text
等待付款確認
```

會員依外部聯絡方式與團主完成付款。

平台不提供付款按鈕。

---

## 15.5 Paid

顯示：

```text
團主已確認付款
```

等待團主出貨。

---

## 15.6 Shipped

顯示：

```text
已出貨
```

第一版不顯示物流編號。

---

## 15.7 Completed

顯示：

```text
訂單已完成
```

不提供評價。

---

## 15.8 Rejected

顯示：

```text
訂單已被團主拒絕
```

同時顯示團主填寫的必填拒絕原因。

拒絕後不可恢復訂單，也不可修改拒絕原因。

---

## 15.9 Cancelled

顯示：

```text
訂單已取消
```

不得重新啟用。

---

# 16. Cancellation Request Flow

## 16.1 Entry

符合可取消條件的訂單顯示：

```text
申請取消訂單
```

同一時間已存在 `pending` 取消申請時，不顯示新的申請入口。

---

## 16.2 Submit Request

```text
點擊申請取消
↓
可選填取消原因
↓
確認送出
↓
POST /orders/:orderId/cancellation-request
```

取消原因不是必填，因為會員可能已先透過 Facebook、Discord 或 LINE 與團主完成溝通。

---

## 16.3 Pending Request

建立後：

```text
cancellation_request.status = pending
```

訂單狀態保持原狀。

畫面顯示：

```text
取消申請審核中
```

此申請處理完成前不得再次提出。

---

## 16.4 Approved

團主同意：

```text
cancellation_request.status = approved
group_order.status = cancelled
↓
建立會員通知
```

---

## 16.5 Rejected

團主拒絕：

```text
cancellation_request.status = rejected
group_order.status 不變
↓
建立會員通知
```

團主回覆為選填。

只要訂單仍符合取消條件，會員之後可以再次提出新的取消申請。

---

# 17. Notification Flow

## 17.1 Unread Count

登入後，Header 可呼叫：

```text
GET /notifications/unread-count
```

顯示未讀數量。

---

## 17.2 Notification List

```text
點擊通知
↓
/notifications
↓
GET /notifications
```

顯示標籤：

```text
系統
團主
```

---

## 17.3 Open Notification

系統通知可能導向：

- 訂單詳情
- 團主申請結果
- 平台公告詳情

團主通知可能導向：

- 團主公告詳情
- 團主公開頁
- 對應開團
- 對應訂單

點擊通知時，同時將該通知標記為已讀。

公告被刪除後，該公告產生的通知也會一併刪除，不會留下無法開啟的通知。

---

## 17.4 Mark as Read

```text
開啟通知
↓
PATCH /notifications/:notificationId/read
↓
更新已讀狀態
```

---

## 17.5 Read All

```text
點擊全部已讀
↓
PATCH /notifications/read-all
↓
未讀數歸零
```

---

# 18. Group Leader Profile Flow

## 18.1 Enter Group Leader Backend

```text
具有 group_leader_profile 的會員
↓
頭像選單
↓
團主後台
↓
/group-leader
```

若團主公開資料尚未完成，先導向：

```text
/group-leader/profile
```

---

## 18.2 Profile Management

```text
/group-leader/profile
↓
GET /group-leader/profile
```

團主可修改：

- 公開名稱
- 自我介紹（非必填）
- Facebook
- Discord
- LINE

團主頭像使用會員目前頭像，未上傳時顯示預設頭像。

公開名稱必填，且至少保留一項公開聯絡方式。

團主公開聯絡方式與會員私人聯絡方式分開保存。

---

## 18.3 Initial Setup Completion

首次設定完成：

```text
保存公開名稱與聯絡方式
↓
PATCH /group-leader/profile
↓
資料完整
↓
可公開團主頁、建立開團及發布公告
```

---

## 18.4 Default Rules

```text
修改預設團規
↓
PATCH /group-leader/profile/default-rules
```

只影響後續新開團的預設內容。

不影響既有開團。

---

# 19. Group Leader Dashboard Flow

```text
/group-leader
↓
GET /group-leader/dashboard
↓
顯示簡化資訊與最近資料
```

顯示：

- 目前開團
- 待處理訂單
- 待處理取消申請
- 最近訂單

點擊項目可進入對應列表或已篩選列表。

例如：

```text
待處理訂單
↓
/group-leader/orders?status=pending_confirmation
```

Dashboard 不重複顯示大量訂單狀態統計。

---

# 20. Create Group Buy Flow

## 20.1 Entry

```text
團主後台
↓
點擊建立開團
↓
/group-leader/group-buys/new
```

---

## 20.2 Select Activity

團主先選擇一項目前開放的活動。

已結束活動不可選擇。

---

## 20.3 Step 1: Select Products

```text
取得活動商品
↓
團主勾選商品
```

功能：

- 單項選取
- 全選
- 清除選擇

沒有選擇商品時：

```text
下一步停用
```

---

## 20.4 Step 2: Price and Quantity

每項商品填寫：

- 團購價格
- 接單數量上限

前端驗證：

```text
unit_price >= 0
max_quantity > 0
```

---

## 20.5 Step 3: Group Buy Settings

填寫：

- 付款方式
- 是否需要二補
- 是否包含滿贈
- 收單截止時間
- 團規
- 主要聯絡平台
- 主要聯絡內容

活動不支援滿贈時：

```text
不顯示滿贈選項
includes_full_gift = false
```

---

## 20.6 Submit

```text
點擊建立開團
↓
顯示確認摘要
↓
確認
↓
POST /group-leader/group-buys
```

---

## 20.7 Success

```text
建立 group_buy
↓
建立 group_buy_product
↓
status = open
↓
Navigate("/group-leader/group-buys/:groupBuyId")
```

---

## 20.8 Failure

任一商品驗證失敗：

```text
整筆建立失敗
↓
不建立部分開團
↓
保留表單資料
```

---

# 21. Manage Group Buy Flow

## 21.1 List

```text
/group-leader/group-buys
↓
GET /group-leader/group-buys
```

可使用簡單下拉選單篩選：

```text
全部
open
closed
```

---

## 21.2 Detail

```text
點擊開團
↓
/group-leader/group-buys/:groupBuyId
```

顯示：

- 活動
- 狀態
- 實際可用狀態
- 開團設定
- 商品價格
- 接單上限
- 占用數量
- 可接受數量
- 訂單統計

---

## 21.3 Update Before Any Order

開團尚未建立任何正式訂單時，可以修改：

- 已選商品集合
- 商品價格
- 商品接單上限
- 付款方式
- 是否需要二補
- 是否包含滿贈
- 收單截止時間
- 團規
- 主要聯絡平台
- 主要聯絡內容

```text
修改資料
↓
PATCH /group-leader/group-buys/:groupBuyId
```

---

## 21.4 Update After Orders Exist

開團已存在至少一筆正式訂單後，只能修改：

- 收單截止時間
- 主要聯絡平台
- 主要聯絡內容
- 商品接單數量上限

不可修改商品價格、付款方式、二補、滿贈、團規及商品集合。

修改接單上限：

```text
PATCH /group-leader/group-buys/:groupBuyId/products/:groupBuyProductId
```

新上限不得低於目前有效訂單占用數量。

既有訂單快照不變。

---

## 21.5 Close Group Buy

```text
點擊提前結單
↓
確認 Modal
↓
POST /group-leader/group-buys/:groupBuyId/close
```

成功後：

```text
status = closed
↓
不接受新清單或訂單
```

第一版不提供重新開啟。

---

# 22. Group Leader Order Flow

## 22.1 Order List

```text
/group-leader/orders
↓
GET /group-leader/orders
```

可使用簡單下拉選單篩選：

- 開團
- 活動
- 訂單狀態
- 是否有待處理取消申請

---

## 22.2 Order Detail

```text
點擊訂單
↓
/group-leader/orders/:orderId
```

顯示：

- 訂單編號
- 會員暱稱
- 會員目前頭像或預設頭像
- 會員聯絡快照
- 商品
- 數量
- 金額
- 訂單狀態
- 取消申請
- 可執行操作

會員頭像只供該筆訂單所屬團主辨識，不公開給其他使用者。

---

## 22.3 Accept Order

```text
pending_confirmation
↓
點擊接受
↓
確認 Modal
↓
POST /group-leader/orders/:orderId/accept
↓
pending_payment
↓
建立會員通知
```

---

## 22.4 Reject Order

```text
pending_confirmation
↓
點擊拒絕
↓
開啟拒絕 Modal
↓
填寫必填拒絕原因
```

確認後：

```text
POST /group-leader/orders/:orderId/reject
↓
status = rejected
↓
保存 rejection_reason
↓
建立會員通知
```

拒絕後不可恢復，也不可修改拒絕原因。

---

## 22.5 Mark Paid

```text
pending_payment
↓
確認已收到外部付款
↓
POST /group-leader/orders/:orderId/mark-paid
↓
paid
↓
建立會員通知
```

---

## 22.6 Mark Shipped

```text
paid
↓
點擊標記出貨
↓
POST /group-leader/orders/:orderId/mark-shipped
↓
shipped
↓
建立會員通知
```

---

## 22.7 Complete

```text
shipped
↓
點擊完成訂單
↓
確認
↓
POST /group-leader/orders/:orderId/complete
↓
completed
↓
建立會員通知
```

---

## 22.8 Invalid Transition

若前端畫面未更新，團主對舊狀態執行操作：

```text
後端回傳 INVALID_STATUS_TRANSITION
↓
重新取得訂單詳情
↓
顯示目前狀態已變更
```

---

# 23. Group Leader Cancellation Flow

## 23.1 Pending Cancellation List

```text
團主 Dashboard 或訂單列表
↓
篩選待處理取消申請
```

---

## 23.2 Approve

```text
開啟訂單詳情
↓
查看取消原因
↓
點擊同意取消
↓
確認 Modal
↓
POST /cancellation-request/approve
```

成功：

```text
request = approved
order = cancelled
↓
釋放占用數量
↓
建立會員通知
```

---

## 23.3 Reject

```text
點擊拒絕取消
↓
可選填回覆
↓
POST /cancellation-request/reject
```

成功：

```text
request = rejected
order 保持原狀
↓
建立會員通知
```

會員之後仍可在訂單符合取消條件時再次申請。

---

# 24. Group Leader Announcement Flow

## 24.1 List

```text
/group-leader/announcements
↓
GET /group-leader/announcements
```

列表顯示公告範圍、是否公開、通知人數與發布時間。

---

## 24.2 Create General Announcement

團主整體公告通知該團主名下所有至少有一筆未完成訂單的會員。

```text
點擊發布公告
↓
選擇「團主整體公告」
↓
輸入標題與內容
↓
選擇是否公開
↓
POST /group-leader/announcements
```

公開時顯示於團主公開頁。

---

## 24.3 Create Specific Group Buy Announcement

```text
點擊發布公告
↓
選擇「特定開團公告」
↓
選擇自己的開團
↓
輸入標題與內容
↓
選擇是否公開
↓
POST /group-leader/announcements
```

通知對象為該開團中至少有一筆未完成訂單的會員。

公開時顯示於該開團詳情頁。

未完成訂單狀態：

```text
pending_confirmation
pending_payment
paid
shipped
```

不通知：

```text
completed
cancelled
rejected
```

同一會員有多筆符合條件的訂單時，只建立一則相同公告通知。

---

## 24.4 No Recipient

後端先計算通知對象。

公開公告：

```text
通知人數 = 0
↓
仍可發布
↓
顯示於對應公開頁
```

不公開公告：

```text
通知人數 = 0
↓
阻止發布
↓
提示目前沒有可通知的會員
```

---

## 24.5 Edit

```text
開啟自己的公告
↓
修改標題、內容或公開狀態
↓
PATCH /group-leader/announcements/:announcementId
```

修改後：

- 公告內容更新
- 該公告先前建立的通知內容同步更新
- 不重新建立第二批通知

---

## 24.6 Delete

```text
點擊刪除公告
↓
確認 Modal
↓
DELETE /group-leader/announcements/:announcementId
```

刪除後：

- 公告資料刪除
- 該公告產生的通知一併刪除
- 其他訂單狀態通知不受影響

---

# 25. Administrator Entry Flow

```text
有效管理員
↓
頭像選單
↓
管理員後台
↓
/admin
```

一般會員輸入 `/admin`：

```text
前端導向無權限頁或首頁
```

後端 `/admin/*` API 仍回傳 403。

---

# 26. Admin Activity Flow

## 26.1 List

```text
/admin/activities
↓
GET /admin/activities
```

---

## 26.2 Create

```text
點擊新增活動
↓
填寫活動資料
↓
上傳圖片
↓
POST /admin/activities
↓
建立成功
```

---

## 26.3 Edit

```text
活動詳情
↓
修改資料
↓
PATCH /admin/activities/:activityId
```

---

## 26.4 End Activity

```text
點擊結束活動
↓
確認 Modal
↓
狀態改為 ended
```

已結束活動不可建立新開團。

---

# 27. Admin Product Flow

## 27.1 Product List

```text
/admin/products
↓
依活動或狀態篩選
```

---

## 27.2 Create Product

```text
選擇活動
↓
填寫商品資料
↓
上傳主要圖片
↓
選擇角色
↓
建立商品
```

---

## 27.3 Extra Images

```text
商品詳情
↓
上傳額外圖片
↓
使用上移或下移調整顯示順序
↓
保存排序
```

第一版不要求拖曳排序。

---

## 27.4 Edit Product

```text
修改名稱、官方價格、幣別或角色
↓
保存
```

---

## 27.5 Unpublish Product

```text
點擊下架
↓
確認
↓
is_active = false
```

歷史訂單不受影響。

---

## 27.6 Republish Product

```text
已下架商品
↓
點擊重新上架
↓
is_active = true
```

---

# 28. Admin Character Flow

## 28.1 List

```text
/admin/characters
↓
顯示角色列表
```

---

## 28.2 Create

```text
新增角色
↓
輸入名稱
↓
POST
```

名稱重複：

```text
顯示角色已存在
```

---

## 28.3 Edit

```text
角色詳情
↓
修改名稱
↓
保存
```

---

## 28.4 Delete

沒有關聯任何商品：

```text
點擊刪除角色
↓
確認
↓
DELETE /admin/characters/:characterId
```

已有商品關聯：

```text
不允許直接刪除
↓
提示先移除所有商品關聯
```

---

# 29. Admin User Flow

## 29.1 User List

```text
/admin/users
↓
GET /admin/users
↓
顯示會員列表
```

可使用簡單篩選：

```text
全部
一般會員
具有團主資料
```

---

## 29.2 User Detail

```text
點擊會員
↓
/admin/users/:userId
↓
顯示會員資料與是否具有團主資料
```

管理員可查看：

- Email
- 暱稱
- 帳號建立時間
- 團主申請狀態
- 是否具有團主資料

第一版不提供停用、重新啟用或刪除會員功能。

---

# 30. Admin Group Leader Application Flow

## 30.1 Pending List

```text
/admin/group-leader-applications
↓
篩選 pending
```

---

## 30.2 Detail

顯示：

- 會員 Email
- 會員暱稱
- 申請時間
- 目前申請狀態

第一版沒有申請說明、公開聯絡方式或審核備註。

---

## 30.3 Approve

```text
點擊通過
↓
確認
↓
鎖定申請
↓
建立新的 group_leader_profile
↓
application = approved
↓
建立通知
```

通過後，會員需自行完成團主公開名稱與公開聯絡方式。

---

## 30.4 Reject

```text
點擊拒絕
↓
確認
↓
鎖定申請
↓
application = rejected
↓
建立通知
```

第一版不要求填寫審核備註。

---

## 30.5 Duplicate Review

申請已由其他管理員處理：

```text
後端回傳狀態衝突
↓
重新取得申請詳情
↓
顯示最新結果
```

同一筆申請只能處理一次，審核完成後不可改變結果。

---

# 31. Admin Group Leader Flow

## 31.1 List

```text
/admin/group-leaders
↓
GET /admin/group-leaders
↓
顯示團主列表
```

---

## 31.2 Detail

顯示：

- 團主公開資料
- 對應會員
- 團主資料是否完整
- 開團數
- 目前開團
- 完成訂單數

第一版不提供停用、重新啟用或移除團主權限功能。

---

# 32. Admin Platform Announcement Flow

## 32.1 List

```text
/admin/announcements
↓
GET /admin/announcements
↓
顯示平台公告
```

---

## 32.2 Create

```text
點擊新增公告
↓
輸入標題與內容
↓
POST /admin/announcements
↓
通知所有已註冊會員
```

平台公告不建立獨立公開公告頁，主要顯示於會員通知中心。

---

## 32.3 Edit

```text
修改平台公告
↓
PATCH /admin/announcements/:announcementId
```

修改後：

- 公告內容更新
- 該公告已建立的通知內容同步更新
- 不重新建立通知

---

## 32.4 Delete

```text
點擊刪除
↓
確認 Modal
↓
DELETE /admin/announcements/:announcementId
```

刪除後，該公告產生的通知一併刪除。

---

# 33. Route Protection Flow

## 33.1 Public Route

公開 Route：

```text
/
/login
/register
/search
/activities/:activityId
/products/:productId
/group-buys/:groupBuyId
/group-leaders/:groupLeaderId
```

不要求登入。

---

## 33.2 Member Route

```text
/favorites
/follow-list
/orders
/orders/:orderId
/notifications
/profile
```

流程：

```text
Auth 初始化完成
↓
未登入 → /login
已登入 → 顯示頁面
```

---

## 33.3 Group Leader Route

```text
/group-leader/*
```

流程：

```text
未登入
→ /login

已登入但沒有團主資料
→ /profile

已有團主資料但公開資料尚未完成
→ /group-leader/profile

團主資料完整
→ 顯示團主後台
```

---

## 33.4 Admin Route

```text
/admin/*
```

流程：

```text
未登入
→ /login

已登入但不是 admin
→ 403 頁面或首頁

admin
→ 顯示管理員後台
```

---

# 34. Error and Exception Flow

## 34.1 400 Validation Error

```text
顯示表單或操作錯誤
↓
保留使用者輸入
```

---

## 34.2 401 Unauthorized

```text
移除 Token
↓
清除 AuthContext
↓
導向登入頁
```

---

## 34.3 403 Forbidden

```text
顯示沒有權限
```

團主公開資料尚未完成時，建立開團或發布公告：

```text
導向 /group-leader/profile
↓
提示先完成公開名稱與至少一項公開聯絡方式
```

---

## 34.4 404 Not Found

```text
顯示 404 頁面
```

團主存取其他團主資源時，後端可回傳 404，避免透露資源存在。

---

## 34.5 409 Conflict

用於：

- 訂單狀態已變更
- 開團已結單
- 數量上限低於占用數量
- 申請已被處理
- 重複收藏
- 同時存在待處理取消申請
- 不公開公告沒有通知對象

前端：

```text
顯示具體錯誤
↓
重新取得最新資料
```

---

## 34.6 422 Unprocessable Entity

用於：

- 欄位格式錯誤
- 缺少必填欄位
- 活動不支援滿贈
- 聯絡方式不足
- 商品不屬於活動
- 訂單拒絕原因為空

---

## 34.7 500 Server Error

```text
顯示系統暫時無法處理
↓
保留安全的重新嘗試入口
```

不得直接顯示後端 Stack Trace。

---

# 35. Loading and Submission Flow

所有送出操作：

```text
點擊送出
↓
設定 submitting = true
↓
停用按鈕
↓
顯示 Loading
↓
呼叫 API
```

成功或失敗後：

```text
設定 submitting = false
```

送出期間：

- 不可重複送出
- 不可連續點擊確認
- Modal 確認按鈕停用
- 必要時阻擋關閉 Modal

---

# 36. Session Expiration Flow

使用者操作期間 Token 到期：

```text
API 回傳 401
↓
apiClient 統一處理
↓
移除 Token
↓
清除 AuthContext
↓
保存目前 Route
↓
導向 /login
```

登入成功後返回原 Route。

送出敏感表單時 Token 到期：

- 不自動重新送出原操作
- 避免建立重複訂單或重複狀態操作
- 使用者重新登入後需再次確認送出

---

# 37. Responsive Navigation Flow

## 37.1 Desktop

Header 顯示完整：

- 搜尋
- 跟團清單
- 通知
- 收藏
- 頭像選單

團主與管理員後台使用側邊選單。

---

## 37.2 Mobile

Header 可收合為：

```text
Logo
搜尋按鈕
通知
Menu
```

Menu 內包含：

- 跟團清單
- 收藏
- 訂單
- 個人資料
- 團主後台
- 管理員後台
- 登出

具體樣式由 UI / Wireframe Specification 決定。

---

## 37.3 Mobile Modal

Modal 在手機版可使用：

- 接近全螢幕寬度
- 固定操作按鈕區
- 內容可捲動

不得讓確認按鈕超出螢幕。

---

# 38. Complete Role Flow Summary

## Visitor

```text
首頁
↓
活動
↓
商品
↓
比較開團
↓
查看公開團主公告
↓
登入或註冊
```

---

## Member

```text
登入
↓
瀏覽商品
↓
選擇團主開團
↓
加入跟團清單
↓
確認團規與聯絡資料
↓
送出訂單
↓
查看訂單與通知
```

---

## Group Leader

```text
會員申請團主
↓
管理員通過
↓
完成團主公開資料
↓
進入團主後台
↓
建立開團
↓
接收訂單
↓
接受或拒絕
↓
確認付款
↓
標記出貨
↓
完成訂單
↓
發布整體或特定開團公告
```

---

## Administrator

```text
管理員登入
↓
進入管理員後台
↓
管理活動、商品與角色
↓
審核團主申請
↓
查看會員與團主資料
↓
管理平台公告
```

---

# 39. Final Flow Decisions

1. React App 啟動時先完成 Auth 初始化。
2. 重新整理受保護頁面時，不可在初始化完成前錯誤導向。
3. Route Guard 只負責前端顯示，後端仍驗證權限。
4. Visitor 可以瀏覽、搜尋及查看團主選擇公開的公告。
5. 註冊時暱稱與至少一項外部聯絡方式必填，頭像非必填。
6. 註冊成功後自動登入並導向首頁（2026-07-28 修訂）。
7. 登入成功後返回登入前原頁面。
8. Email 第一版不允許會員自行修改。
9. Token 保存於 sessionStorage，登出只移除前端 Token。
10. 收藏列表保留已下架商品並標示下架狀態。
11. 跟團清單一次只能屬於一筆開團。
12. 再次加入同一商品時，數量與原數量相加。
13. 不同開團商品不可直接混入同一跟團清單。
14. 失效跟團清單不自動刪除，會員可自行移除或清空。
15. 送出訂單前必須勾選已閱讀團規。
16. 訂單建立失敗時保留跟團清單。
17. 送出訂單時重新驗證價格、數量及開團狀態。
18. 訂單成功建立後才清空跟團清單。
19. 會員與團主訂單列表提供簡單狀態篩選。
20. 團主只能處理自己的開團與訂單。
21. 訂單狀態只能透過指定 Action 流程更新。
22. 拒絕訂單只允許從 pending_confirmation 執行。
23. 訂單拒絕原因為必填，拒絕後不可修改或恢復。
24. 會員取消原因與團主拒絕回覆皆為選填。
25. 同一訂單同時最多一筆待處理取消申請，被拒後符合條件時可再次申請。
26. 通知可導向相關訂單、申請、公告、團主或開團頁面。
27. 通知可標記單筆已讀或全部已讀，會員不可自行刪除通知。
28. 團主申請不要求申請說明或審核備註，同時最多一筆待審核申請。
29. 申請通過後先完成團主公開名稱與至少一項公開聯絡方式。
30. 團主 Dashboard 使用簡化版，項目可連到對應列表。
31. 建立開團前先選擇開放中的活動。
32. 開團沒有正式訂單時可修改全部內容。
33. 開團已有正式訂單後，只能修改收單時間、聯絡方式及接單上限。
34. 接單上限不得低於目前有效訂單占用數量。
35. 管理列表使用簡單下拉選單篩選，不建立複雜搜尋系統。
36. 團主公告分為團主整體公告與特定開團公告。
37. 團主公告只通知未完成訂單會員，且同一公告對同一會員只建立一則通知。
38. 團主可選擇公告是否公開；公開只影響頁面顯示，不改變通知對象。
39. 公開公告即使通知人數為零仍可發布；不公開公告沒有通知對象時不可發布。
40. 修改公告會同步更新相關通知內容，不重新建立通知。
41. 刪除公告會一併刪除該公告產生的通知。
42. 商品額外圖片可用上移或下移調整順序。
43. 未關聯商品的角色可刪除；已關聯角色需先解除關聯。
44. 平台公告通知所有已註冊會員，不建立獨立公開公告頁。
45. 第一版不提供會員帳號或團主權限停用功能。
46. Token 到期後返回原頁面，但不自動重送敏感操作。
47. 所有重要操作需顯示 Loading 並阻止重複送出。
48. 狀態衝突後，前端應重新取得最新資料。
49. 手機導覽採收合選單，具體樣式由 UI 文件決定。
50. 本文件流程作為第三份 UI / Wireframe Specification 的頁面與互動依據。

---

# End of Document
