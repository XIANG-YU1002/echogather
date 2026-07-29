# 06_Business_Rules_v1.0

**Project Name:** WuWaGroup  
**Document Type:** Business Rules  
**Related Documents:** Project Specification v2.1、User Flow v2.1、UI / Wireframe Specification v2.1、Database Design v2.1、API Design v2.1  
**Version:** 1.0  
**Last Updated:** 2026-07-18  

---

# Change Log

| Version | Date | Description |
|---|---|---|
| 1.0 | 2026-07-18 | 依前五份 v2.1 文件建立第一版完整業務規則，統一會員、團主、活動、商品、開團、訂單、取消申請、公告、通知、圖片與管理員規則 |

---

# Table of Contents

1. Document Purpose  
2. Rule Authority and Interpretation  
3. Core Terms  
4. General Business Principles  
5. Roles and Permission Rules  
6. Registration and Authentication Rules  
7. Member Profile and Private Contact Rules  
8. Group Leader Application Rules  
9. Group Leader Profile Rules  
10. Activity Rules  
11. Product Rules  
12. Character Rules  
13. Image Rules  
14. Public Browsing and Search Rules  
15. Group Buy Creation Rules  
16. Group Buy Edit and Status Rules  
17. Group Buy Comparison Rules  
18. Follow List Rules  
19. Order Creation Rules  
20. Quantity and Queue Priority Rules  
21. Order Status Rules  
22. Cancellation Request Rules  
23. Favorite Rules  
24. Group Leader Announcement Rules  
25. Platform Announcement Rules  
26. Notification Rules  
27. Administrator Rules  
28. Money, Time and Display Rules  
29. Validation and Error Rules  
30. Transaction and Concurrency Rules  
31. Privacy and Security Rules  
32. Data Retention and Delete Rules  
33. First Version Scope Boundaries  
34. Business Rule Acceptance Checklist  
35. Final Business Decisions  

---

# 1. Document Purpose

本文件定義 WuWaGroup 第一版所有主要功能必須遵守的業務規則。

本文件用途：

- 作為前端畫面判斷依據
- 作為 FastAPI Service Layer 驗證依據
- 作為 Pydantic Schema 驗證依據
- 作為 SQLAlchemy Transaction 設計依據
- 作為測試案例與驗收條件來源
- 統一 Project Specification、User Flow、UI、Database 與 API 的行為
- 明確區分畫面提示、API 驗證及資料庫限制
- 避免前端自行推測後端狀態
- 避免同一功能在不同文件出現不同解讀

本文件只定義第一版已確認的規則。

---

# 2. Rule Authority and Interpretation

## 2.1 Rule Priority

若不同文件的描述出現差異，第一版實作依下列順序判斷：

```text
已確認的最新決策
↓
本 Business Rules
↓
API Design v2.1
↓
Database Design v2.1
↓
UI / Wireframe Specification v2.1
↓
User Flow v2.1
↓
Project Specification v2.1
```

本文件不得自行擴充未確認的付款、物流、聊天或評價功能。

---

## 2.2 Server Is the Final Authority

React 前端可以：

- 隱藏不適用的按鈕
- 顯示目前可執行操作
- 先做基本欄位驗證
- 顯示查詢當下的剩餘數量

但最終結果必須由 FastAPI 後端重新驗證。

前端顯示：

```text
可跟團
剩餘 3 個
可以取消
可以接受訂單
```

均不代表操作一定成功。

---

## 2.3 Trim and Empty Values

所有文字輸入在驗證前先移除前後空白。

選填欄位輸入：

```text
""
"   "
```

時，正規化為：

```text
null
```

必填欄位正規化後為空，視為驗證失敗。

---

## 2.4 First Version Principle

第一版優先考量：

- 規則清楚
- 可完成
- 可測試
- 可展示
- 不建立不必要的企業級功能
- 不讓功能之間產生無法解釋的例外

---

# 3. Core Terms

## 3.1 Visitor

未登入使用者。

可瀏覽公開資料，但不可收藏、建立跟團清單、下單或申請團主。

---

## 3.2 Member

已註冊並登入的使用者。

所有團主與管理員同時也是會員帳號。

---

## 3.3 Group Leader

具有 `group_leader_profile` 的會員。

團主不是獨立帳號，也不是獨立 `UserRole`。

---

## 3.4 Completed Group Leader Profile

團主公開資料同時符合：

```text
已設定公開名稱
AND
至少一項公開聯絡方式
```

才視為完成。

---

## 3.5 Administrator

`app_user.role = admin` 的帳號。

管理員不會因為是管理員而自動取得團主功能。

若管理員另外具有完成的團主資料，才可使用團主功能。

---

## 3.6 Formal Order

會員正式送出後建立的 `group_order`。

跟團清單不是正式訂單，也不保留數量。

---

## 3.7 Unfinished Order

用於團主公告通知範圍時，未完成訂單為：

```text
pending_confirmation
pending_payment
paid
shipped
```

不包含：

```text
completed
cancelled
rejected
```

---

## 3.8 Occupying Order

用於數量計算時，除以下狀態外的訂單都占用數量：

```text
cancelled
rejected
```

因此 `completed` 訂單仍計入已占用數量。

---

## 3.9 Product Total Amount

訂單中的商品總額：

```text
SUM(unit_price × quantity)
```

不包含二補、國際運費、國內運費或其他後續費用。

---

# 4. General Business Principles

| Rule ID | Rule |
|---|---|
| BR-GEN-001 | 平台定位為官方周邊資訊整合與跟團管理，不是完整電商平台。 |
| BR-GEN-002 | 正式資料以後端與資料庫為準，前端狀態不得取代後端驗證。 |
| BR-GEN-003 | 重要業務資料應保留歷史，不因後續名稱、價格或聯絡方式變更而改寫舊訂單。 |
| BR-GEN-004 | 數量、統計與收件人數等衍生資料原則上即時計算，不保存容易失真的重複欄位。 |
| BR-GEN-005 | 金額一律使用 TWD 與 Decimal／NUMERIC，不使用浮點數計算。 |
| BR-GEN-006 | 重要狀態變更使用明確操作，不允許前端任意指定目標狀態。 |
| BR-GEN-007 | 所有需要確認的操作在提交期間必須防止重複送出。 |
| BR-GEN-008 | 發生狀態衝突時，前端重新取得最新資料後再顯示可執行操作。 |
| BR-GEN-009 | 第一版不提供會員帳號停用、團主權限停用或重新啟用功能。 |
| BR-GEN-010 | 第一版不提供公告停用功能，公告只提供修改與刪除。 |

---

# 5. Roles and Permission Rules

## 5.1 Visitor Permissions

Visitor 可以：

- 查看首頁目前活動及已結束活動
- 查看活動詳情
- 查看上架商品
- 搜尋活動、商品與角色
- 查看商品的開團比較
- 查看公開開團團規
- 查看已完成資料的團主公開頁
- 查看團主選擇公開的公告

Visitor 不可：

- 收藏商品
- 建立或修改跟團清單
- 正式下單
- 查看通知
- 查看會員訂單
- 申請團主
- 使用團主或管理員後台

---

## 5.2 Member Permissions

Member 除 Visitor 功能外，可以：

- 管理個人資料
- 管理私人聯絡方式
- 收藏商品
- 建立跟團清單
- 正式送出訂單
- 查看自己的訂單
- 申請取消訂單
- 查看並標記通知
- 申請團主資格

---

## 5.3 Group Leader Permissions

具有完整團主公開資料後，可以：

- 顯示公開團主頁
- 建立與管理自己的開團
- 查看及處理自己開團的訂單
- 查看訂單中的會員聯絡快照
- 處理取消申請
- 發布、修改及刪除自己的團主公告
- 查看團主 Dashboard

未完成公開資料時，只能進入團主資料設定功能。

---

## 5.4 Administrator Permissions

Administrator 可以：

- 查看簡化管理員 Dashboard
- 審核團主申請
- 管理活動
- 管理商品
- 在商品表單中搜尋、新增及維護角色
- 建立、修改及刪除平台公告

第一版不提供：

- 會員管理頁
- 團主管理頁
- 會員帳號停用
- 團主資格停用
- 任意修改團主名稱

---

## 5.5 Resource Ownership

| Resource | Owner Rule |
|---|---|
| Member Profile | 會員只能修改本人資料 |
| Favorite | 會員只能管理本人收藏 |
| Follow List | 會員只能管理本人跟團清單 |
| Member Order | 會員只能查看本人訂單 |
| Cancellation Request | 會員只能對本人訂單提出申請 |
| Group Buy | 團主只能管理本人建立的開團 |
| Group Leader Order | 團主只能管理本人開團的訂單 |
| Group Leader Announcement | 團主只能管理本人公告 |
| Private Member Contacts | 只有本人、該訂單團主及必要管理功能可查看 |

無權查看他人私人資源時，應避免透露該資源是否存在。

---

# 6. Registration and Authentication Rules

## 6.1 Registration Fields

註冊必須提供：

- Email
- 密碼
- 密碼確認
- 暱稱
- Facebook、Discord、LINE 至少一項私人聯絡方式

頭像非必填。

未上傳頭像時使用系統預設頭像。

---

## 6.2 Email Rules

| Rule ID | Rule |
|---|---|
| BR-AUTH-001 | Email 儲存前先 Trim。 |
| BR-AUTH-002 | Email 正規化為小寫。 |
| BR-AUTH-003 | Email 大小寫不敏感且不可重複。 |
| BR-AUTH-004 | 第一版會員不可自行修改 Email。 |
| BR-AUTH-005 | 登入錯誤不得透露 Email 是否存在。 |

---

## 6.3 Password Rules

密碼必須符合：

```text
長度 8～72 個字元
至少包含一個英文字母
至少包含一個數字
```

第一版不強制：

- 大寫英文字母
- 特殊符號
- 定期更換密碼

其他規則：

| Rule ID | Rule |
|---|---|
| BR-AUTH-006 | 密碼與密碼確認必須一致。 |
| BR-AUTH-007 | 後端只能保存安全雜湊，不得保存明文或可逆加密密碼。 |
| BR-AUTH-008 | 登入失敗統一顯示「Email 或密碼錯誤」。 |
| BR-AUTH-009 | API、Log 與錯誤內容不得回傳密碼或密碼雜湊。 |

---

## 6.4 Registration Result

註冊成功後（2026-07-28 使用者決議修訂）：

- 建立會員帳號
- 自動登入（前端以同一組帳密呼叫登入 API 取得 Token）
- 導向首頁
- 若註冊時選了頭像，於自動登入後上傳並套用；上傳失敗不影響帳號已建立的事實，
  改導向登入頁並提示可於個人資料頁重新設定

---

## 6.5 Access Token

第一版只使用 JWT Access Token。

規則：

```text
有效時間：8 小時
前端儲存：sessionStorage
Refresh Token：不提供
後端 Logout API：不提供
```

登出時由 React：

- 移除 Access Token
- 清除 AuthContext
- 回到公開頁或登入頁

---

## 6.6 Login Redirect

會員從受保護頁面被導向登入時，登入成功後應返回原本要前往的頁面。

Token 過期時：

1. 保留目前頁面的 `redirectPath`
2. 導向登入頁
3. 登入成功後返回原頁
4. 不自動重新送出下單、審核、刪除或狀態變更等敏感操作

---

# 7. Member Profile and Private Contact Rules

## 7.1 Editable Fields

會員可修改：

- 暱稱
- 頭像
- Facebook 聯絡方式
- Discord 聯絡方式
- LINE 聯絡方式

會員不可修改：

- Email
- Role
- 團主申請結果
- 團主公開資料欄位

---

## 7.2 Contact Requirement

會員私人聯絡方式在註冊及每次更新後，至少保留一項。

以下狀態不允許保存：

```text
facebook = null
discord = null
line = null
```

---

## 7.3 Private Contact Visibility

會員私人聯絡方式：

- 本人可查看
- 下單時保存至訂單聯絡快照
- 該訂單所屬團主可查看快照
- 公開頁不得回傳
- 不自動成為團主公開聯絡資料

---

## 7.4 Member Avatar Visibility

一般會員頭像：

- 本人可查看
- 訂單所屬團主可在必要訂單畫面查看
- 不建立一般會員公開個人頁

會員成為團主後，同一帳號頭像可顯示於團主公開頁。

---

## 7.5 Contact Snapshot

正式訂單建立時保存會員當下私人聯絡方式。

會員之後修改個人聯絡資料，不修改既有訂單快照。

---

# 8. Group Leader Application Rules

## 8.1 Application Input

團主申請第一版不要求：

- 團主公開名稱
- 團主公開聯絡方式
- 預設團規

申請操作只代表：

> 會員申請取得團主資格。

**申請原因（2026-07-28 使用者決議新增，原為「第一版不要求」）**

- 欄位：`group_leader_application.reason`（Text，可為 NULL）
- **選填**，上限 1000 字；空白字串正規化為 NULL（有值時不得為空白，以 CHECK 約束保證）
- 用途：供管理員審核時參考，會員可簡述開團經驗或想開團的商品類型
- 顯示位置：會員端申請狀態頁的「申請資料」卡、管理員審核頁的「申請說明」卡；
  未填寫時管理員審核頁顯示「此申請未提供額外說明。」
- 不影響任何審核邏輯：未填寫不構成拒絕理由，系統也不因此阻擋送出

---

## 8.2 Eligibility

會員可以申請的條件：

```text
目前沒有 group_leader_profile
AND
目前沒有 pending 申請
```

已有團主資料的會員不可再次申請。

---

## 8.3 One Pending Application

同一會員同時最多一筆：

```text
status = pending
```

保留歷史申請，但不允許同時送出第二筆待審核申請。

---

## 8.4 Reapplication

申請被拒絕後：

- 不設等待期間
- 可以再次申請
- 新申請建立新紀錄
- 舊申請結果繼續保留

---

## 8.5 Review

管理員可：

- 通過申請
- 拒絕申請

第一版不要求審核備註。

已審核申請不可再次審核。

---

## 8.6 Approval Result

通過時必須在同一 Transaction 中：

1. 確認申請仍為 `pending`
2. 確認會員尚無團主資料
3. 更新申請為 `approved`
4. 建立一筆不完整 `group_leader_profile`
5. 建立申請結果通知
6. Commit

剛通過時：

```text
display_name = null
公開聯絡方式可全部為 null
```

---

## 8.7 Rejection Result

拒絕時：

1. 確認申請仍為 `pending`
2. 更新申請為 `rejected`
3. 保存審核時間
4. 建立申請結果通知

拒絕不會建立團主資料。

---

## 8.8 Platform Rules for Group Leaders

**2026-07-28 使用者提供並決議：以下規範全文顯示於申請頁，會員須勾選確認後才能送出申請。**

團主平台規範：

1. 團主應提供正確的商品、價格、付款方式、截止時間及團購規則。
2. 開團後應依訂單送出順序處理訂單，不得任意調整會員順位。
3. 商品價格、付款方式與相關費用應清楚說明，不得刻意隱瞞額外費用。
4. 團主應妥善處理訂單確認、付款、出貨及取消申請。
5. 團主公開聯絡資訊需保持有效，方便團員聯繫。
6. 不得發布詐騙、違法、冒用或與團購無關的內容。
7. 若有重大異動，應及時透過公告通知受影響的團員。
8. 違反平台規範時，管理員得限制相關團主功能或進行必要處理。

實作對應：

- 規範全文顯示於申請頁右側「平台規範」區塊（純文字編號清單，不外連至獨立頁面）
- 申請頁的唯一勾選項為「我已確認並會遵守平台規範」，未勾選時送出按鈕停用
- 前端常數：`frontend/src/pages/member/GroupLeaderApplicationPage.jsx` 的 `PLATFORM_RULES`
- 第一版不將勾選結果另存欄位；勾選是送出前的前端閘門，本文件為規範的正式出處
- 第 8 條所述「限制相關團主功能」的具體機制第一版尚未實作
  （平台目前沒有帳號停權或功能限制功能），屬未來擴充

---

# 9. Group Leader Profile Rules

## 9.1 Profile Completion

團主資料完成條件：

```text
display_name 不為空
AND
facebook_url、discord_contact、line_contact 至少一項不為空
```

未完成時：

- 不公開團主頁
- 不可建立開團
- 不可發布公告
- 可進入團主資料設定頁
- 可修改介紹、預設團規與公開聯絡方式

---

## 9.2 Public Name

團主公開名稱規則：

| Rule ID | Rule |
|---|---|
| BR-LEADER-001 | 名稱 Trim 後不可為空。 |
| BR-LEADER-002 | 名稱大小寫不敏感且不可與其他團主重複。 |
| BR-LEADER-003 | 名稱第一次設定成功後不可修改。 |
| BR-LEADER-004 | 團主本人不可修改已設定名稱。 |
| BR-LEADER-005 | 管理員第一版也不可修改團主名稱。 |

名稱不可修改的目的：

- 避免舊公告與新名稱不一致
- 避免會員誤認為不同團主
- 避免歷史訂單與目前公開頁產生混淆

---

## 9.3 Editable Public Data

名稱完成後仍可修改：

- 團主介紹
- 預設團規
- Facebook 公開聯絡資料
- Discord 公開聯絡資料
- LINE 公開聯絡資料

每次更新後仍須至少保留一項公開聯絡方式。

---

## 9.4 Default Rules

預設團規：

- 顯示於團主公開頁
- 建立新開團時可用來預填
- 團主可以修改
- 修改後只影響未來預填內容
- 不修改既有開團團規
- 不修改既有訂單團規快照

每筆開團的正式規則仍以該開團保存的團規為準。

---

## 9.5 Public Profile Content

公開團主頁可顯示：

- 頭像
- 團主名稱
- 團主介紹
- 公開聯絡方式
- 成為團主時間
- 開團數
- 完成訂單數
- 預設團規
- 目前開團
- 公開的團主整體公告

第一版不顯示評價或星等。

---

# 10. Activity Rules

## 10.1 Dynamic Activities

活動代表實際官方活動，不使用固定活動分類。

例如：

```text
3.4 官方周邊
Solar5 主題周邊
潮聲信籤
墜夢奇境
予世新生
```

管理員每新增一筆活動，首頁就新增一張活動卡片。

---

## 10.2 Activity Fields

活動至少包含：

- 名稱
- 圖片
- 狀態
- 是否支援滿贈

說明可選填。

第一版不保存：

- 活動分類 Enum
- 活動開始日期
- 活動結束日期

---

## 10.3 Activity Status

狀態只有：

```text
open
ended
```

`open`：

- 顯示於目前活動
- 可建立新開團

`ended`：

- 顯示於已結束活動
- 可繼續瀏覽活動、商品、歷史開團與訂單
- 不可建立新開團

---

## 10.4 End and Reopen

管理員可將活動結束，也可重新開啟。

重新開啟後：

- 活動重新回到目前活動區
- 可再次建立新開團
- 原本仍為 `open`、未截止且未額滿的開團，移除活動結束造成的不可用條件
- 已提前結單的開團不會因此重新開啟

---

## 10.5 Activity Sorting

首頁分為：

```text
目前活動
已結束活動
```

兩區內皆依活動建立時間由新到舊排列。

---

## 10.6 Activity Name

活動名稱 Trim 後不可為空。

第一版不要求活動名稱全站唯一，因不同時期可能使用相似名稱。

---

# 11. Product Rules

## 11.1 Product Ownership

每項商品：

- 只能屬於一項活動
- 可關聯零至多名角色
- 可具有一張主要圖片及多張額外圖片

---

## 11.2 Product Required Data

商品至少需要：

- 活動
- 商品名稱
- 主要圖片

官方價格可依資料情況填寫，但填寫時：

```text
official_price >= 0
currency = TWD
```

---

## 11.3 Product Name

同一活動內不可建立兩筆完全相同的商品名稱。

不同款式應明確寫入名稱，例如：

```text
今汐壓克力立牌 A 款
今汐壓克力立牌 B 款
```

---

## 11.4 Product Status

商品使用：

```text
is_active = true / false
```

上架商品：

- 顯示於公開活動頁
- 顯示於公開搜尋
- 可加入有效開團與跟團清單

下架商品：

- 不顯示於一般公開商品列表與搜尋
- 既有收藏仍保留並標示「商品已下架」
- 歷史開團與訂單資料仍保留
- 既有失效跟團清單不自動刪除
- 不可建立新的有效下單內容

管理員可重新上架商品。

---

## 11.5 Product Card

活動頁的商品卡片只需顯示：

- 商品圖片
- 商品名稱

完整價格、角色及開團比較於商品詳情頁顯示。

---

# 12. Character Rules

## 12.1 Global Character Data

角色是全站共用資料，可跨活動關聯商品。

角色不直接隸屬某一活動。

---

## 12.2 Character Scope

第一版角色只保存名稱。

不保存：

- 角色圖片
- 武器
- 屬性
- 稀有度
- 生日
- 角色介紹

---

## 12.3 Character Search and Create

商品表單使用可搜尋、可新增的多選輸入。

例如輸入：

```text
今
```

應顯示符合的既有角色，例如：

```text
今汐
```

找不到完全相同名稱時，可顯示明確操作：

```text
新增角色「輸入名稱」
```

不得只按 Enter 就自動建立角色。

---

## 12.4 Character Validation

| Rule ID | Rule |
|---|---|
| BR-CHAR-001 | 角色名稱先 Trim。 |
| BR-CHAR-002 | Trim 後不可為空。 |
| BR-CHAR-003 | 角色名稱大小寫不敏感且不可重複。 |
| BR-CHAR-004 | 同一商品不可重複關聯同一角色。 |
| BR-CHAR-005 | 一項商品可關聯多名角色。 |

---

## 12.5 Character Maintenance

第一版不建立獨立角色管理頁或 Sidebar。

精簡維護功能可以：

- 修改角色名稱
- 查看關聯商品數
- 刪除沒有商品關聯的角色

已有商品關聯的角色不可刪除，需先移除全部商品關聯。

---

# 13. Image Rules

## 13.1 Supported Formats

支援上傳：

```text
JPG
JPEG
PNG
WebP
```

後端需驗證：

- Content Type
- 副檔名
- 實際檔案內容
- 儲存路徑
- 上傳權限
- 檔名安全性

---

## 13.2 File Size

產品業務規則不設定使用者可見的固定檔案大小限制。

因此前端不需要顯示：

```text
每張最多 5 MB
```

但伺服器必須保留可設定的安全上限，用於避免：

- 記憶體耗盡
- 磁碟空間被單一檔案占用
- 惡意或異常檔案造成服務中斷

安全上限屬於系統保護設定，不是固定產品規格。

超過伺服器安全上限時，回傳清楚的上傳失敗訊息。

---

## 13.3 Crop Area

需要固定顯示比例的圖片，上傳者必須能：

- 自由拖曳圖片
- 放大或縮小
- 自由選擇裁切範圍
- 預覽最終裁切結果
- 確認後再上傳

系統不得自行固定裁切中央區域而不讓使用者調整。

---

## 13.4 Display Ratios

| Image Type | Display / Crop Ratio |
|---|---|
| Member Avatar | 1:1 |
| Group Leader Public Avatar | 1:1 |
| Activity Image | 16:9 |
| Product Primary Image | 1:1 |
| Product Extra Image | 不強制固定比例 |

比例是最終顯示及裁切要求，不代表原始檔案必須先符合該比例。

---

## 13.5 Image Conversion

上傳完成後，系統可以轉換為 WebP 保存。

轉換不得造成：

- 圖片方向錯誤
- 裁切範圍改變
- 明顯無法辨識的品質下降

---

## 13.6 Upload Permissions

| Category | Permission |
|---|---|
| Avatar | 已登入會員，只能用於本人資料 |
| Activity | Administrator |
| Product | Administrator |

---

## 13.7 Extra Image Ordering

商品額外圖片：

- 可新增
- 可刪除
- 可上移
- 可下移

第一版不要求拖曳排序。

後端依前端送出的完整圖片 ID 排列更新 `sort_order`。

---

## 13.8 Product Image Viewer

商品詳情圖片應支援：

- 點擊放大
- 左右切換
- Thumbnail 選擇
- 鍵盤方向鍵
- 手機水平滑動

---

# 14. Public Browsing and Search Rules

## 14.1 Homepage

首頁：

- 顯示網站名稱與一句用途說明
- 不使用輪播圖
- 不設 Footer
- 顯示目前活動及已結束活動
- 活動圖片比例為 16:9

---

## 14.2 Global Search Scope

全站搜尋只搜尋：

- 活動名稱
- 商品名稱
- 角色名稱

不搜尋：

- 一般會員
- 團主名稱
- 訂單
- 公告
- 團規
- 聯絡方式

---

## 14.3 Search Input

搜尋文字 Trim 後不可為空。

搜尋應支援部分文字，例如：

```text
今
```

可以找到：

- 名稱包含「今」的活動
- 名稱包含「今」的商品
- 名稱包含「今」的角色

---

## 14.4 Search Result Sections

搜尋結果在同一頁分成：

```text
活動
商品
角色
```

不使用 Tabs。

每一區：

- 顯示自己的總筆數
- 使用自己的頁碼與分頁
- 可獨立查看更多
- 不與另外兩區共用一組 `total_items`

---

## 14.5 Public Product Visibility

公開搜尋與活動商品列表只顯示上架商品。

角色結果點入後，只顯示目前可公開瀏覽的上架商品。

---

## 14.6 Public Group Leader Visibility

只有完成公開資料的團主才有公開頁。

公開頁不得回傳會員私人聯絡方式。

---

## 14.7 Breadcrumb

具有明確層級的公開頁保留麵包屑，例如：

```text
首頁 / 活動 / 商品
首頁 / 商品 / 開團詳情
```

---

# 15. Group Buy Creation Rules

## 15.1 Creator Eligibility

建立開團必須符合：

```text
已登入
AND
具有 group_leader_profile
AND
團主公開資料已完成
```

---

## 15.2 Activity Selection

建立流程先選擇一項：

```text
status = open
```

的活動。

已結束活動不可建立新開團。

---

## 15.3 Product Selection

一筆開團：

- 至少包含一項商品
- 商品不得重複
- 所有商品必須屬於所選活動
- 所有商品建立當下必須為上架狀態

---

## 15.4 Product Settings

每個開團商品必須設定：

- 團主售價
- 接單上限

規則：

```text
unit_price >= 0
max_quantity > 0
currency = TWD
```

---

## 15.5 Payment Methods

付款方式支援：

```text
bank_transfer
cash_on_delivery
other
```

顯示文字可對應：

- 匯款（`bank_transfer`）
- 取貨付款（`cash_on_delivery`）

> 變更紀錄（2026-07-27）：依使用者決議移除 `other` 付款方式。

付款方式備註（`payment_method_note`）：

- 選填，任何付款方式皆可填寫
- 例如「團費確認後再私訊告知匯款帳號」「取貨地點與時間」
- Trim 後為空一律存 NULL，不顯示於前台

---

## 15.6 Second Payment

`requires_second_payment` 表示團主是否預期後續需要二補。

此欄位只提供資訊，不代表平台會：

- 計算二補
- 收取二補
- 追蹤二補付款

---

## 15.7 Full Gift

`includes_full_gift = true` 只允許在：

```text
activity.has_full_gift = true
```

時設定。

活動不支援滿贈時，開團不得宣告包含滿贈。

---

## 15.8 Deadline

收單期限：

- 必填
- 必須晚於建立當下時間
- 以 UTC 保存
- 前端以 Asia/Taipei 顯示

---

## 15.9 Rules and Contact

每筆開團必須提供：

- 完整團規
- 主要聯絡平台
- 主要聯絡內容

團規及聯絡內容 Trim 後不可為空。

開團聯絡方式可以作為該團的正式聯絡快照，不要求與團主公開頁目前聯絡資料完全相同。

---

## 15.10 No Draft

第一版開團建立後立即成為：

```text
status = open
```

不提供：

- 草稿
- 排程發布
- 審核後發布

---

# 16. Group Buy Edit and Status Rules

## 16.1 Formal Order Existence

判斷開團是否已有正式訂單時，只要存在任何 `group_order` 紀錄就視為已有正式訂單。

即使該訂單之後成為：

```text
cancelled
rejected
```

也不恢復成「從未有訂單」狀態。

---

## 16.2 Edit Before Any Formal Order

沒有任何正式訂單時，可修改全部內容，包括：

- 活動
- 商品集合
- 各商品售價
- 各商品接單上限
- 付款方式
- 付款方式備註
- 是否二補
- 是否包含滿贈
- 收單期限
- 團規
- 主要聯絡方式

修改後仍需重新符合所有建立規則。

---

## 16.3 Edit After Formal Order Exists

已有正式訂單後，只可修改：

- 收單期限
- 主要聯絡平台
- 主要聯絡內容
- 各商品接單上限

不可修改：

- 活動
- 商品集合
- 商品售價
- 付款方式
- 付款方式備註
- 是否二補
- 是否包含滿贈
- 團規

目的為保護已建立訂單的公平性與歷史理解。

---

## 16.4 Quantity Limit Update

接單上限可因官方後續限制而調整。

新上限必須：

```text
new_max_quantity >= occupied_quantity
```

否則拒絕修改。

---

## 16.5 Deadline Update

修改後的截止時間不得早於目前時間。

已有訂單後可以延長或縮短期限，但不得將期限改到過去。

實務上「提早收單」比延後更常見（數量不足或其他因素），因此介面不得只提示可延後。
要立即停止收單請用 §16.6 提前結單，而非把期限改到過去。

---

## 16.5a Contact Method Source

開團的主要聯絡方式**必須取自團主資料已設定的公開聯絡方式**，不在開團另外輸入
（使用者 2026-07-29 裁決）。

- 團主資料未設定該平台 → 拒絕，並提示需先於團主資料填寫
- 送出的聯絡內容與團主資料不符 → 拒絕，需改到團主資料修改
- 只切換平台時，系統自動採用團主資料該平台的值

理由：同一位團主若能在各開團各填一組聯絡方式，資訊會分散且容易過期；集中在團主資料
只需維護一份。

Facebook 一律必須是個人頁連結（不接受只填帳號名稱），此規則於會員聯絡欄位、
團主公開聯絡方式、開團主要聯絡方式三處共用同一份實作。

---

## 16.6 Close Group Buy

團主可以提前結單。

結單後：

```text
status = closed
closed_at = now()
```

結果：

- 不接受新跟團項目
- 不接受正式送單
- 既有訂單繼續處理
- 歷史資料仍可查看
- 第一版不可重新開啟

---

## 16.7 Effective Status

開團實際可用狀態由系統計算：

```text
open
closed
expired
activity_ended
full
```

不直接保存 `effective_status`。

判斷順序需能清楚回傳主要不可用原因。

---

## 16.8 Product-Level Availability

某項開團商品可接受新訂單，至少需要：

```text
group_buy.status = open
activity.status = open
deadline_at > now()
product.is_active = true
available_quantity > 0
```

其中任一不成立，該項目不可正式送單。

---

# 17. Group Buy Comparison Rules

## 17.1 Default Sorting

商品頁的開團比較預設：

```text
開團建立時間：新到舊
```

---

## 17.2 Optional Sorting

使用者可以選擇：

```text
價格：低到高
價格：高到低
截止時間：近到遠
截止時間：遠到近
```

第一版不要求提供開團時間舊到新。

---

## 17.3 Filters

商品頁開團比較支援：

- 只顯示目前可跟團
- 付款方式（下拉選單，預設不限）
- 是否需要二補
- 是否包含滿贈

付款方式篩選對應：

```text
payment_method 未帶     → 不篩選（預設「不限」）
payment_method = cash_on_delivery → 只顯示取貨付款
payment_method = bank_transfer    → 只顯示匯款
```

---

## 17.4 No Additional First-Version Filters

第一版不需要：

- 團主名稱篩選
- 聯絡平台篩選
- 商品數量區間篩選

避免篩選介面過度複雜。

---

## 17.5 Remaining Quantity Display

公開頁可顯示查詢當下：

```text
剩餘 N 個
```

但必須同時表達：

> 顯示數量不代表保留，正式送單時仍會重新檢查。

---

# 18. Follow List Rules

## 18.1 One Member, One List

一名會員同時最多一張跟團清單。

一張清單只能屬於一筆開團。

因此同一張清單自然只包含：

- 一名團主
- 一項活動
- 一套付款方式
- 一套團規
- 一項主要聯絡方式

---

## 18.2 Add Same Product

同一開團的相同商品再次加入時：

```text
new_quantity
=
current_quantity
+
added_quantity
```

不得建立第二筆重複項目。

---

## 18.3 Add Different Product in Same Group Buy

同一開團的新商品可直接加入現有清單。

---

## 18.4 Add Product from Different Group Buy

目前清單屬於其他開團時，不可直接混合。

前端需詢問是否替換。

確認替換後，後端在同一 Transaction 中：

1. 驗證新商品仍可加入
2. 刪除舊清單
3. 建立新清單
4. 建立新項目
5. Commit

新清單建立失敗時，舊清單不得遺失。

---

## 18.5 Quantity

清單項目數量必須：

```text
quantity > 0
```

修改數量使用絕對數量，不是增加量。

---

## 18.6 No Reservation

跟團清單：

- 不占用接單上限
- 不保留商品
- 不建立訂單順序
- 不保證稍後仍有相同剩餘數量

---

## 18.7 Invalid List Retention

以下情況發生時，既有清單不自動刪除：

- 開團提前結單
- 開團截止
- 活動結束
- 商品下架
- 剩餘數量不足
- 其他導致不可送單的狀態

會員仍可：

- 查看失效原因
- 修改數量
- 移除單項
- 清空清單

但不可正式送出。

---

## 18.8 Empty List

刪除最後一項時，同時刪除空的跟團清單。

---

# 19. Order Creation Rules

## 19.1 Rules Confirmation

送出訂單前，會員必須明確勾選：

```text
已閱讀並同意本次團規
```

未勾選不得建立訂單。

確認內容應顯示於完整頁面區塊，不依賴難以閱讀的小型 Modal。

---

## 19.2 Source Data

正式訂單只能從會員目前的跟團清單建立。

前端不得決定或提交：

- 商品單價
- 小計
- 商品總額
- 商品名稱
- 商品圖片
- 團主名稱
- 活動名稱
- 團規快照
- 付款方式快照
- 聯絡方式快照

後端重新查詢並計算。

---

## 19.3 Submission Validation

建立前至少確認：

- 清單存在且不為空
- 清單屬於目前會員
- 已確認團規
- 開團仍可接受訂單
- 活動仍為 open
- 商品仍上架
- 截止時間未到
- 每項數量大於零
- 每項剩餘數量足夠
- 團主售價使用目前正式資料
- 會員仍至少有一項私人聯絡方式

---

## 19.4 Atomic Creation

正式下單必須為全有或全無：

- 所有商品皆成功，才建立完整訂單
- 任一商品失敗，不建立部分訂單
- 失敗時保留完整跟團清單

---

## 19.5 Success Result

成功後：

1. 建立一張新的獨立訂單
2. 建立所有訂單明細
3. 保存必要快照
4. 訂單狀態為 `pending_confirmation`
5. 清空跟團清單
6. 回傳訂單編號及商品總額

---

## 19.6 Historical Snapshot

訂單需保存下單當時的：

- 團主名稱
- 活動名稱
- 付款方式
- 付款方式備註
- 是否二補
- 是否包含滿贈
- 團規
- 團主主要聯絡方式
- 會員私人聯絡方式
- 商品名稱
- 商品主要圖片
- 商品單價
- 商品數量
- 商品小計

後續資料變更不得改寫既有訂單快照。

---

## 19.7 Multiple Orders

同一會員可以對同一開團再次下單。

每次送出都必須：

- 建立全新訂單
- 使用新訂單編號
- 保存新的送出時間
- 保存新的資料快照
- 不與舊訂單合併

---

## 19.8 Representative Image

訂單列表代表圖片使用第一筆訂單明細的圖片快照。

---

# 20. Quantity and Queue Priority Rules

## 20.1 Occupied Quantity

某開團商品的已占用數量：

```text
所有 status 不為 cancelled 或 rejected 的訂單明細數量總和
```

包含：

```text
pending_confirmation
pending_payment
paid
shipped
completed
```

---

## 20.2 Available Quantity

```text
available_quantity
=
max_quantity
-
occupied_quantity
```

`available_quantity` 不直接保存於資料庫。

---

## 20.3 Release Quantity

訂單變成以下狀態時釋放占用數量：

```text
cancelled
rejected
```

`completed` 不釋放，因為該數量已完成交易流程。

---

## 20.4 First-Come Priority

同一開團的團主訂單處理順序：

```text
created_at ASC, id ASC
```

較早建立的訂單排在前面。

若建立時間相同，以 `id ASC` 作為穩定排序。

---

## 20.5 Added Order Priority

會員第二次加喊：

- 必須建立第二張訂單
- 必須排在第一次訂單後面
- 不可將新商品合併回第一張訂單
- 只能使用第二次送單當下仍可接受的數量

---

## 20.6 Client Time Not Used

先喊順序使用伺服器／資料庫建立時間，不使用使用者裝置時間。

---

## 20.7 Concurrent Submission

兩名會員同時送出時：

- 後端鎖定相關開團商品
- 依 Transaction 實際成功順序建立訂單
- 後取得鎖定者需使用更新後剩餘數量重新驗證
- 數量不足者整筆失敗並保留跟團清單

---

# 21. Order Status Rules

## 21.1 Status Set

訂單狀態：

```text
pending_confirmation
pending_payment
paid
shipped
completed
cancelled
rejected
```

---

## 21.2 Status Transition Matrix

| Current Status | Action | Next Status | Actor |
|---|---|---|---|
| pending_confirmation | Accept Order | pending_payment | Group Leader |
| pending_confirmation | Reject Order | rejected | Group Leader |
| pending_payment | Mark Paid | paid | Group Leader |
| paid | Mark Shipped | shipped | Group Leader |
| shipped | Complete Order | completed | Group Leader |
| pending_confirmation / pending_payment / paid | Approve Cancellation | cancelled | Group Leader |

未列出的直接轉換全部禁止。

---

## 21.3 Accept Order

接受訂單只允許：

```text
pending_confirmation → pending_payment
```

接受後建立會員通知。

---

## 21.4 Reject Order

拒絕只允許：

```text
pending_confirmation → rejected
```

拒絕原因：

- 必填
- Trim 後不可為空
- 拒絕後不可修改

拒絕後：

- 訂單不可恢復
- 不可接受
- 不進入付款流程
- 不占用數量
- 保留歷史資料
- 建立會員通知

---

## 21.5 Mark Paid

只允許：

```text
pending_payment → paid
```

平台只記錄團主確認的狀態，不處理實際金流驗證。

---

## 21.6 Mark Shipped

只允許：

```text
paid → shipped
```

第一版不保存物流單號或物流商。

---

## 21.7 Complete Order

只允許：

```text
shipped → completed
```

完成後：

- 保留數量占用
- 不再列入團主公告未完成訂單通知對象
- 不可申請取消

---

## 21.8 Status Conflict

前端畫面仍顯示可操作，但後端發現狀態已變更時：

- 不執行操作
- 回傳目前狀態
- 前端重新載入訂單

---

# 22. Cancellation Request Rules

## 22.1 Allowed Order Statuses

會員可對以下訂單提出取消申請：

```text
pending_confirmation
pending_payment
paid
```

---

## 22.2 Disallowed Order Statuses

不可對以下狀態提出：

```text
shipped
completed
cancelled
rejected
```

---

## 22.3 Optional Reason

會員取消原因選填。

空白字串正規化為 `null`。

---

## 22.4 Pending Limit

同一訂單同時最多一筆：

```text
cancellation_request.status = pending
```

已有待處理申請時，不可再建立第二筆。

---

## 22.5 Order Status During Request

建立取消申請時：

- 訂單狀態保持原狀
- 不立即釋放數量
- 不代表已取消
- 團主訂單列表標示有待處理申請

---

## 22.6 Approval

團主同意前需重新確認訂單目前仍可取消。

成功後：

```text
cancellation_request.status = approved
group_order.status = cancelled
processed_at = now()
```

並：

- 釋放訂單占用數量
- 建立會員通知
- 不可再次提出取消申請

團主回覆選填。

---

## 22.7 Rejection

拒絕後：

```text
cancellation_request.status = rejected
group_order.status = 原狀態
processed_at = now()
```

團主回覆選填。

---

## 22.8 Reapply After Rejection

先前取消申請被拒絕後，只要：

- 訂單目前仍為允許取消的狀態
- 沒有另一筆待處理申請

會員即可再次提出新申請。

每次申請保留獨立歷史紀錄。

---

## 22.9 Cancellation History

訂單詳情顯示：

- 所有取消申請歷史
- 目前待處理申請
- 每筆申請原因
- 團主回覆
- 申請與處理時間

---

# 23. Favorite Rules

## 23.1 Favorite Target

第一版只收藏商品。

不收藏：

- 活動
- 開團
- 團主
- 公告

---

## 23.2 Unique Favorite

同一會員對同一商品最多一筆收藏。

重複收藏不得建立重複資料。

---

## 23.3 Remove Favorite

取消收藏可直接刪除收藏關聯。

未收藏時重複取消，可視為成功。

---

## 23.4 Inactive Product

商品下架後：

- 收藏關聯保留
- 收藏頁仍顯示商品
- 明確標示「商品已下架」
- 不可從收藏頁直接建立無效跟團內容

---

# 24. Group Leader Announcement Rules

## 24.1 Eligibility

發布團主公告需要：

```text
具有 group_leader_profile
AND
團主公開資料已完成
```

---

## 24.2 Announcement Scopes

團主公告有兩種通知範圍。

### Leader Unfinished

```text
leader_unfinished
```

通知：

> 曾加入該團主，且目前在該團主名下至少有一筆未完成訂單的會員。

### Group Buy Unfinished

```text
group_buy_unfinished
```

通知：

> 指定開團中至少有一筆未完成訂單的會員。

指定開團必須屬於目前團主。

---

## 24.3 Recipient Order Statuses

包含：

```text
pending_confirmation
pending_payment
paid
shipped
```

排除：

```text
completed
cancelled
rejected
```

---

## 24.4 Recipient Deduplication

同一會員即使有：

- 多張訂單
- 多項商品
- 多次加喊

同一公告仍只建立一則通知。

---

## 24.5 Public Visibility

團主可選擇：

```text
is_public = true / false
```

公開只影響公開頁顯示，不改變通知對象。

`leader_unfinished` 公開公告顯示於團主公開頁。

`group_buy_unfinished` 公開公告顯示於指定開團公開頁。

---

## 24.6 Zero Recipient Rule

通知對象為零時：

| Visibility | Result |
|---|---|
| Public | 允許發布 |
| Not Public | 阻止發布 |

原因：

- 公開公告仍可供公開頁訪客閱讀
- 不公開公告沒有收件人時，任何人都看不到

將既有零收件人的公開公告改成不公開時，也必須遵守相同規則。

---

## 24.7 Required Content

公告標題及內容：

- 必填
- Trim 後不可為空
- 使用純文字
- 保留換行
- 不執行 HTML

---

## 24.8 No Draft or Schedule

公告建立後立即發布。

第一版不提供：

- 草稿
- 排程發布
- 自動到期

---

## 24.9 Edit

團主可修改自己的公告：

- 標題
- 內容
- 是否公開

不可修改：

- 公告範圍
- 指定開團
- 發布者
- 發布時間

修改後：

- 同步更新公告
- 同步更新該公告產生的通知標題與內容
- 不重新建立通知
- 不重設通知已讀狀態
- 不改變原收件人集合

---

## 24.10 Delete

團主可刪除自己的公告。

刪除時：

- 刪除公告
- 刪除該公告建立的通知
- 不刪除訂單通知
- 不刪除申請結果通知
- 不刪除其他公告通知

第一版不提供公告停用。

---

# 25. Platform Announcement Rules

## 25.1 Publisher

只有 Administrator 可以建立平台公告。

---

## 25.2 Recipients

平台公告通知所有已註冊會員帳號。

同一平台公告對同一會員只建立一則通知。

---

## 25.3 Public Page

平台公告：

- 不建立獨立公開列表
- 不建立獨立公開詳情頁
- 主要顯示於會員通知中心

---

## 25.4 Edit

管理員可修改平台公告標題與內容。

修改後：

- 同步更新該公告產生的通知
- 不建立第二批通知
- 不重設已讀狀態

---

## 25.5 Delete

管理員可刪除平台公告。

刪除時只刪除：

- 該平台公告
- 該公告產生的通知

---

# 26. Notification Rules

## 26.1 Notification Sources

通知只對應一個來源：

- 訂單
- 公告
- 團主申請

不得同時指向兩個來源。

---

## 26.2 Notification Types

通知可區分：

```text
system
group_leader
```

平台公告、訂單狀態與申請結果可使用系統通知。

團主公告使用團主通知。

---

## 26.3 Read Status

新通知：

```text
is_read = false
read_at = null
```

標記已讀後：

```text
is_read = true
read_at = 第一次標記時間
```

重複標記已讀不更新原 `read_at`。

---

## 26.4 User Actions

會員可以：

- 查看通知列表
- 篩選已讀或未讀
- 標記單筆已讀
- 全部標記已讀
- 點擊前往相關頁面

會員不可一般性刪除通知。

---

## 26.5 Navigation

點擊通知依來源導向：

| Source | Target |
|---|---|
| Order | 會員訂單詳情 |
| Group Leader Application | 團主申請狀態或個人資料頁 |
| Public Leader Announcement | 團主公開頁 |
| Public Group Buy Announcement | 開團公開頁 |
| Private Announcement | 通知中心中的通知內容 |
| Platform Announcement | 通知中心中的通知內容 |

---

## 26.6 Announcement Synchronization

公告被修改：

- 更新相關通知標題與訊息
- 保留通知 ID
- 保留建立時間
- 保留已讀狀態

公告被刪除：

- 刪除該公告相關通知

---

# 27. Administrator Rules

## 27.1 Dashboard

管理員 Dashboard 第一版只顯示：

- 待審核團主申請數
- 進行中活動數
- 上架商品數
- 目前開團數
- 對應管理頁快速入口

第一版不要求圖表。

---

## 27.2 Group Leader Application Review

管理員：

- 依較早申請優先顯示
- 可查看會員基本資料及申請狀態
- 可通過或拒絕
- 不要求輸入審核備註
- 不可重複審核同一申請

---

## 27.3 Activity Management

管理員可：

- 建立活動
- 修改活動名稱、說明、圖片及滿贈設定
- 結束活動
- 重新開啟活動

活動不使用固定分類。

---

## 27.4 Product Management

管理員可：

- 建立商品
- 修改商品
- 上架或下架商品
- 管理主要圖片
- 管理額外圖片
- 調整額外圖片順序
- 關聯角色

---

## 27.5 Character Support

角色功能服務於商品管理。

管理員可透過商品表單：

- 搜尋既有角色
- 明確新增角色
- 編輯角色名稱
- 刪除無商品關聯角色

第一版沒有獨立角色管理頁。

---

## 27.6 Platform Announcement Management

管理員可：

- 查看平台公告
- 建立平台公告
- 修改平台公告
- 刪除平台公告

不提供停用或重新啟用。

---

## 27.7 Removed Administration Scope

第一版不提供：

- 會員列表管理
- 會員詳情管理
- 團主列表管理
- 團主詳情管理
- 停用會員
- 停用團主
- 修改團主名稱

---

# 28. Money, Time and Display Rules

## 28.1 Currency

所有第一版金額固定使用：

```text
TWD
```

不提供幣別切換或匯率換算。

---

## 28.2 Money Calculation

後端使用 Decimal。

資料庫使用：

```text
NUMERIC(12,2)
```

API 以字串傳輸金額。

---

## 28.3 Product Total Label

畫面統一顯示：

```text
商品總額
```

不得只顯示「總額」而讓會員誤以為包含全部後續費用。

---

## 28.4 Excluded Fees

商品總額不包含：

- 二補
- 國際運費
- 國內運費
- 超商或宅配費
- 其他團主後續費用

---

## 28.5 Time Storage

後端與資料庫保存 UTC。

前端以：

```text
Asia/Taipei
```

轉換顯示。

---

## 28.6 Server Time

截止時間、送單順序、審核時間及狀態變更時間以伺服器時間為準。

---

## 28.7 Default List Sorting

除非另有規定：

```text
created_at DESC
```

例外：

- 待審核團主申請：`created_at ASC`
- 團主訂單處理列表：`created_at ASC, id ASC`
- 首頁活動各區：`created_at DESC`
- 商品頁開團比較：預設 `created_at DESC`

---

# 29. Validation and Error Rules

## 29.1 Validation Layers

同一規則可以同時在：

- React 表單
- Pydantic Schema
- Service Layer
- Database Constraint

進行驗證。

前端驗證不得取代後端驗證。

---

## 29.2 Field Validation

欄位錯誤應指出：

- 哪一個欄位錯誤
- 可理解的錯誤訊息

不得將原始資料庫錯誤直接顯示給使用者。

---

## 29.3 State Conflict

以下情況使用狀態衝突處理：

- 訂單已被其他操作更新
- 申請已被審核
- 開團已結單
- 數量已被其他訂單占用
- 接單上限低於占用數量
- 取消申請已處理
- 跟團清單已變更

前端收到衝突後重新取得最新資料。

---

## 29.4 Ownership Error

存取他人私人訂單或資源時，建議回傳：

```text
404 Not Found
```

避免透露資源存在。

---

## 29.5 Loading and Duplicate Submission

下列操作提交時必須停用重複按鈕：

- 註冊
- 登入
- 替換跟團清單
- 正式下單
- 接受或拒絕訂單
- 更新訂單狀態
- 處理取消申請
- 發布、修改或刪除公告
- 審核團主申請
- 建立或更新開團

---

## 29.6 Plain Text

以下內容使用純文字：

- 團規
- 團主介紹
- 公告
- 取消原因
- 團主回覆
- 訂單拒絕原因
- 付款方式補充說明

保留換行，但不接受任意 HTML。

---

# 30. Transaction and Concurrency Rules

## 30.1 Required Transactions

以下操作必須使用 Transaction：

- 註冊會員
- 通過團主申請
- 拒絕團主申請
- 建立開團
- 無訂單開團商品集合修改
- 替換跟團清單
- 建立正式訂單
- 接受訂單
- 拒絕訂單
- 更新訂單狀態
- 同意取消申請
- 拒絕取消申請
- 建立團主公告及通知
- 建立平台公告及通知
- 修改公告與相關通知
- 刪除公告與相關通知

---

## 30.2 Order Creation Locks

建立訂單時至少鎖定：

- 跟團清單
- 開團
- 所有相關開團商品

多項商品依固定 ID 順序鎖定，降低 Deadlock 風險。

---

## 30.3 Quantity Recheck

取得鎖定後重新：

1. 計算占用數量
2. 計算剩餘數量
3. 驗證全部商品
4. 建立訂單

不得使用鎖定前的剩餘數量直接建立訂單。

---

## 30.4 Rollback

Transaction 任一步失敗：

- 全部 Rollback
- 不建立部分資料
- 不清空跟團清單
- 不建立部分通知
- 不留下半完成狀態

---

## 30.5 Announcement Atomicity

發布公告時：

- 公告與全部通知同一 Transaction
- 任一必要寫入失敗時全部 Rollback

修改公告時：

- 公告與其通知內容同一 Transaction

刪除公告時：

- 公告與該公告通知同一 Transaction 或由 Foreign Key Cascade 保證一致

---

# 31. Privacy and Security Rules

## 31.1 Authentication

所有受保護 API 必須驗證：

- JWT 簽章
- JWT 到期時間
- 使用者存在
- 必要角色或團主資料
- 資源擁有權

不得只相信 Token 中的角色宣告。

---

## 31.2 Private Contacts

公開 API 不得回傳：

- 一般會員 Email
- 會員私人 Facebook
- 會員私人 Discord
- 會員私人 LINE
- 會員訂單以外的私人聯絡資料

---

## 31.3 Group Leader Public Contacts

團主公開聯絡資料由團主主動填寫。

不得從會員私人聯絡方式自動複製。

---

## 31.4 File Upload Security

檔案上傳需防止：

- 路徑穿越
- 偽造副檔名
- 偽造 MIME Type
- 使用原始檔名覆蓋其他檔案
- 異常巨大檔案耗盡資源
- 未授權類別上傳

---

## 31.5 HTML and XSS

後端不處理任意 HTML。

前端不得使用未經處理的：

```text
dangerouslySetInnerHTML
```

顯示使用者文字。

---

## 31.6 Sensitive Logs

Log 不得記錄：

- 完整 Access Token
- 明文密碼
- 密碼雜湊
- 不必要的私人聯絡資料
- 完整上傳檔案內容

---

# 32. Data Retention and Delete Rules

## 32.1 Preserve Historical Business Data

一般功能不得任意 Hard Delete：

- 會員帳號
- 團主申請
- 團主資料
- 活動
- 商品
- 開團
- 開團商品
- 訂單
- 訂單明細
- 取消申請

---

## 32.2 Status-Based Retention

| Resource | Removal Method |
|---|---|
| Activity | ended |
| Product | is_active = false |
| Group Buy | closed |
| Order | 狀態流程，不刪除 |

---

## 32.3 Directly Deletable Data

可以依規則刪除：

- 跟團清單
- 跟團清單項目
- 商品收藏
- 商品額外圖片
- 商品角色關聯
- 沒有商品關聯的角色
- 團主公告
- 平台公告
- 公告所產生的通知

---

## 32.4 Notification Retention

會員不可自行刪除通知。

例外：

> 公告刪除時，系統一併刪除由該公告建立的通知。

訂單及團主申請通知不因其他公告刪除而受影響。

---

## 32.5 Order Snapshot Retention

商品、活動、團主資料或聯絡方式後續修改時，不修改舊訂單快照。

---

# 33. First Version Scope Boundaries

## 33.1 Included

第一版包含：

- 公開活動、商品與角色搜尋
- 商品開團比較
- 會員註冊與登入
- 私人聯絡方式
- 商品收藏
- 跟團清單
- 正式訂單
- 訂單狀態管理
- 取消申請
- 團主申請與資料
- 團主開團
- 團主及平台公告
- 通知中心
- 管理員活動、商品及申請管理

---

## 33.2 Excluded

第一版不包含：

- 站內付款
- 自動對帳
- 退款
- 二補金額管理
- 國際運費計算
- 國內物流費計算
- 物流單號
- 宅配追蹤
- 站內聊天
- 私訊
- 評價
- 星等
- 盲盒拆分
- 熱度定價
- 商品規格變體
- 多遊戲支援
- App
- Refresh Token
- 帳號停用
- 團主資格停用
- 公告停用
- 通知刪除
- 開團草稿
- 已結單開團重新開啟

---

# 34. Business Rule Acceptance Checklist

## 34.1 Registration

- [ ] 密碼 8～72 字元，至少一個英文字母及一個數字
- [ ] 暱稱必填
- [ ] 至少一項私人聯絡方式
- [ ] 頭像選填並有預設頭像
- [ ] 註冊需通過 Email 驗證碼
- [ ] 註冊成功後自動登入並導向首頁
- [ ] Email 不可由會員修改

---

## 34.2 Group Leader

- [ ] 同時最多一筆待審核申請
- [ ] 申請不要求原因、名稱或公開聯絡方式
- [ ] 拒絕後可重新申請
- [ ] 通過後建立不完整團主資料
- [ ] 完成名稱與公開聯絡方式後才可開團
- [ ] 團主名稱設定後不可修改
- [ ] 團主名稱大小寫不敏感且不可重複

---

## 34.3 Activity and Product

- [ ] 活動不使用固定分類
- [ ] 新增活動後首頁自動顯示
- [ ] 活動可結束及重新開啟
- [ ] 商品價格固定 TWD
- [ ] 同活動商品名稱不可重複
- [ ] 下架商品保留收藏及歷史資料
- [ ] 角色可跨活動使用
- [ ] 有商品關聯的角色不可刪除

---

## 34.4 Image

- [ ] 支援 JPG、PNG、WebP
- [ ] 前端不顯示固定檔案大小限制
- [ ] 伺服器保留安全上限
- [ ] 使用者可自由選擇裁切範圍
- [ ] 頭像與商品主要圖片為 1:1
- [ ] 活動圖片為 16:9
- [ ] 額外圖片不強制比例
- [ ] 額外圖片可上移及下移

---

## 34.5 Group Buy

- [ ] 只有完成團主公開資料才能開團
- [ ] 先選 open 活動
- [ ] 至少一項同活動上架商品
- [ ] 支援匯款與取貨付款兩種付款方式
- [ ] 付款方式備註為選填，任何付款方式皆可填寫
- [ ] 同一團主對同一活動同時只能有一個進行中的開團
- [ ] 沒有訂單時全部內容可修改
- [ ] 有訂單後只可改期限、聯絡方式與上限
- [ ] 上限不可低於占用數量
- [ ] 結單後不可重新開啟

---

## 34.6 Follow List and Order

- [ ] 一名會員同時一張跟團清單
- [ ] 同商品再次加入時累加數量
- [ ] 不同開團需 Transaction 替換
- [ ] 失效清單不自動刪除
- [ ] 跟團清單不保留數量
- [ ] 下單前確認團規
- [ ] 下單時重新計算全部資料
- [ ] 失敗時保留清單
- [ ] 成功後才清空清單
- [ ] 每次加喊建立獨立訂單
- [ ] 團主訂單依先喊順序排列

---

## 34.7 Order and Cancellation

- [ ] 訂單狀態只能依指定流程更新
- [ ] 拒絕原因必填且不可修改
- [ ] 拒絕或取消訂單釋放數量
- [ ] 商品總額不包含後續費用
- [ ] 可取消狀態為待確認、待付款、已付款
- [ ] 已出貨後不可申請取消
- [ ] 同時最多一筆待處理取消申請
- [ ] 被拒絕後符合條件可再次申請

---

## 34.8 Announcement and Notification

- [ ] 團主公告有整體及指定開團兩種範圍
- [ ] 只通知未完成訂單會員
- [ ] 同會員同公告只收到一次
- [ ] 公開公告零收件人可發布
- [ ] 不公開公告零收件人不可發布
- [ ] 修改公告同步更新通知
- [ ] 刪除公告只刪除該公告通知
- [ ] 平台公告沒有獨立公開頁
- [ ] 會員不可一般性刪除通知
- [ ] 通知可單筆及全部標記已讀

---

# 35. Final Business Decisions

1. WuWaGroup 第一版為資訊整合與跟團管理平台，不是完整電商平台。
2. Visitor 可瀏覽公開內容，Member 才能收藏、建立清單及下單。
3. 團主不是獨立帳號或 Role，而是具有 `group_leader_profile` 的會員。
4. 管理員不自動具有團主功能。
5. 註冊必須提供暱稱與至少一項私人聯絡方式，頭像選填。
6. 密碼長度為 8～72 字元，至少包含一個英文字母及一個數字。
7. Email 大小寫不敏感且不可重複，第一版不可由會員修改。
8. 註冊成功後自動登入並導向首頁（2026-07-28 修訂）。
8-1. 註冊必須通過 Email 驗證碼：先呼叫 `POST /auth/verification-codes` 取得 6 位數
   驗證碼（雜湊儲存、10 分鐘有效、單次使用），註冊時一併送出。同一 Email 兩次寄送
   間隔至少 60 秒、每日上限 10 次，驗證碼錯誤 5 次後失效。已註冊的 Email 不予寄送。
9. JWT Access Token 有效 8 小時，使用 sessionStorage，不提供 Refresh Token。
10. Token 到期後登入可返回原頁，但敏感操作不自動重送。
11. 團主申請不要求申請原因、名稱或公開聯絡方式。
12. 同一會員同時最多一筆待審核團主申請，被拒後可重新申請。
13. 通過申請後建立不完整團主資料。
14. 團主完成公開名稱與至少一項公開聯絡方式後，才可公開頁、開團及發布公告。
15. 團主公開名稱設定後不可修改，大小寫不敏感且不可重複。
16. 活動為管理員動態建立的實際活動，不使用固定分類。
17. 活動使用 open 與 ended，可由管理員結束及重新開啟。
18. 第一版活動不保存開始與結束日期。
19. 商品官方價格及團主售價固定使用 TWD。
20. 同一活動內商品名稱不可重複。
21. 商品可下架及重新上架；下架後收藏與歷史資料保留。
22. 角色為跨活動共用資料，主要於商品表單搜尋或新增。
23. 新增角色必須經明確按鈕確認，已有商品關聯時不可刪除。
24. 圖片支援 JPG、PNG 與 WebP，前端不顯示固定大小限制。
25. 伺服器保留可設定安全上限，以防止異常大檔案影響服務。
26. 固定比例圖片讓使用者自由拖曳、縮放及選擇裁切範圍。
27. 頭像與商品主要圖片為 1:1，活動圖片為 16:9，額外商品圖片不強制比例。
28. 一筆開團只屬於一名團主及一項活動，且至少包含一項商品。
28-1. 同一團主對同一活動同時只能有一個進行中（open）的開團；結單後可再開新的一輪。
29. 付款方式支援匯款與取貨付款兩種。
30. 付款方式備註為選填，任何付款方式皆可填寫；未填不顯示。
31. 開團沒有正式訂單時可修改全部內容。
32. 開團已有正式訂單後，只可修改截止時間、主要聯絡方式及安全範圍內的接單上限。
33. 開團提前結單後不可重新開啟。
34. 商品頁開團預設新到舊，可依價格與截止時間排序。
35. 開團比較支援可跟團、付款方式、二補及滿贈篩選。
36. 公開頁可顯示查詢當下剩餘數量，但不代表保留。
37. 一名會員同時最多一張跟團清單，一張清單只屬於一筆開團。
38. 相同商品再次加入清單時累加數量。
39. 不同開團替換清單必須在單一 Transaction 完成。
40. 失效跟團清單不自動刪除，但不可正式送單。
41. 跟團清單不占用或保留商品數量。
42. 正式下單前必須確認已閱讀團規。
43. 下單不信任前端價格、數量統計或快照。
44. 訂單建立使用 Transaction 與 Row Lock。
45. 下單失敗保留跟團清單，成功後才清空。
46. 每次加喊建立全新獨立訂單，不與舊訂單合併。
47. 先喊順序使用 `created_at ASC, id ASC`。
48. 訂單商品總額不包含二補、國際運費、國內運費及其他後續費用。
49. 訂單拒絕原因必填、不可修改，拒絕訂單不可恢復。
50. 會員可在待確認、待付款及已付款狀態提出取消申請。
51. 已出貨、已完成、已取消及已拒絕訂單不可提出取消申請。
52. 同一訂單同時最多一筆待處理取消申請，被拒後符合條件可再次申請。
53. 會員取消原因與團主處理回覆皆為選填。
54. 團主公告支援團主整體及指定開團兩種未完成訂單範圍。
55. 團主公告只通知待確認、待付款、已付款及已出貨訂單會員。
56. 同一公告對同一會員只建立一則通知。
57. 公開公告即使沒有通知對象仍可發布；不公開公告沒有通知對象時不可發布。
58. 公告修改同步更新相關通知，不重新發送或重設已讀狀態。
59. 公告刪除只刪除該公告及其通知。
60. 平台公告通知所有已註冊會員，不建立獨立公開頁。
61. 會員可以標記通知已讀，但不可一般性刪除通知。
62. 管理員第一版只管理 Dashboard、團主申請、活動、商品、角色支援及平台公告。
63. 第一版不提供會員帳號停用、團主資格停用或公告停用。
64. 第一版不加入付款、退款、物流、聊天或評價功能。
65. 本文件作為 WuWaGroup 第一版功能實作、測試與驗收的正式業務規則依據。

---

# End of Document
