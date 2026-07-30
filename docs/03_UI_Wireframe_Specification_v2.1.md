# 03_UI_Wireframe_Specification_v2.1

**Project Name:** WuWaGroup  
**Document Type:** UI / Wireframe Specification  
**Frontend:** React、Vite、JavaScript  
**Routing:** React Router  
**Styling:** CSS  
**Version:** 2.1  
**Last Updated:** 2026-07-18  

---

# Change Log

| Version | Date | Description |
|---|---|---|
| 1.0 | Initial Draft | 建立初始頁面與 Wireframe 規格 |
| 1.1 | Previous Version | 補充會員、團主與管理員頁面 |
| 1.2 | Previous Version | 新增團主申請、會員外部聯絡方式、特定開團公告及訂單取消介面 |
| 2.0 | 2026-07-18 | 改為 React + Vite 架構並重新整理 Route、Layout 與共用元件 |
| 2.1 | 2026-07-18 | 配合 Project Specification v2.1 與 User Flow v2.1，簡化首頁與後台、移除帳號及團主停用介面、重整公告、團主申請、開團編輯、角色輸入與商品圖片瀏覽介面 |

---

# Table of Contents

1. Document Purpose  
2. UI Design Principles  
3. React UI Architecture  
4. Route Overview  
5. Layout Specification  
6. Common Component Specification  
7. Common Page States  
8. Header and Navigation  
9. Homepage  
10. Search Result Page  
11. Activity Detail Page  
12. Product Detail Page  
13. Public Group Buy Detail Page  
14. Public Group Leader Profile Page  
15. Public Announcement Detail Page  
16. Login Page  
17. Registration Page  
18. Member Profile Page  
19. Product Favorite Page  
20. Group Leader Application Page  
21. Follow List Page  
22. Order Confirmation UI  
23. Member Order List Page  
24. Member Order Detail Page  
25. Notification Page  
26. Group Leader Layout  
27. Group Leader Dashboard  
28. Group Leader Profile Management  
29. Create Group Buy Wizard  
30. Group Leader Group Buy List  
31. Group Leader Group Buy Detail  
32. Group Leader Order List  
33. Group Leader Order Detail  
34. Group Leader Announcement Management  
35. Administrator Layout  
36. Administrator Dashboard  
37. Admin Activity Management  
38. Admin Product Management  
39. Character Input and Maintenance  
40. Admin User Management  
41. Admin Group Leader Application Review  
42. Admin Group Leader Management  
43. Admin Platform Announcement Management  
44. Modal Specification  
45. Form Validation and Feedback  
46. Permission and Route States  
47. Responsive Design  
48. Accessibility Requirements  
49. React Component Organization  
50. UI Acceptance Criteria  
51. Final UI Decisions  

---

# 1. Document Purpose

本文件定義 WuWaGroup 第一版 React 前端的：

- 頁面結構
- Route
- Layout
- 共用元件
- 表單欄位
- 狀態顯示
- Modal
- 錯誤提示
- Loading
- Empty State
- 權限畫面
- Responsive 行為

本文件用途：

- 作為 React Page Component 的開發依據
- 作為 React Router Route 的建立依據
- 作為 CSS Layout 的設計依據
- 作為 API Response 顯示需求的依據
- 作為前後端欄位對照依據
- 確保 Visitor、Member、Group Leader 與 Administrator 的介面一致
- 避免開發期間臨時增加未規劃頁面或元件

本文件使用文字 Wireframe 描述畫面。

實際視覺細節可於開發時微調，但不得改變：

- 功能
- 欄位
- 權限
- 頁面流程
- 核心狀態
- 商業規則

---

# 2. UI Design Principles

## 2.1 Information First

平台主要目標為資訊整合與開團比較。

介面優先顯示：

- 活動
- 商品
- 團主
- 團購價格
- 收單期限
- 付款方式
- 團規
- 訂單狀態

首頁介紹區只使用網站名稱與一句簡短說明，不使用輪播圖。

不使用過多動畫或裝飾影響閱讀。

---

## 2.2 Clear Status

所有重要狀態不得只靠顏色表示。

狀態需同時具有：

- 文字
- 顏色
- 必要時搭配圖示

例如：

```text
已付款
```

不可只顯示綠色圓點。

---

## 2.3 Confirm Important Actions

以下操作必須顯示確認介面：

- 清空跟團清單
- 替換跟團清單所屬開團
- 送出正式訂單
- 提出取消申請
- 接受訂單
- 拒絕訂單
- 標記付款
- 標記出貨
- 完成訂單
- 同意取消申請
- 拒絕取消申請
- 提前結單
- 刪除公告
- 結束活動
- 下架商品
- 刪除未被商品使用的角色

---

## 2.4 Server Is Source of Truth

React 前端可先驗證表單，但 API 回傳結果才是正式結果。

前端不得自行假設：

- 商品仍有數量
- 開團仍可下單
- 訂單狀態未改變
- 使用者權限仍有效
- 團主資料已完成
- 管理員資格仍有效

API 成功後才更新正式畫面狀態。

---

## 2.5 Personal Project Scope

第一版介面不加入：

- 複雜拖拉編輯器
- 首頁輪播圖
- 即時聊天視窗
- 金流頁面
- 物流追蹤
- 團主評分
- 商品評價
- 儀表板圖表套件
- 進階資料視覺化
- 多語系切換
- 主題切換
- Dark Mode

商品圖片檢視仍提供基本放大、左右切換與手機滑動，不視為複雜圖片編輯功能。

---

# 3. React UI Architecture

## 3.1 Page Component

每個主要 Route 對應一個 Page Component。

例如：

```text
HomePage
SearchPage
ActivityDetailPage
ProductDetailPage
LoginPage
RegisterPage
ProfilePage
FollowListPage
OrderListPage
OrderDetailPage
GroupLeaderDashboardPage
AdminDashboardPage
```

Page Component 負責：

- 取得 Route Parameter
- 取得 Query Parameter
- 呼叫 Service
- 管理頁面 Loading
- 管理頁面 Error
- 組合功能元件
- 處理頁面導向

---

## 3.2 Feature Component

功能元件依模組分類。

例如：

```text
ActivityCard
ProductCard
GroupBuyCard
OrderCard
NotificationItem
GroupBuyProductEditor
OrderStatusTimeline
ContactDisplay
```

---

## 3.3 Common Component

共用元件不得在不同頁面重複實作。

至少包含：

```text
Button
Input
Textarea
Select
Checkbox
RadioGroup
Modal
ConfirmModal
StatusBadge
Alert
LoadingSpinner
PageLoader
Skeleton
EmptyState
ErrorState
Pagination
Breadcrumb
ImageUploader
ImageLightbox
SearchableTagInput
FormField
SearchInput
```

---

## 3.4 State Ownership

全域登入資料：

```text
AuthContext
```

頁面資料：

```text
useState
useEffect
```

表單資料由表單所屬 Page 或 Feature Component 管理。

第一版不使用 Redux。

---

# 4. Route Overview

## 4.1 Public Routes

| Route | Page |
|---|---|
| `/` | 首頁 |
| `/search` | 搜尋結果 |
| `/login` | 登入 |
| `/register` | 註冊 |
| `/activities/:activityId` | 活動詳情 |
| `/products/:productId` | 商品詳情 |
| `/group-buys/:groupBuyId` | 公開開團詳情與團規 |
| `/group-leaders/:groupLeaderId` | 團主公開資料 |
| `/announcements/:announcementId` | 團主公開公告詳情 |

平台公告不建立獨立公開 Route。

---

## 4.2 Member Routes

| Route | Page |
|---|---|
| `/profile` | 會員個人資料 |
| `/favorites` | 商品收藏 |
| `/follow-list` | 跟團清單 |
| `/orders` | 我的訂單 |
| `/orders/:orderId` | 訂單詳情 |
| `/notifications` | 通知列表 |
| `/group-leader-application` | 團主申請 |

---

## 4.3 Group Leader Routes

| Route | Page |
|---|---|
| `/group-leader` | 團主 Dashboard |
| `/group-leader/profile` | 團主資料管理 |
| `/group-leader/group-buys` | 我的開團 |
| `/group-leader/group-buys/new` | 建立開團 |
| `/group-leader/group-buys/:groupBuyId` | 開團管理詳情 |
| `/group-leader/orders` | 團主訂單列表 |
| `/group-leader/orders/:orderId` | 團主訂單詳情 |
| `/group-leader/announcements` | 團主公告列表 |
| `/group-leader/announcements/new` | 發布團主公告 |
| `/group-leader/announcements/:announcementId` | 團主公告管理 |

---

## 4.4 Administrator Routes

| Route | Page |
|---|---|
| `/admin` | 管理員 Dashboard |
| `/admin/activities` | 活動列表 |
| `/admin/activities/new` | 新增活動 |
| `/admin/activities/:activityId` | 活動管理 |
| `/admin/products` | 商品列表 |
| `/admin/products/new` | 新增商品 |
| `/admin/products/:productId` | 商品管理 |
| `/admin/users` | 會員列表 |
| `/admin/users/:userId` | 會員詳情 |
| `/admin/group-leader-applications` | 團主申請列表 |
| `/admin/group-leader-applications/:applicationId` | 團主申請審核 |
| `/admin/group-leaders` | 團主列表 |
| `/admin/group-leaders/:groupLeaderId` | 團主詳情 |
| `/admin/announcements` | 平台公告列表 |
| `/admin/announcements/new` | 新增平台公告 |
| `/admin/announcements/:announcementId` | 平台公告管理 |

角色不設置獨立管理 Route，於商品表單中搜尋、新增及維護。

---

# 5. Layout Specification

## 5.1 Main Layout

適用：

- 公開頁面
- 登入及註冊
- 會員頁面

結構：

```text
┌──────────────────────────────────────────────┐
│ Header                                       │
├──────────────────────────────────────────────┤
│                                              │
│ Main Content                                 │
│                                              │
└──────────────────────────────────────────────┘
```

React：

```text
MainLayout
├─ Header
└─ Outlet
```

第一版不設置 Footer。

---

## 5.2 Group Leader Layout

結構：

```text
┌──────────────────────────────────────────────┐
│ Main Header                                  │
├──────────────┬───────────────────────────────┤
│              │                               │
│ Sidebar      │ Group Leader Content          │
│              │                               │
└──────────────┴───────────────────────────────┘
```

Sidebar：

- Dashboard
- 團主資料
- 我的開團
- 訂單管理
- 團務公告
- 返回前台

---

## 5.3 Administrator Layout

結構：

```text
┌──────────────────────────────────────────────┐
│ Main Header                                  │
├──────────────┬───────────────────────────────┤
│              │                               │
│ Admin        │ Admin Content                 │
│ Sidebar      │                               │
│              │                               │
└──────────────┴───────────────────────────────┘
```

Sidebar：

- Dashboard
- 活動管理
- 商品管理
- 會員管理
- 團主申請
- 團主管理
- 平台公告
- 返回前台

不顯示獨立角色管理入口。

---

## 5.4 Content Width

一般前台內容使用置中容器。

建議：

```text
max-width: 1200px
```

登入與表單頁面可使用較窄容器。

建議：

```text
max-width: 560px
```

後台表格頁面可使用較寬容器。

---

# 6. Common Component Specification

## 6.1 Button

Button 類型：

```text
primary
secondary
danger
ghost
link
```

狀態：

```text
default
hover
focus
disabled
loading
```

Loading 時：

- 顯示 Spinner
- 保留按鈕寬度
- 禁止再次點擊

---

## 6.2 Form Field

結構：

```text
Label *
[Input]

Helper Text
Error Message
```

必填欄位使用：

```text
*
```

錯誤訊息顯示於欄位下方。

---

## 6.3 Status Badge

至少支援：

### Activity

```text
進行中
已結束
```

### Group Buy

```text
開放跟團
已結單
已截止
活動已結束
```

### Order

```text
待團主確認
待付款
已付款
已出貨
已完成
已取消
已拒絕
```

### Application

```text
待審核
已通過
已拒絕
```

### Announcement

```text
公開
不公開
團主整體
特定開團
```

---

## 6.4 Modal

Modal 結構：

```text
┌────────────────────────────────────┐
│ Modal Title                    [X] │
├────────────────────────────────────┤
│ Modal Content                      │
├────────────────────────────────────┤
│ [Cancel]             [Confirm]     │
└────────────────────────────────────┘
```

危險操作的確認按鈕使用 `danger` 樣式。

---

## 6.5 Pagination

列表超過單頁筆數時顯示。

結構：

```text
[上一頁] 1 2 3 ... [下一頁]
```

目前頁需有清楚狀態。

切換頁面後捲動至列表頂部。

---

## 6.6 Breadcrumb

例如：

```text
首頁 / 活動 / 3.4 官方周邊 / 壓克力立牌
```

Breadcrumb 不包含不可操作的假連結。

---

## 6.7 Image Uploader

支援：

- 選擇圖片
- 圖片預覽
- 更換圖片
- 移除尚未送出的圖片
- 顯示格式錯誤
- 顯示大小錯誤
- 上傳 Loading

第一版不提供圖片裁切。

---

# 7. Common Page States

## 7.1 Page Loading

整頁首次讀取：

```text
PageLoader
```

列表可使用 Skeleton。

不可在資料尚未取得時顯示錯誤的空資料畫面。

---

## 7.2 Empty State

結構：

```text
[Icon]

目前沒有資料

說明文字

[可選操作按鈕]
```

例如收藏頁：

```text
目前沒有收藏商品

你可以從商品詳情頁加入收藏。

[瀏覽活動]
```

---

## 7.3 Error State

結構：

```text
無法載入資料

請稍後再試。

[重新載入]
```

404：

```text
找不到此頁面或資料已不存在。

[返回首頁]
```

---

## 7.4 Inline Error

適合操作失敗但頁面仍可保留時使用。

例如：

```text
目前商品數量不足，請調整數量後再送出。
```

---

## 7.5 Success Feedback

可使用 Toast 或頁面 Alert。

例如：

```text
個人資料已更新。
```

成功提示不可取代正式畫面更新。

---

# 8. Header and Navigation

## 8.1 Desktop Header

```text
┌──────────────────────────────────────────────────────────┐
│ Logo       [全站搜尋________________]   清單 通知 收藏 頭像 │
└──────────────────────────────────────────────────────────┘
```

---

## 8.2 Visitor Header

右側顯示：

```text
登入
註冊
```

---

## 8.3 Member Header

右側顯示：

```text
跟團清單
通知
收藏
頭像
```

通知有未讀時：

```text
通知 3
```

---

## 8.4 Avatar Menu

一般會員：

```text
個人資料
我的訂單
申請成為團主
登出
```

有效團主增加：

```text
團主後台
```

管理員增加：

```text
管理員後台
```


---

## 8.5 Mobile Header

```text
┌──────────────────────────┐
│ Logo       搜尋 通知 Menu │
└──────────────────────────┘
```

Menu：

```text
跟團清單
收藏
我的訂單
個人資料
團主後台
管理員後台
登出
```

依權限顯示。

---

# 9. Homepage

Route：

```text
/
```

## 9.1 Desktop Wireframe

```text
┌──────────────────────────────────────────────┐
│ WuWaGroup                                    │
│ 官方周邊開團資訊整合                         │
├──────────────────────────────────────────────┤
│ 活動分類 [全部 v]                            │
├──────────────────────────────────────────────┤
│ 目前活動                                     │
│                                              │
│ [Activity Card] [Activity Card] [Activity]   │
│ [Activity Card] [Activity Card] [Activity]   │
├──────────────────────────────────────────────┤
│ 已結束活動                                   │
│                                              │
│ [Activity Card] [Activity Card] [Activity]   │
└──────────────────────────────────────────────┘
```

介紹區只顯示網站名稱與一句用途說明，可使用簡單背景色或單張靜態背景，不使用輪播圖。

---

## 9.2 Activity Card

顯示：

- 活動圖片
- 活動名稱
- 活動分類
- 狀態 Badge

圖片比例：

```text
16:9
```

圖片不符合比例時可使用 `object-fit: cover` 裁切顯示，不修改原始圖片。

不顯示商品價格。

---

## 9.3 Empty State

沒有目前活動：

```text
目前沒有進行中的活動。
```

沒有已結束活動：

```text
目前沒有已結束活動。
```

---

# 10. Search Result Page

Route：

```text
/search?q=關鍵字
```

## 10.1 Wireframe

```text
搜尋結果
關鍵字：今汐

商品  8 件結果                                    查看更多 ›
[Product Result] [Product Result] ...

角色  1 件結果
[Character Result]
```

第一版在同一頁依序顯示商品與角色，不使用 Tabs。

沒有某一類結果時，該分類顯示簡短 Empty State。

**活動分區（2026-07-23 使用者決議移除）**

原規格在商品之前另有「活動」分區。實作時發現只帶 `character_id` 未帶 `q` 的情境下，
活動搜尋會以空關鍵字呼叫 API 而回傳 400，連帶讓整頁顯示錯誤。經使用者決議：
前台搜尋結果頁不再顯示活動分區。`GET /search` 的 `activities` 區段與
`GET /search/activities` 端點皆保留（API 與後端測試不變），僅前台不呈現。

**商品「查看更多」與角色連動（2026-07-28 使用者決議）**

搜尋頁有兩種檢視：

- 摘要檢視 `/search?q=關鍵字`：商品區塊顯示前 6 筆並在標題右側提供「查看更多」，
  下方顯示角色區塊。
- 全部商品檢視：只顯示商品，一頁 20 筆並提供頁碼切換，**不顯示角色區塊**。
  兩個入口——點商品區塊的「查看更多」（`/search?q=關鍵字&view=products`），
  或點角色名稱查看含該角色的所有商品（`/search?character_id=uuid`，見 §10.2）。

---

## 10.2 Character Result

顯示：

- 角色名稱
- 關聯商品數量

點擊後更新 Query：

```text
/search?character_id=uuid
```

顯示該角色跨活動的相關商品。

---

# 11. Activity Detail Page

Route：

```text
/activities/:activityId
```

## 11.1 Wireframe

```text
首頁 / 活動 / 3.4 官方周邊

┌─────────────────┬───────────────────────────┐
│ Activity Image  │ 活動名稱                  │
│                 │ 活動分類                  │
│                 │ 活動狀態                  │
│                 │ 活動說明                  │
└─────────────────┴───────────────────────────┘

活動商品

[Product Card] [Product Card] [Product Card]
[Product Card] [Product Card] [Product Card]
```

---

## 11.2 Product Card

活動頁商品卡片只顯示：

- 商品主要圖片
- 商品名稱

圖片比例：

```text
1:1
```

圖片不符合比例時可使用 `object-fit: cover` 裁切顯示，不修改原始圖片。

---

## 11.3 Ended Activity

已結束活動顯示：

```text
此活動已結束，目前無法建立新的開團。
```

商品仍可瀏覽。

---

# 12. Product Detail Page

Route：

```text
/products/:productId
```

## 12.1 Wireframe

```text
首頁 / 活動 / 商品名稱

┌──────────────────────┬─────────────────────────────┐
│ Product Main Image   │ 商品名稱                    │
│ Extra Image List     │ 所屬活動                    │
│                      │ 角色：今汐、長離            │
│                      │ 官方價格：¥59 CNY           │
│                      │ [收藏商品]                  │
└──────────────────────┴─────────────────────────────┘

開團比較

[Group Buy Card]
[Group Buy Card]
[Group Buy Card]
```

---

## 12.2 Image Gallery

顯示：

- 一張主要圖片
- 零至多張額外圖片
- Thumbnail
- 左右切換按鈕
- 圖片放大按鈕

桌面版操作：

- 點擊 Thumbnail 切換主要圖片
- 點擊主要圖片或放大按鈕開啟 Lightbox
- 在主要圖片或 Lightbox 左右兩側點擊箭頭切換圖片
- 使用鍵盤方向鍵切換圖片
- 按 Escape 關閉 Lightbox

手機版操作：

- 在主要圖片或 Lightbox 左右滑動切換圖片
- 仍保留 Thumbnail 及左右按鈕作為替代操作

Lightbox 顯示目前圖片與總圖片數，例如：

```text
2 / 5
```

第一版不提供圖片裁切或圖片編輯。

---

## 12.3 Favorite Button

Visitor 點擊：

```text
請先登入後使用收藏功能。
```

Member：

```text
收藏商品
已收藏
```

---

## 12.4 Group Buy Card

顯示：

```text
團主名稱
團購價格
付款方式
是否需要二補
是否包含滿贈
收單期限
主要聯絡平台
[查看團規]
數量 [-] 1 [+]
[加入跟團清單]
```

---

## 12.5 Invalid Group Buy

不可跟團時：

```text
目前不可跟團
```

按鈕停用。

原因可顯示：

- 已結單
- 已截止
- 活動已結束

---

# 13. Public Group Buy Detail Page

Route：

```text
/group-buys/:groupBuyId
```

## 13.1 Wireframe

```text
首頁 / 商品 / 開團詳情

活動
商品
團主

付款方式
是否二補
是否滿贈
收單期限
主要聯絡方式

團規
────────────────────
完整團規文字
────────────────────

[返回商品]
```

---

## 13.2 Rules Display

團規使用一般文字顯示。

保留換行，但不執行 HTML。

---

## 13.3 Availability Banner

可跟團：

```text
此開團目前仍可接受訂單。
```

不可跟團：

```text
此開團目前已停止接受新的訂單。
```

---

# 14. Public Group Leader Profile Page

Route：

```text
/group-leaders/:groupLeaderId
```

## 14.1 Wireframe

```text
┌──────────┬─────────────────────────────────┐
│ Avatar   │ 團主名稱                        │
│          │ 成為團主時間                    │
│          │ 開團次數                        │
│          │ 完成訂單數                      │
└──────────┴─────────────────────────────────┘

團主介紹

公開聯絡方式
Facebook
Discord
LINE

目前開團
[Group Buy Card]

最新公開公告
[Announcement Item]

預設團規
────────────────────
團主通常使用的開團規則
────────────────────
```

預設團規用來讓使用者了解團主平常的開團習慣。

各開團的正式團規仍以該開團詳情頁與訂單快照為準。

---

## 14.2 Profile Visibility

團主申請通過但尚未完成公開名稱或公開聯絡方式時：

```text
團主公開資料尚未完成
```

不公開團主頁，也不可建立開團或發布公告。

公開頁不得顯示會員私人 Email 或私人聯絡方式。

---

# 15. Public Announcement Detail Page

Route：

```text
/announcements/:announcementId
```

此頁只顯示團主選擇公開的公告。

顯示：

- 公告範圍：團主整體或特定開團
- 公告標題
- 團主名稱
- 所屬開團（特定開團公告才顯示）
- 發布時間
- 更新時間
- 公告內容

公告不存在、已刪除或目前為不公開時：

```text
404 或公告目前無法查看
```

平台公告不使用此頁面。

---

# 16. Login Page

Route：

```text
/login
```

## 16.1 Wireframe

```text
登入 WuWaGroup

Email *
[________________________]

密碼 *
[________________________]

[登入]

還沒有帳號？前往註冊
```

---

## 16.2 Invalid Credentials

顯示：

```text
Email 或密碼錯誤。
```

不得顯示 Email 是否存在。

---

## 16.3 Redirect Notice

由受保護頁面導向時，可顯示：

```text
請先登入後繼續操作。
```

登入成功後返回原 Route。

---

# 17. Registration Page

Route：

```text
/register
```

## 17.1 Wireframe

```text
建立帳號

Email *
[________________________]

密碼 *
[________________________]

確認密碼 *
[________________________]

暱稱 *
[________________________]

頭像（選填）
[Image Uploader]
未上傳時使用預設頭像

外部聯絡方式
至少填寫一項

Facebook
[________________________]

Discord
[________________________]

LINE
[________________________]

[建立帳號]
```

---

## 17.2 Validation

錯誤訊息：

```text
請輸入有效的 Email。
密碼格式不符合要求。
兩次密碼不一致。
請輸入暱稱。
請至少提供一項外部聯絡方式。
圖片格式或大小不符合要求。
```

註冊成功後自動登入並導向首頁（2026-07-28 修訂，原為「前往登入頁，不自動登入」）。

註冊表單需先取得 Email 驗證碼（欄位置於 Email 之下，右側為「發送驗證碼」按鈕，
寄出後按鈕進入倒數）。頭像為選填，只提供選檔與圓形預覽，裁切依既有決議延後。

---

# 18. Member Profile Page

Route：

```text
/profile
```

## 18.1 Wireframe

```text
個人資料

帳號資料
Email：user@example.com
建立時間：2026/07/18

頭像
[Avatar] [更換頭像]

暱稱
[________________]

外部聯絡方式
Facebook [_______________]
Discord  [_______________]
LINE     [_______________]

[儲存變更]

團主資格
[Qualification Status]
```

Email 第一版不可自行修改。

外部聯絡方式至少保留一項。

---

## 18.2 Group Leader Status

### No Qualification

```text
團主資格
尚未取得

[申請成為團主]
```

### Pending Application

```text
團主申請
待審核

申請時間：2026/07/18
```

### Rejected Application

```text
團主申請未通過

[再次申請]
```

只要目前沒有新的待審核申請即可再次申請。

### Approved but Setup Incomplete

```text
團主資格
已通過，尚未完成公開資料

[完成團主資料]
```

### Active

```text
團主資格
可使用

團主名稱：月影團

[進入團主後台]
```

---

# 19. Product Favorite Page

Route：

```text
/favorites
```

## 19.1 Wireframe

```text
我的收藏

[Product Card] [Product Card] [Product Card]
```

每張卡片顯示：

- 商品圖片
- 商品名稱
- 所屬活動
- 下架狀態
- 取消收藏

---

## 19.2 Inactive Product

```text
商品已下架
```

仍允許取消收藏。

---

# 20. Group Leader Application Page

Route：

```text
/group-leader-application
```

## 20.1 New Application

第一版不要求申請說明、團主名稱或公開聯絡方式。

```text
申請成為團主

管理員通過申請後，
你需要再設定團主公開名稱與公開聯絡方式。

[返回] [送出申請]
```

送出前顯示確認 Modal。

---

## 20.2 Pending State

```text
團主申請審核中

申請時間
2026/07/18
```

不顯示新的申請按鈕。

---

## 20.3 Rejected State

```text
團主申請未通過

[再次申請]
```

第一版不顯示審核備註。

---

## 20.4 Approved State

申請通過後導向：

```text
/group-leader/profile
```

完成團主公開名稱與至少一項公開聯絡方式前，不公開團主頁，也不可建立開團或公告。

---

# 21. Follow List Page

Route：

```text
/follow-list
```

## 21.1 Wireframe

```text
跟團清單

團主：月影團
活動：3.4 官方周邊
收單期限：2026/08/10
付款方式：銀行轉帳
主要聯絡：Discord / moon_group

商品
┌─────────────────────────────────────────┐
│ 圖片 商品名稱 單價 數量 小計 [移除]     │
│ 圖片 商品名稱 單價 數量 小計 [移除]     │
└─────────────────────────────────────────┘

預估總額：NT$ 1,170

團規
[查看完整團規]

[清空跟團清單]      [送出訂單]
```

---

## 21.2 Quantity Editor

```text
[-] 2 [+]
```

也可使用 Number Input。

數量更新時：

- 顯示局部 Loading
- 成功後更新小計
- 成功後更新預估總額
- 失敗時恢復原數量

---

## 21.3 Invalid Follow List

開團失效時顯示：

```text
目前無法送出此跟團清單。

原因：開團已截止。
```

送出按鈕停用。

會員仍可：

- 移除商品
- 清空清單

---

# 22. Order Confirmation UI

在跟團清單點擊送出訂單後顯示 Modal 或獨立確認區塊。

```text
確認送出訂單

團主
月影團

活動
3.4 官方周邊

商品
壓克力立牌 × 2
徽章 × 1

預估總額
NT$ 1,170

會員聯絡方式
Discord：member_name
LINE：member_line

付款方式
銀行轉帳

主要聯絡方式
Discord：moon_group

[ ] 我已閱讀並同意本次團規

[返回] [確認送出]
```

未勾選團規時，確認按鈕停用。

正式總額由後端重新計算。

---

# 23. Member Order List Page

Route：

```text
/orders
```

## 23.1 Filter

```text
全部
待確認
待付款
已付款
已出貨
已完成
已取消
已拒絕
```

---

## 23.2 Order Card

顯示：

- 訂單編號
- 活動名稱
- 團主名稱
- 商品摘要
- 代表圖片
- 總額
- 訂單狀態
- 建立時間

---

# 24. Member Order Detail Page

Route：

```text
/orders/:orderId
```

## 24.1 Wireframe

```text
訂單詳情

訂單編號：WG-20260801-A1B2C3
狀態：[待團主確認]

訂單進度
待確認 → 待付款 → 已付款 → 已出貨 → 已完成

團主
月影團

活動
3.4 官方周邊

商品明細
商品名稱 / 單價 / 數量 / 小計

總額
NT$ 780

付款方式
銀行轉帳

團主聯絡方式
Discord：moon_group

團規
完整團規文字

取消申請
[依狀態顯示]
```

被拒絕或取消的訂單不繼續顯示正常進度，改顯示終止狀態。

---

## 24.2 Rejected Order

```text
訂單已被團主拒絕

拒絕原因
本次可接受數量不足。
```

拒絕原因必填，顯示後不可修改。

---

## 24.3 Cancellation Request

可申請取消時：

```text
[申請取消訂單]
```

Modal：

```text
申請取消訂單

取消原因（選填）
[                         ]

[返回] [送出申請]
```

已有待審核申請：

```text
取消申請審核中
```

已拒絕：

```text
取消申請未通過

團主回覆（可能未提供）
商品已完成代購，依本次團規無法取消。

[再次申請取消]
```

訂單仍符合取消條件且沒有待審核申請時，可再次申請。

---

## 22a. Image Crop Rule

> 新增紀錄（2026-07-30 使用者要求本批加上；原先列為延後項目）。

所有圖片上傳一律先進裁切器，裁切後才上傳，因此存進 Storage 的已是成品。

**運作方式**：整張圖完整顯示、不縮放也不留白（容器尺寸等於圖片顯示尺寸），
圖上疊一個裁切框；拖曳框身移動、拖曳四角改變範圍。框永遠被夾在圖片內，
因此輸出不會有白邊，也不會為了填滿框而把圖放大到模糊。

> **不可改成「固定框、移動圖片」**：只要圖片比例與框不同，那種做法必然要嘛
> 裁掉邊緣、要嘛產生留白。本專案早期版本走過這條路，已改掉。

各處的比例設定：

| 用途 | 比例 | 可直接用原圖 |
|---|---|---|
| 活動封面（圖 33） | 鎖 16:9 | 否 |
| 商品主圖與額外圖片（圖 35） | **自由比例** | **是** |
| 會員／團主頭像 | 鎖 1:1（框呈圓形） | 否 |

- 輸出統一為 WebP（品質 0.92），副檔名同步改為 `.webp`，否則後端的副檔名檢查會擋。
- **不放大**：輸出解析度就是實際裁到的像素數，上限 1600px。工具列會顯示實際輸出
  尺寸，讓使用者判斷會不會太小。
- 商品圖提供「直接使用原圖」，原檔原封不動送出（不裁就沒必要多壓一次）。

**顯示端必須一致**：商品圖既然允許自由比例，商品詳情頁的主圖就**不可**設固定
`aspect-ratio` —— 用 `cover` 會裁掉圖，用 `contain` 會產生白邊，兩者都與「上傳時不裁」
矛盾。高度交給圖片自己決定。編輯頁的預覽框可保留固定高度（多項商品要對齊），
但需用 `contain`，否則管理員會誤以為圖被裁掉。
小尺寸縮圖（卡片、列表）仍用 `cover` 填滿方框，這是刻意的。

---

## 23a. List Filter State Rule

> 新增紀錄（2026-07-30 使用者回報搜尋清不掉）。

**列表頁的所有篩選條件（狀態、活動、搜尋關鍵字）一律以網址查詢參數為單一來源，
不得只存在元件狀態。**

理由：側邊選單的連結指向不帶 query 的路徑（例如 `/group-leader/orders`），
導向同一路由時 React Router 不會重新掛載元件——篩選若存在元件狀態就會殘留，
使用者得離開頁面或重新整理才清得掉。以網址為單一來源後，點選單即等於清空全部篩選。

例外：搜尋框的「未送出輸入值」可留在元件狀態（否則每打一個字就查一次 API），
但必須以 effect 跟著網址的關鍵字同步，否則框內文字會與實際篩選不一致。

換任何篩選條件都要回到第一頁，否則可能停在超出範圍的頁碼而顯示空清單。

已套用（2026-07-30 全數完成）：
圖 25 團主訂單管理（status／has_pending_cancellation／activity_id／keyword）、
圖 21 我的開團（status／keyword）、
管理員活動管理（status／keyword）、
管理員商品管理（activity_id／is_active／keyword）。

排序與每頁筆數不算篩選條件，維持元件狀態即可（點選單回到預設值反而合理），
但改動時同樣要回第一頁。

---

## 24.3a Bottom Action Bar

> 修訂紀錄（2026-07-30 使用者裁決）。

底部操作列只保留「返回我的訂單」（左）與「查看團主公開頁」（右）。

參考圖 08 在此處另畫了一顆紫色「申請取消訂單」，但與「取消申請」卡片內那顆
完全重複——同一個路由、同樣文字。**已移除底部這一顆**，保留卡片內那顆：
只有卡片內那個位置旁邊才有可取消狀態、目前狀態與「被拒絕可再申請」的說明脈絡。

---

## 24.4 Unmerge Request

> 新增紀錄（2026-07-30 使用者需求）。

拆回入口放在**「取消申請」卡片內**，不另開一張卡片（使用者 2026-07-30 裁決）：
該卡片與「下單時團規」同屬一個兩欄區，多一張卡會讓兩欄排成 2+1 而空一格。

由多張訂單合併而成、且目前仍可拆回時（`can_request_unmerge`），卡片內容為：

```text
取消申請

拆回原本的訂單
這張訂單由多張合併而成。拆回後商品仍保留，**不是取消訂單**；
各張會回到合併前的狀態與金額。

[申請拆回原訂單]

ⓘ 已出貨之後就無法再拆。
┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
取消整筆訂單
在以下狀態可申請取消訂單
[等待團主確認][等待付款][已付款]

[申請取消訂單]

ⓘ 目前狀態：…
```

已有待處理拆單申請時，上半改為：

```text
ⓘ 已提出申請，等待團主處理。核准後會拆回合併前的 N 張訂單。
你填寫的原因：…
```

規則：

- 兩個動作意思完全不同（拆回＝商品保留；取消＝不買了），因此以小標題與虛線
  分隔線切開，文案並明確寫出「不是取消訂單」，避免誤按。
- **非合併訂單不顯示上半區塊，也不顯示小標題**，畫面與圖 08 原樣完全相同。
- 申請燈窗與通知中心（§25.3）共用同一個元件，避免兩處文案與行為分歧。
- 會員有兩個入口：這裡，以及通知中心那則「訂單已合併」通知底下的按鈕——
  只放通知那一個的話，通知一多就找不到了。

---

# 25. Notification Page

Route：

```text
/notifications
```

## 25.1 Wireframe

```text
通知

[全部標記已讀]

[系統] 團主申請已通過
2026/08/01

[團主] 官方出貨時間調整
2026/08/05
```

---

## 25.2 Notification Item

顯示：

- 類型 Badge
- 標題
- 短訊息
- 時間
- 已讀狀態

未讀通知需有清楚標示。

點擊通知後：

- 標記該通知為已讀
- 導向相關訂單、團主申請、公告、團主頁或開團頁

通知列表提供「全部標記已讀」，不提供會員自行刪除通知。

公告被編輯時，該公告產生的通知內容同步更新。

公告被刪除時，只有該公告產生的通知一併刪除。

---

## 25.3 Merge Notification Action

> 新增紀錄（2026-07-30 使用者需求）。

「訂單已合併」這一則通知底下顯示「取消合併訂單」按鈕與說明文字
「需由團主確認後才會拆回原本的訂單」。

- 按鈕放在通知本體**外面**：通知本體整塊是連結，按鈕嵌在裡面會變成巢狀互動元素，
  且點按鈕會被當成點通知而導頁。
- 只有 `can_request_unmerge` 為 true 的通知才顯示；該批次已拆、訂單已出貨，
  或已有待處理申請時後端會回 false，按鈕即消失。
- 點擊開啟燈窗：說明「送出後由團主確認才會拆回」、可填選填原因，送出後顯示
  已送出狀態。
- 通知訊息含被合併訂單的逐項商品明細，因此訊息區需保留換行（`white-space: pre-line`）。

---

# 26. Group Leader Layout

## 26.1 Sidebar

**2026-07-28 使用者提供的選單規格，為團主後台此區塊的最高依據。**
除了 20_團主儀表板、21_我的開團、22_商品訂購總覽、23_開團設定 這四張參考圖以外，
其他參考圖若與本節文字衝突，一律以本節為準（舊圖畫得較早，職責已被本規格取代）。

```text
團主後台

儀表板
開團管理
  ├─ 我的開團
  └─ 建立開團
訂單管理
公告管理
團主資料

返回前台
```

目前頁面需顯示 Active 狀態。

## 26.1a Menu Responsibilities

一句話定位：

| 選單 | 定位 |
|---|---|
| 儀表板 | 今天要處理什麼 |
| 我的開團 | 我曾經開過哪些團 |
| 訂單管理 | 有哪些訂單要處理 |
| 公告管理 | 我要通知哪些團員 |
| 團主資料 | 前台怎麼顯示我 |

**1. 儀表板** — 看整體概況與快速處理，是「總覽首頁」而非完整管理頁。

- 待處理訂單數（＝待確認＋待付款，兩者都要團主處理）
- 待處理取消申請數
- 進行中開團數
- 即將截止的開團（進行中且 3 天內截止；已過期未結單的不算）
- 目前開團活動（只列進行中、不分頁、依活動分組）
- 快速進入訂購總覽或開團設定

**2. 我的開團** — 查看自己所有開過的團，不只進行中。

- 篩選：全部／進行中／已截止
- 每筆顯示活動名稱＋輪次、狀態、截止日期、訂單數
- 動作：查看訂購總覽、開團設定
- 與儀表板的差別：儀表板看最近／重要／待處理，我的開團看完整紀錄與篩選
- 搜尋框比對活動名稱（開團沒有名稱欄位，輪次由後端算出）

## 26.1b 參考圖有畫但不實作的項目

| 項目 | 出現位置 | 不做的原因 |
|---|---|---|
| 活動期間／活動時間 | 圖 20、21 | `activity` 沒有起訖日期欄位，全部規格文件亦從未定義。改顯示開團截止日期。 |
| 統計卡「較昨日 +6 ↗」 | 圖 20 | 資料庫沒有每日統計快照，昨天的數字無從得知。 |
| 開團名稱（第一團／追加團） | 圖 20–23 | 不新增欄位，一律以後端算出的「第 N 團」呈現。 |

沿用既有的「規格沒有就不做」原則（同圖 07 出貨單號、圖 08 付款倒數）。
以上三項均為使用者當面裁決，2026-07-28／07-29。

統計數字的基準（重要，避免前後台數字看起來矛盾）：

- 訂單數、商品數量／訂購數量：**排除已取消與已拒絕**的訂單。
- **待處理＝待確認＋待付款**（使用者 2026-07-29 說明：兩者都要團主處理）。
  統計卡與每輪開團那列的紅字欄位都用這個定義；參考圖該欄原標「待確認」，
  已一併改為「待處理」，全頁只保留一種「要處理」的數字。
  點統計卡進入訂單列表時用複合篩選 `?status=pending`，數字與清單筆數一致。
- 開團設定頁的欄位凍結判斷：計入**所有**訂單紀錄（含已取消），
  因此可能出現「訂單數 0 但欄位已凍結」的情況，這是正確行為。

**3. 建立開團** — 新增入口，與「我的開團」不重複。

選擇進行中的活動、設定開團名稱、選擇商品、設定價格、設定付款方式、
設定截止時間、設定團規、設定最大數量、發布開團。

**4. 訂單管理** — 跨所有開團管理訂單。

- 所有待確認／待付款／已付款訂單、某會員的訂單、某活動的訂單、取消申請
- 與「商品訂購總覽」的差別：訂購總覽以「某一開團、某一商品」為主，
  訂單管理以「所有訂單」為主

**5. 公告管理** — 管理團主發布的所有公告（公告不一定只屬於某一團）。

一般團主公告／特定開團公告、公開公告／僅通知未完成訂單會員的公告、編輯、刪除。

**6. 團主資料** — 管理團主公開頁面的內容，會顯示在前台團主公開頁。

團主頭像、公開顯示名稱、團主介紹、公開聯絡方式、預設團規。
名稱刻意叫「團主資料」而非「個人資料」，避免與一般會員資料混淆。

---

## 26.2 Mobile

Sidebar 收合為 Drawer。

頂部顯示：

```text
[Menu] 團主後台
```

---

# 27. Group Leader Dashboard

Route：

```text
/group-leader
```

## 27.1 Summary Cards

只保留：

```text
目前開團
待處理訂單
待處理取消申請
```

點擊卡片進入對應列表或已篩選列表。

---

## 27.2 Recent Orders

顯示少量最近訂單：

- 訂單編號
- 會員暱稱與頭像
- 活動
- 金額
- 狀態
- 建立時間

提供「查看全部訂單」。

---

## 27.3 Quick Actions

顯示：

```text
[建立開團]
[發布公告]
[管理團主資料]
```

Dashboard 不重複顯示所有訂單狀態統計，也不使用圖表。

---

# 28. Group Leader Profile Management

Route：

```text
/group-leader/profile
```

## 28.1 Form

```text
團主資料

團主公開名稱 *
[_______________________]

自我介紹（選填）
[                         ]
[                         ]

公開聯絡方式
至少填寫一項
Facebook [______________]
Discord  [______________]
LINE     [______________]

[儲存團主資料]
```

會員私人聯絡方式不自動帶入此表單。

申請剛通過時，團主必須先完成公開名稱與至少一項公開聯絡方式。

完成前頁面顯示：

```text
請先完成團主公開資料，才能公開團主頁、建立開團或發布公告。
```

---

## 28.2 Default Rules

```text
預設團規（選填）

[                         ]
[                         ]
[                         ]

[儲存預設團規]
```

說明：

```text
預設團規會顯示於團主公開頁，
並帶入後續新開團。

修改預設團規不會改動既有開團。
各開團的正式規則仍以該開團團規為準。
```

---

# 29. Create Group Buy Wizard

Route：

```text
/group-leader/group-buys/new
```

## 29.1 Stepper

```text
1 選擇商品
2 價格與數量
3 開團設定
```

---

## 29.2 Activity Selection

```text
選擇活動 *
[3.4 官方周邊 v]
```

只顯示目前開放活動。

選擇活動後才載入商品。

---

## 29.3 Step 1 Wireframe

```text
Step 1：選擇商品

[全選] [清除選擇]

[ ] 商品圖片 商品名稱
[ ] 商品圖片 商品名稱
[ ] 商品圖片 商品名稱

已選擇 3 項商品

[取消] [下一步]
```

---

## 29.4 Step 2 Wireframe

```text
Step 2：價格與數量

商品：壓克力立牌
團購價格 *
[390.00]

接單數量上限 *
[20]

商品：徽章
團購價格 *
[120.00]

接單數量上限 *
[30]

[上一步] [下一步]
```

---

## 29.5 Step 3 Wireframe

```text
Step 3：開團設定

付款方式 *
[銀行轉帳 v]

需要二補
( ) 是
( ) 否

包含滿贈
[ ] 是

收單截止時間 *
[日期時間]

團規 *
[                         ]
[                         ]
預設帶入團主目前的預設團規，可在本次開團中修改

主要聯絡平台 *
[Discord v]

聯絡內容 *
[moon_group]

[上一步] [建立開團]
```

活動不支援滿贈時，不顯示滿贈欄位。

---

## 29.6 Submit Confirmation

```text
確認建立開團

活動：3.4 官方周邊
商品數量：3 項
收單期限：2026/08/10
付款方式：銀行轉帳
主要聯絡：Discord

[返回修改] [確認建立]
```

---

# 30. Group Leader Group Buy List

Route：

```text
/group-leader/group-buys
```

## 30.1 Filter

```text
全部
開放中
已結單
```

---

## 30.2 Card or Table

顯示：

- 活動
- 狀態
- 實際可用狀態
- 商品數量
- 訂單數量
- 收單期限
- 建立時間
- 查看管理

---

# 31. Group Leader Group Buy Detail

Route：

```text
/group-leader/group-buys/:groupBuyId
```

## 31.1 Summary

```text
活動：3.4 官方周邊
狀態：開放中
實際狀態：可跟團
收單期限：2026/08/10
正式訂單：12 筆
```

操作：

```text
[編輯開團]
[提前結單]
```

---

## 31.2 Product Management Table

| 商品 | 單價 | 上限 | 已占用 | 可接受 | 操作 |
|---|---:|---:|---:|---:|---|
| 壓克力立牌 | 390 | 20 | 12 | 8 | 編輯 |
| 徽章 | 120 | 30 | 18 | 12 | 編輯 |

---

## 31.3 Editing Before Any Order

沒有正式訂單時，可以修改：

- 商品集合
- 商品價格
- 接單上限
- 付款方式
- 是否需要二補
- 是否包含滿贈
- 收單截止時間
- 團規
- 主要聯絡方式

可重新進入與建立開團相同的三步驟表單。

---

## 31.4 Editing After Orders Exist

已有正式訂單時，只能修改：

- 收單截止時間
- 主要聯絡平台
- 主要聯絡內容
- 商品接單數量上限

不可修改：

- 商品集合
- 商品價格
- 付款方式
- 是否需要二補
- 是否包含滿贈
- 團規

不可編輯欄位顯示唯讀狀態及原因：

```text
此開團已有正式訂單，為保留訂單快照一致性，目前不可修改。
```

---

## 31.5 Edit Quantity Limit Modal

```text
編輯接單數量上限

商品
壓克力立牌

接單數量上限 *
[25]

目前占用數量
12

[返回] [儲存]
```

上限低於占用數量時顯示：

```text
接單數量上限不可低於目前占用數量 12。
```

---

# 32. Group Leader Order List

Route：

```text
/group-leader/orders
```

## 32.1 Filters

使用簡單下拉選單：

- 開團
- 活動
- 訂單狀態
- 是否有待處理取消申請

第一版不加入複雜搜尋介面。

---

## 32.2 Table

| 訂單編號 | 會員 | 活動 | 商品摘要 | 金額 | 狀態 | 取消申請 | 時間 |
|---|---|---|---|---:|---|---|---|

會員欄顯示頭像或預設頭像及暱稱，協助團主辨識。

手機版改為 Order Card。

---

# 33. Group Leader Order Detail

Route：

```text
/group-leader/orders/:orderId
```

## 33.1 Member Information

顯示：

- 會員頭像或預設頭像
- 會員暱稱
- Facebook 聯絡快照
- Discord 聯絡快照
- LINE 聯絡快照

只顯示該訂單建立時的聯絡快照。

會員頭像只供該訂單所屬團主辨識。

---

## 33.2 Order Actions

依狀態顯示：

### Pending Confirmation

```text
[接受訂單]
[拒絕訂單]
```

### Pending Payment

```text
[標記已付款]
```

### Paid

```text
[標記已出貨]
```

### Shipped

```text
[完成訂單]
```

---

## 33.3 Reject Order Modal

```text
拒絕訂單

訂單編號
WG-20260801-A1B2C3

拒絕後訂單無法恢復，拒絕原因也無法修改。

拒絕原因 *
[                         ]
[                         ]

0 / 500

[返回] [確認拒絕]
```

拒絕原因必填，全空白視為未填。

---

## 33.4 Cancellation Request Section

```text
取消申請

會員原因（可能未提供）
臨時無法完成付款。

申請時間
2026/08/04

[同意取消] [拒絕取消]
```

拒絕取消 Modal：

```text
拒絕取消申請

團主回覆（選填）
[                         ]
[                         ]

[返回] [確認拒絕]
```

拒絕後訂單狀態不變；會員之後仍可在符合條件時再次提出取消申請。

---

## 33.5 Merge Section

> 新增紀錄（2026-07-29 合併；2026-07-30 拆單）。

同會員在本開團還有可合併的訂單時顯示「合併訂單」區塊：候選訂單複選清單、
保留哪一張（最舊／最新）的選擇，送出前以確認燈窗再確認一次。

訂單本身不可合併（已出貨之後、或有待處理取消申請）時整個區塊不顯示。

---

## 33.6 Unmerge Request Section

> 新增紀錄（2026-07-30 使用者需求）。

會員提出取消合併申請後，團主訂單詳情頁顯示「取消合併申請」區塊：

```text
取消合併申請

會員希望把這張訂單拆回合併前的樣子。
核准後下列訂單會重新出現，本張訂單的金額與狀態會回到合併前。

會員原因（可能未提供）
想分開付款

WG260730-000001  浴衣祭典・提袋 ×2、吟霖・浴衣立牌（安可）×2   NT$ 3498.00  [待團主確認]

回覆備註（拒絕時必填）
[                         ]

[拒絕拆單] [執行拆單]
```

- 每一列顯示要拆回的訂單編號、逐項商品明細、金額與**合併前**的狀態。
- 「拒絕拆單」的回覆備註必填（後端回 422），「執行拆單」的備註選填。
- 訂單金額區在有已收金額時顯示「商品總額／其中已收款／待收款」三列，
  三者皆由後端以同一種金額格式回傳（前端不自行相減，否則會出現
  `6996` 與 `6996.00` 併存的不一致）。

---

# 34. Group Leader Announcement Management

> 改版紀錄（2026-07-30，依參考圖 27）：清單由卡片式改為表格，表單改為清單右側的
> 面板（不是獨立路由），並新增「通知對象預覽」。以下 §34.1a 為改版後的實際規格；
> §34.2 的獨立 `/new` 路由未採用。

## 34.1 List Route

```text
/group-leader/announcements
```

顯示：

- 公告標題
- 公告範圍
- 所屬開團（如有）
- 公開狀態
- 通知會員數
- 發布時間
- 更新時間
- 編輯
- 刪除

---

## 34.1a List Layout（圖 27）

頁首為標題「公告管理」＋副標「管理團主整體公告與特定開團公告」，
「新增公告」按鈕自成一列在副標下方、左對齊。

清單為白底卡片內的表格，六欄：

| 欄位 | 內容 |
|---|---|
| 公告標題 | 標題（粗體）＋下方一行內文摘要（灰色、超出以 … 截斷） |
| 公告類型 | badge：團主整體公告／特定開團公告 |
| 目標與對象 | 特定開團公告顯示「指定開團／活動名稱｜第 N 團」；兩者都顯示「通知對象／所有（或該開團）未完成訂單會員（N 人）」 |
| 公開狀態 | badge：公開（綠）／僅通知相關會員（橘） |
| 發布時間 | 日期與時間分兩行 |
| 操作 | 編輯（紫框＋鉛筆）、刪除（紅框＋垃圾桶），上下排列 |

底部為 ListFooter（左筆數說明、中頁碼、右每頁筆數 5／10／20，預設 10）。

**與參考圖刻意不同之處**：

1. 參考圖表格沒有內容欄，本專案在標題下加一行內文摘要（使用者 2026-07-30 裁決）——
   否則每則都得點編輯才知道寫了什麼。
2. 保留「只顯示某開團公告」的篩選提示條（參考圖沒有）：從圖 22 的「團購公告」分頁
   帶 `group_buy_id` 進來時必須讓團主看得出來現在不是全部公告，否則會以為公告不見了。

---

## 34.1b Form Panel（圖 27）

點「新增公告」或「編輯」時，表單以右側整欄面板出現（使用者 2026-07-30 要求：
像瀏覽器 DevTools 那樣右側跳出、頂端在 header 下，**且頁面內容要向左收窄並完整
顯示，不可被遮擋**）。

- 版面用 **grid 兩欄**（`minmax(0, 1fr)` ＋ 400px），清單因此自動向左收窄。
  **不可用 `position: fixed`**——fixed 會脫離版面浮在內容上方，就成了遮擋。
- 面板在右欄內以 `position: sticky` 貼齊 header 底部並撐到視窗底部，
  內容過長時面板自身滾動。
- header 是 sticky 且高度由內容決定（沒有固定值），因此面板頂端位置需**量測
  `.app-header` 實際高度**寫入 CSS 變數，並在視窗大小改變時重新量。
- 視窗寬度 < 1200px 放不下兩欄時，面板移到清單**下方**（仍為完整顯示，不是覆蓋）。

```text
新增公告                                    ✕

公告標題
[請輸入公告標題              ]

公告類型
( ) 團主整體公告
(•) 特定開團公告

指定開團
[3.4 官方周邊              v]

公開狀態
(•) 公開顯示並通知相關會員
( ) 僅通知相關會員

公告內容
[請輸入公告內容...           ]
[                    0 / 1000]

┌ 通知對象預覽 ──────────────┐
│ 👥  通知對象：              │
│     3.4 官方周邊未完成訂單會員（18 人）│
│     此公告將僅通知上述對象。 │
└────────────────────────────┘

[取消] [發布公告]
```

規則：

- 公告內容右下角顯示字數 `N / 1000`；標題上限 80 字。
- 通知對象預覽的人數由 §25.6 的預覽 API 即時計算，切換公告類型或指定開團時重新查詢；
  特定開團公告尚未選開團時顯示「請先選擇開團，即可預覽通知對象」。
- 預覽的說明文字依公開狀態切換（公開＝「會公開顯示，並通知上述對象」）；
  人數為 0 時另外提示「必須設為公開才能發布」。
- **編輯時不顯示公告類型、指定開團與通知對象預覽**：後端只接受修改標題／內容／
  是否公開，通知對象在發布時就固定了（見 §25.4）。

---

## 34.2 Create Route

```text
/group-leader/announcements/new
```

表單：

```text
發布團務公告

公告範圍 *
( ) 團主整體公告
( ) 特定開團公告

所屬開團 *
[3.4 官方周邊 v]
僅在選擇特定開團公告時顯示

公告標題 *
[________________________]

公告內容 *
[                          ]
[                          ]

[ ] 顯示於公開頁面

預計通知會員：12 人

[發布公告]
```

團主整體公告通知該團主所有仍有未完成訂單的會員。

特定開團公告只通知該開團仍有未完成訂單的會員。

---

## 34.3 No Recipient Notice

公開公告且通知人數為 0：

```text
目前沒有符合通知條件的會員。
公告仍可發布並顯示於公開頁面。
```

不公開公告且通知人數為 0：

```text
目前沒有可通知的會員，無法發布不公開公告。
```

發布按鈕 Disabled。

---

## 34.4 Edit Announcement

可修改：

- 標題
- 內容
- 是否公開

不可修改：

- 公告範圍
- 所屬開團
- 發布時間

顯示提示：

```text
儲存後，這則公告已建立的通知內容會同步更新，
但不會重新建立通知。
```

---

## 34.5 Delete Announcement

```text
刪除公告

刪除後：
- 公告將無法查看
- 這則公告產生的通知會一併刪除
- 其他訂單與系統通知不受影響

[返回] [確認刪除]
```

第一版不提供公告停用功能。

---

# 35. Administrator Layout

Sidebar：

```text
管理員後台

Dashboard
活動管理
商品管理
會員管理
團主申請
團主管理
平台公告

返回前台
```

角色的搜尋、新增與維護整合於商品表單，不顯示獨立角色管理選單。

---

# 36. Administrator Dashboard

Route：

```text
/admin
```

只顯示四張數字卡片：

- 待審核團主申請
- 進行中活動
- 上架商品
- 目前開團

顯示快速入口：

```text
[新增活動]
[新增商品]
[審核團主申請]
[發布平台公告]
```

第一版不顯示會員總數、有效團主總數或其他申請數，也不使用圖表套件。

---

# 37. Admin Activity Management

## 37.1 List

Route：

```text
/admin/activities
```

顯示：

- 活動圖片
- 活動名稱
- 分類
- 狀態
- 是否支援滿贈
- 建立時間
- 操作

---

## 37.2 Create Form

```text
活動名稱 *
[____________________]

活動分類 *
[官方周邊 v]

活動說明
[                      ]

活動圖片 *
[Image Uploader]

支援滿贈
[ ] 是

[建立活動]
```

新活動建立後狀態自動為 `open`。

> 修訂紀錄（2026-07-30，依參考圖 33 改版）：
> - 「活動分類」欄位已不存在——`activity.category` 為需求追蹤矩陣衝突解法 #1，
>   已於 2026-07-23 撤回並從資料庫移除。
> - 表單包在白底卡片內，含麵包屑「活動管理 / 活動新增」與「返回活動列表」。
> - 活動名稱上限 50 字、活動說明上限 500 字，均於欄位右下角顯示字數。
> - 封面圖片附說明「建議封面比例為 16:9，支援 JPG、PNG、WebP」，
>   並提供裁切（鎖 16:9，見 §22a）。
> - 「支援滿贈」改為「有／無」選項組，與「狀態」並排；選項需**橫向排列**
>   （`.form-field` 是 flex column，radio 必須另包一層橫向容器，否則會變成一行一個）。
> - **建立成功後直接導向商品批次新增頁並帶入該活動**（見 §38.2a）：
>   新活動必然還沒有商品，回列表只是多一次點擊。
> - 參考圖另有「儲存草稿」，但後端沒有草稿狀態（活動只有進行中／已結束），
>   依使用者裁決不實作。

---

## 37.3 Edit Form

進行中活動可修改：

- 名稱
- 分類
- 說明
- 圖片
- 是否支援滿贈

狀態不使用下拉選單任意切換。

> 修訂紀錄（2026-07-30，依參考圖 33）：活動**編輯頁**提供「進行中／已結束」的
> 選項組（radio，非下拉），新增頁不顯示（新活動一律進行中）。
> 這不是「任意切換」——選項變更後實際呼叫的仍是 §37.4 的 `/end` 與 `/reopen`
> 專用端點，`UpdateActivityRequest` 本身不含 status；狀態沒變動時不送這兩支請求。
> 列表頁的「結束活動／重新開啟」按鈕維持不變。

---

## 37.4 End Activity Modal

```text
結束活動

活動結束後將無法建立新的開團，
但歷史商品、開團與訂單仍會保留。

[返回] [確認結束]
```

已結束活動在列表以 Badge 顯示。

> 修訂紀錄：原文寫「第一版不提供重新開啟」，但後端在 Stage 5 就實作了
> `POST /admin/activities/{id}/reopen`，列表頁亦有「重新開啟」按鈕，
> 該限制已不成立，故刪除該句。

---

# 38. Admin Product Management

## 38.1 Product List

顯示：

- 商品圖片
- 商品名稱
- 活動
- 官方價格
- 幣別
- 狀態
- 關聯角色
- 操作

可使用簡單下拉選單依活動或上架狀態篩選。

---

## 38.2 Product Form

```text
所屬活動 *
[________________ v]

商品名稱 *
[________________]

官方價格 *
[59.00]

官方幣別 *
[CNY v]

主要圖片 *
[Image Uploader]

關聯角色
[今汐 ×] [長離 ×]
[輸入角色名稱____________]

商品狀態
[上架 v]

[儲存商品]
```

角色欄位使用可搜尋、可新增的多選輸入框，不使用需要捲動尋找的大型傳統下拉選單。

輸入「今」時可顯示：

```text
今汐
今州
```

找不到完全相同的角色時顯示明確操作：

```text
[新增角色「今汐」]
```

管理員必須點擊新增操作後才建立角色，不能只按 Enter 就直接建立。

選中的角色以可移除標籤顯示，一個商品可關聯多個角色。

---

## 38.2a Batch Product Create（新增改為批次）

> 新增紀錄（2026-07-30 使用者需求）。

`/admin/products/new` 改為**一次可建立多項商品**的批次頁；`/admin/products/:id`
仍是單項編輯表單（額外圖片管理只在編輯時有意義）。

版面：

```text
所屬活動 *            [3.4 版本周邊活動 v]
官方定價幣別          [TWD 新台幣 v]     ← 活動層級，套用整批

┌ 商品 1 ─────────────────────────── [移除] ┐
│ [主圖預覽]      商品名稱 *                  │
│ [上傳主圖]      官方定價（選填，TWD）        │
│                 關聯角色（選填）             │
└────────────────────────────────────────────┘
┌ 商品 2 …                                    ┐

        [ + 再新增一項商品 ]

                        [取消] [建立 N 項商品]
```

規則：

- **幣別放在活動層級**，不在每項商品內：同一活動的幣別必須一致
  （Business Rules §11.2a）。活動已有標價商品時**鎖定為既有幣別並說明原因**，
  不可修改——讓它可改到送出才報錯是白費工。
- 後端沒有批次端點，逐項送出。**部分失敗時**：已成功的項目標記「已建立」、
  變灰且不再重送；失敗的保留並顯示原因，修正後只補送剩下的。
  這樣重試不會建出重複商品。
- 用順序送出而非並行：一次打十幾個建立請求容易踩到後端的角色去重與唯一性檢查。
- 每項商品的圖片為自由比例，可裁切也可直接用原圖（見 §22a）。

**進入點會帶入活動**：

- 建立活動成功後直接導向本頁並帶 `activity_id`（新活動必然還沒有商品）
- 商品列表已篩選活動時，「新增商品」也帶 `activity_id`

單項編輯頁的幣別同樣會在「同活動已有其他標價商品」時唯讀
（依 docs/05 §28.3 的 `activity_currency` 欄位判斷，該欄位已排除商品自己）。

---

## 38.3 Extra Image Management

顯示：

```text
額外圖片

[圖片 1] [上移] [下移] [刪除]
[圖片 2] [上移] [下移] [刪除]

[上傳額外圖片]
```

第一版使用上移與下移調整順序，不要求拖曳排序。

---

## 38.4 Product Deactivation

```text
下架商品

商品下架後不再顯示於一般活動商品列表，
也不可加入新的開團。

歷史訂單資料不受影響。

[返回] [確認下架]
```

已下架商品提供：

```text
[重新上架]
```

---

# 39. Character Input and Maintenance

角色是全站共用資料，可跨不同活動與商品重複使用，不直接隸屬於單一活動。

第一版不提供獨立角色管理頁或 Route。

## 39.1 Search or Create in Product Form

管理員在新增或編輯商品時輸入角色名稱：

```text
關聯角色
[今汐 ×]
[今________________]

搜尋結果
今汐
今州
```

若沒有完全相同的結果：

```text
[新增角色「今祈」（立即建立）]
```

建立前需：

- Trim 前後空白
- 阻擋空白名稱
- 由後端再次檢查重複名稱

> 修訂紀錄（2026-07-30 使用者要求）：**點下新增就立即寫入資料庫**
> （`POST /admin/characters`），不再等商品送出時才由後端從 `new_name` 建立。
> 因此角色一經新增就存在，打錯字會留下錯誤資料 —— 標籤上必須提供刪除。
>
> 標籤有兩個動作，用顏色與 tooltip 區分，避免誤按：
>
> | 按鈕 | 作用 | 出現時機 |
> |---|---|---|
> | `✕` | 從**這個商品**移除關聯，角色留在資料庫 | 一律 |
> | 垃圾桶（紅色） | 從**資料庫刪除**這個角色 | 僅本次新建的角色 |
>
> 「僅本次新建」是刻意的限制：避免管理員在商品表單裡誤刪其他商品正在使用的既有角色。
> 後端另有第二層防線 —— 已有商品關聯的角色一律不可刪
> （`409 CHARACTER_HAS_PRODUCT_RELATIONS`，Business Rules §12.5）。
>
> 刪除角色時會從**本頁所有商品**的標籤中一併移除（同一角色可能已加到多項商品上）。
>
> 前端因此一律以 `{id}` 關聯角色；API 仍保留 `{new_name}` 的支援（契約未變）。

---

## 39.2 Simple Character Maintenance Modal

商品表單可提供小型入口：

```text
[編輯角色]
```

Modal 只處理目前選取或搜尋到的角色：

```text
編輯角色

角色名稱 *
[今汐____________]

關聯商品：12 項

[返回] [儲存名稱]
```

沒有關聯任何商品時，可顯示：

```text
[刪除角色]
```

已有商品關聯時，不顯示刪除按鈕，並提示需先解除所有商品關聯。

---

# 40. Admin User Management

## 40.1 User List

Route：

```text
/admin/users
```

顯示：

| Email | 暱稱 | 是否有團主資料 | 建立時間 | 操作 |
|---|---|---|---|---|

簡單篩選：

```text
全部
一般會員
具有團主資料
```

---

## 40.2 User Detail

Route：

```text
/admin/users/:userId
```

顯示：

- Email
- 暱稱
- 頭像
- 建立時間
- 團主申請狀態
- 是否具有團主資料

第一版不提供停用、重新啟用或刪除會員功能。

---

# 41. Admin Group Leader Application Review

## 41.1 List

顯示：

- 申請會員 Email
- 會員暱稱
- 申請時間
- 狀態
- 操作

篩選：

```text
待審核
已通過
已拒絕
```

---

## 41.2 Review Detail

```text
團主申請審核

會員 Email
user@example.com

會員暱稱
小游

申請時間
2026/08/01

目前狀態
待審核

[拒絕申請] [通過申請]
```

通過後，會員需自行完成團主公開名稱與至少一項公開聯絡方式。

> 修訂紀錄（2026-07-30，依參考圖 31 對照）：原文「第一版沒有申請說明、公開聯絡方式」
> 已不成立——申請說明於 2026-07-29（migration `0009_application_reason`）加入，
> 公開聯絡方式亦已顯示。現況版面：
>
> - 上方卡片：頭像＋會員暱稱／Email｜申請編號／申請時間｜狀態 Badge＋會員聯絡方式
>   （LINE／Discord／Facebook，各配品牌 icon，未填顯示「未設定」）
> - 下方兩欄：「申請說明（選填）」｜「審核重點」
> - 黃底提醒：通過後會員需完成團主公開資料
> - 操作：核准申請（紫底實心）／拒絕申請（**紅框白底**，非紅底實心）
>
> **刻意與參考圖不同之處**：
> 1. 申請編號用 UUID 前 8 碼（`#XXXXXXXX`），非參考圖的 `APP20260805001` ——
>    資料庫沒有這種流水編號，不虛構。
> 2. 聯絡方式區塊不重複列出 Email（左側身分區已顯示）。
> 3. 「審核重點」只列系統真的查得到的事實：平台沒有帳號停權／異常紀錄機制，
>    因此不做參考圖的「帳號狀態正常」判斷；純陳述現況的項目（如「尚未具有團主資格」）
>    用灰色減號 icon，成立的條件才用綠色勾。

**審核備註**：仍未提供（後端 approve／reject 不接受備註欄位）。

---

## 41.3 Review Confirmation

拒絕與通過都使用確認 Modal，不要求輸入原因。

申請已被其他管理員處理時：

- 顯示狀態衝突訊息
- 重新載入最新資料
- 不允許再次變更審核結果

---

# 42. Admin Group Leader Management

## 42.1 List

Route：

```text
/admin/group-leaders
```

顯示：

| 團主名稱 | 會員 Email | 資料是否完整 | 目前開團 | 完成訂單 | 操作 |
|---|---|---|---:|---:|---|

---

## 42.2 Detail

顯示：

- 團主公開名稱
- 對應會員
- 團主資料是否完整
- 公開聯絡方式
- 成為團主時間
- 目前開團數
- 完成訂單數
- 預設團規

第一版不提供停用、重新啟用或移除團主權限功能。

---

# 43. Admin Platform Announcement Management

## 43.1 List

顯示：

- 標題
- 發布時間
- 通知會員數
- 更新時間
- 編輯
- 刪除

平台公告主要顯示於會員通知中心，不建立公開公告詳情頁。

---

## 43.2 Create Form

```text
發布平台公告

公告標題 *
[________________________]

公告內容 *
[                          ]
[                          ]

[發布公告]
```

發布後通知所有已註冊會員。

---

## 43.3 Edit

顯示提示：

```text
儲存後，這則平台公告已建立的通知內容會同步更新，
但不會重新建立通知。
```

---

## 43.4 Delete

```text
刪除平台公告

刪除後，這則公告產生的通知會一併刪除。
其他系統與訂單通知不受影響。

[返回] [確認刪除]
```

第一版不提供公告停用功能。

---

# 44. Modal Specification

## 44.1 Close Behavior

Modal 可透過以下方式關閉：

- 點擊取消
- 點擊右上角關閉
- 按 Escape

提交中不可關閉需要 Transaction 的重要 Modal。

---

## 44.2 Destructive Modal

危險操作需清楚寫出影響。

不可只顯示：

```text
確定嗎？
```

應顯示：

```text
拒絕後訂單無法恢復。
```

---

## 44.3 Focus

開啟 Modal 後：

- Focus 移至 Modal
- Tab 不應跳到背景
- 關閉後 Focus 返回原按鈕

---

# 45. Form Validation and Feedback

## 45.1 Validation Timing

欄位錯誤可於：

- Blur
- Submit

時顯示。

不需在每次按鍵後立即顯示所有錯誤。

---

## 45.2 Required Text

文字必填欄位：

- Trim 前後空白
- 全空白視為未填
- 顯示清楚錯誤

---

## 45.3 Server Validation

API 回傳欄位錯誤時，需對應顯示於欄位下方。

非欄位錯誤顯示於表單上方。

---

## 45.4 Duplicate Submission

送出中：

```text
submitting = true
```

按鈕：

- Disabled
- 顯示 Loading
- 不得連續呼叫 API

---

# 46. Permission and Route States

## 46.1 Auth Initializing

AuthContext 尚在初始化時：

```text
顯示全頁 Loading
```

不得先導向登入。

---

## 46.2 Member Route

未登入：

```text
導向 /login
```

保存原 Route，登入後返回。

---

## 46.3 Group Leader Route

沒有團主資料：

```text
導向 /profile
```

團主資料尚未完成：

- `/group-leader/profile` 可正常進入
- 其他團主頁導向 `/group-leader/profile`
- 顯示需先完成公開名稱與公開聯絡方式

資料完成後顯示團主後台。

---

## 46.4 Admin Route

非管理員：

```text
顯示 403 頁面
```

第一版使用獨立 403 畫面。

---

## 46.5 Session Expiration

API 回傳 401：

```text
移除 Token
清除 AuthContext
保存目前 Route
導向 /login
```

重新登入後可返回原頁面，但不自動重新送出訂單或狀態操作。

---

# 47. Responsive Design

## 47.1 Desktop

建議 Breakpoint：

```text
>= 1024px
```

- 完整 Header
- Sidebar 固定顯示
- 多欄商品 Grid
- 後台使用 Table

---

## 47.2 Tablet

```text
768px ～ 1023px
```

- Header 部分收合
- Sidebar 可收合
- Grid 減少欄數
- 表格允許水平捲動

---

## 47.3 Mobile

```text
< 768px
```

- Header 使用 Menu
- Sidebar 使用 Drawer
- 商品卡片單欄或雙欄
- 商品圖片檢視支援左右滑動，並保留左右按鈕
- 後台 Table 改為 Card
- Modal 接近全螢幕寬度
- 表單欄位單欄排列
- 主要操作按鈕可全寬

---

## 47.4 Mobile Order Card

表格資料改為：

```text
訂單編號
WG-20260801-A1B2C3

會員
小游

活動
3.4 官方周邊

金額
NT$ 780

狀態
待確認

[查看詳情]
```

---

# 48. Accessibility Requirements

至少支援：

- 所有 Input 有 Label
- 圖片有 Alt
- Button 使用明確文字
- 互動元素可使用鍵盤操作
- Focus 狀態清楚
- Modal 與圖片 Lightbox 管理 Focus
- 圖片 Lightbox 支援鍵盤方向鍵與 Escape
- 觸控滑動功能同時提供可點擊按鈕
- 錯誤訊息與欄位建立關聯
- 不只使用顏色表達狀態
- 標題使用正確層級
- Icon Button 提供可讀名稱
- 表格使用正確欄位標題
- Loading 狀態提供可理解文字

---

# 49. React Component Organization

```text
src/
├─ components/
│  ├─ common/
│  │  ├─ Alert.jsx
│  │  ├─ Breadcrumb.jsx
│  │  ├─ Button.jsx
│  │  ├─ ConfirmModal.jsx
│  │  ├─ EmptyState.jsx
│  │  ├─ ErrorState.jsx
│  │  ├─ FormField.jsx
│  │  ├─ ImageLightbox.jsx
│  │  ├─ ImageUploader.jsx
│  │  ├─ Modal.jsx
│  │  ├─ PageLoader.jsx
│  │  ├─ Pagination.jsx
│  │  ├─ SearchableTagInput.jsx
│  │  ├─ SearchInput.jsx
│  │  └─ StatusBadge.jsx
│  │
│  ├─ activity/
│  │  ├─ ActivityCard.jsx
│  │  └─ ActivityFilter.jsx
│  │
│  ├─ product/
│  │  ├─ CharacterEditModal.jsx
│  │  ├─ CharacterTagInput.jsx
│  │  ├─ FavoriteButton.jsx
│  │  ├─ ProductCard.jsx
│  │  └─ ProductGallery.jsx
│  │
│  ├─ group-buy/
│  │  ├─ GroupBuyCard.jsx
│  │  ├─ GroupBuySettingsForm.jsx
│  │  ├─ GroupBuyProductEditor.jsx
│  │  └─ GroupBuyStepper.jsx
│  │
│  ├─ order/
│  │  ├─ CancellationRequestPanel.jsx
│  │  ├─ OrderCard.jsx
│  │  ├─ OrderItemList.jsx
│  │  └─ OrderStatusTimeline.jsx
│  │
│  ├─ notification/
│  │  └─ NotificationItem.jsx
│  │
│  ├─ group-leader/
│  │  ├─ DashboardStatCard.jsx
│  │  ├─ GroupLeaderCard.jsx
│  │  └─ GroupLeaderSidebar.jsx
│  │
│  └─ admin/
│     └─ AdminSidebar.jsx
```

元件名稱可於實作時微調，但職責需保持分離。

---

# 50. UI Acceptance Criteria

## Public Pages

- Header 依登入狀態正確顯示
- 首頁使用簡化介紹區且不顯示輪播圖
- 第一版不顯示 Footer
- 首頁只顯示活動卡片
- 活動頁商品卡片只顯示圖片與名稱
- 商品頁可查看多位團主開團
- 商品圖片可放大、左右切換，手機可滑動
- 搜尋結果在同一頁依商品與角色分區（活動分區已於 2026-07-23 經使用者決議移除，見 §10.1）
- 團主公開頁顯示目前開團、公開公告與預設團規
- 公開公告頁只顯示團主選擇公開的公告

## Authentication

- 登入與註冊具有完整欄位驗證
- 註冊頭像為選填，未上傳時使用預設頭像
- 登入失敗不透露 Email 是否存在
- Auth 初始化期間不錯誤跳轉
- 登入成功後可返回原 Route

## Member

- 個人資料至少保留一項聯絡方式
- 商品可以收藏及取消收藏
- 跟團清單只能屬於一筆開團
- 不同開團商品會出現替換確認
- 訂單送出前顯示團規確認
- 訂單失敗時保留跟團清單
- 訂單列表可依狀態篩選
- 訂單拒絕原因可在詳情查看
- 取消原因為選填，取消申請被拒後可再次提出
- 通知可以全部已讀，不提供會員刪除

## Group Leader

- 申請通過後需先完成公開名稱與公開聯絡方式
- Dashboard 使用簡化統計及快速入口
- 建立開團使用三步驟 Wizard
- 不支援草稿或重新開團
- 沒有訂單時可修改全部開團資料
- 有訂單後只可修改截止時間、聯絡方式及數量上限
- 商品上限不可低於占用數量
- 訂單操作依狀態顯示
- 拒絕訂單原因必填且不可修改
- 公告支援團主整體與特定開團兩種範圍
- 公告可選擇公開或不公開
- 公告編輯同步更新原通知，刪除時刪除原通知

## Administrator

- Dashboard 只顯示四項簡化統計
- 可以管理活動與商品
- 商品表單可搜尋既有角色或新增角色
- 不提供獨立角色管理頁
- 不提供角色改名介面（見 §51.39）
- 沒有商品關聯的角色才可刪除
- 商品額外圖片可使用上移與下移排序
- 可以審核團主申請
- 第一版不要求申請說明或審核備註
- 可以查看會員與團主資料
- 不提供會員帳號或團主權限停用介面
- 平台公告可建立、編輯與刪除

## Responsive

- 手機版 Header 可操作
- Sidebar 可收合
- Table 可轉為 Card 或水平捲動
- Modal 不超出畫面
- 商品圖片可使用觸控滑動
- 主要按鈕可在手機版正常使用

---

# 51. Final UI Decisions

1. 前端使用 React + Vite + JavaScript。
2. Route 使用 React Router。
3. 公開、會員、團主與管理員頁面使用不同 Layout。
4. AuthContext 只管理登入與權限狀態。
5. 一般頁面資料由 Page Component 管理。
6. 第一版使用一般 CSS，不使用 UI Framework。
7. Main Layout 不設置 Footer。
8. 首頁使用網站名稱與一句用途說明，不使用輪播圖。
9. 活動卡片圖片比例為 16:9，商品卡片圖片比例為 1:1。
10. 麵包屑保留於具有明確層級的頁面。
11. 搜尋結果在同一頁依商品與角色分區，不使用 Tabs（活動分區已移除，見 §10.1）。
12. 活動頁商品卡片只顯示圖片與名稱。
13. 商品頁負責顯示團主開團比較。
14. 商品圖片支援放大、左右切換、鍵盤方向鍵與手機滑動。
15. 團規使用獨立公開開團詳情頁顯示，商品頁與跟團清單提供入口。
16. 團主公開頁顯示預設團規，但各開團正式規則仍以該開團團規為準。
17. 收藏功能只收藏商品，已下架商品仍保留於收藏列表並標示。
18. 跟團清單一次只屬於一筆開團，失效時不自動刪除。
19. 送出訂單前必須顯示團規確認，正式資料由後端重新計算。
20. 訂單列表顯示代表圖片，訂單詳情顯示進度線。
21. 訂單拒絕原因必填，拒絕後不可恢復或修改原因。
22. 會員取消原因與團主拒絕回覆皆為選填。
23. 團主申請頁不要求申請說明、團主名稱或聯絡方式。
24. 申請通過後，需完成團主公開名稱與至少一項公開聯絡方式。
25. 團主 Dashboard 使用簡化卡片、最近訂單與快速入口。
26. 團主建立開團使用三步驟 Wizard，不支援草稿或重新開團。
27. 開團沒有訂單時可修改全部內容；有訂單後只可修改截止時間、聯絡方式與數量上限。
28. 數量上限不可低於目前有效訂單占用數量。
29. 團主公告分為團主整體公告與特定開團公告。
30. 團主可選擇公告是否公開；公開公告可從公開頁查看。
31. 公開公告沒有通知對象時仍可發布；不公開公告沒有通知對象時不可發布。
32. 公告修改同步更新該公告產生的通知，公告刪除時一併刪除相關通知。
33. 第一版不提供公告停用功能。
34. 管理員 Dashboard 只顯示待審核團主申請、進行中活動、上架商品與目前開團。
35. 角色是可跨活動使用的全站共用資料，不直接隸屬單一活動。
36. 第一版不建立獨立角色管理頁或 Sidebar 入口。
37. 商品表單使用可搜尋、可新增的角色多選輸入框。
38. 新增角色必須透過明確按鈕確認，不能只按 Enter 自動建立。
39. 不提供角色改名介面；沒有商品關聯時才可刪除。（2026-07-30 修訂：原訂「角色名稱可使用精簡 Modal 編輯」，但全站沒有安排任何適合改名的位置，經使用者裁決取消。後端 `PATCH /admin/characters/{id}` 保留但無前端入口。打錯字的處理方式是刪除後重新新增——新增角色時只要沒有商品關聯就能刪。）
40. 商品額外圖片使用上移與下移調整順序，不要求拖曳排序。
41. 第一版不提供會員帳號或團主權限停用介面。
42. 平台公告不建立獨立公開頁，主要顯示於會員通知中心。
43. 桌面版後台使用 Sidebar，手機版使用 Drawer。
44. 狀態不得只依賴顏色表示。
45. 所有主要頁面必須具有 Loading、Empty 與 Error State。
46. 所有重要操作使用確認介面，提交時阻止重複送出。
47. Route Guard 不取代後端權限驗證。
48. 第一版不加入付款、物流、聊天或評價介面。
49. 本文件作為第四份 Database Design 與第五份 API Design 的 UI 資料需求來源。

以下為後續補充的決議（編號續接，既有編號不重排以免影響交叉引用）：

50. 多角色商品的每角色接單上限可填 0＝不接該角色的單；輸入框 `min` 隨角色數切換（多角色 0、單一角色 1）。商品層級與單一角色的上限至少 1，全部角色都不接時應取消勾選該商品而非填 0。詳見 06 文件 §20.8。（2026-07-30）
51. 開團編輯頁的接單上限欄，多角色商品逐角色一列輸入，「已訂購」欄同樣逐角色一列以左右對齊，欄位下方顯示商品總上限。（2026-07-30）
52. 全站下拉選單使用同一組外觀，以圖 03 商品詳情頁「可跟團開團」的排序選單為標準：白底、1px 邊框、10px 圓角、40px 高、自繪箭頭。基準定義在 `styles/global.css` 的 `select` 元素選擇器，各頁只覆寫寬度與對齊等版面需求，不再各自重寫邊框、圓角與箭頭。（2026-07-30）
53. Facebook 聯絡方式一律顯示為「名稱超連結」（團主名稱、會員暱稱或申請人暱稱），不顯示網址原文；Discord 與 LINE 照原樣顯示 ID。判定不出網址時退回顯示原文。共用元件 `components/common/ContactValue.jsx`。（2026-07-30）
54. 輸入框與文字區塊同樣使用全站統一外觀，與下拉選單同一組語彙（白底、1px 邊框、10px 圓角、40px 高、0.9rem），基準定義在 `styles/global.css`。勾選框、單選鈕、檔案與滑桿不套用。撰寫全域元素基準時條件一律以 `:where()` 包裹，避免特異性高於各頁的 class 規則。登入頁、團主搜尋、個人資料等依參考圖另有明確高度者不受影響。（2026-07-30）
55. Header 搜尋框提供角色名稱建議清單：輸入後即時列出符合的角色與其關聯商品數，第一列固定為「搜尋『關鍵字』」（等同直接按 Enter 的全站搜尋），選取角色則直接前往該角色的商品清單（`/search?character_id=`）。支援方向鍵選擇、Enter 確認、Esc 與點擊外部關閉。（2026-07-30）
56. 搜尋結果頁的區塊順序為「角色」在「商品」之前。（2026-07-30）

---

# End of Document
