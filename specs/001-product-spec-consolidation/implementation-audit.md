# EchoGather Implementation-to-Requirements Audit

**文件類型：** 實作對規格稽核報告（唯讀盤點，非程式修改）
**日期：** 2026-08-04
**依據裁決：** 「目前基準版本中，所有使用者可操作、前端有入口、正式 API 可呼叫，或自動化測試明確保障的功能，都必須納入第一版正式需求。」（專案負責人，本次稽核指示）
**對照規格：** `docs/EchoGather_Product_Specification_v1.0.md`（v1.0，下稱「正式規格」）＋ `docs/CURRENT_DECISIONS.md`（v1.1，下稱 CD）

> **狀態註記（2026-08-04）**：本文件為正式收編前的稽核快照；
> B／C／D 類結果後續已依 CD v1.2 與正式規格同步，
> 最終處理結果見 tasks T052～T062。原始稽核內容保留，不改寫為事後結果
> （B-1、B-7 之 namespace 與分頁細節依同日最終一致性裁決補正）。

---

## 1. 實作基準

| 項目 | 值 |
|---|---|
| Commit | `0d5c43647112482e99ec734e5178877741504f90` |
| 分支 | `docs/product-spec-consolidation` |
| 工作區 | `M specs/001-product-spec-consolidation/tasks.md`、`?? docs/EchoGather_Product_Specification_v1.0.md`（皆為本 Feature 先前允許產出，非本次稽核異動） |

## 2. 盤點統計

| 面向 | 數量 | 備註 |
|---|---|---|
| 前端 Route | **40** | 公開 12、會員 9、團主 9、管理員 10（AppRoutes.jsx 全數列舉） |
| 前端 Page | 41 | pages/ 全數 |
| 前端 API 模組 | 24 | api/ 全數 |
| Context／Hook | 3／1 | Auth、Cart、Notification／useAutoRefresh |
| 後端 API Endpoint | **115** | api/v1 23 檔 114 個 ＋ main.py `GET /api/v1/health` |
| 後端 Service | 26 | services/ 全數 |
| 後端 Model 檔 | 14 | models/ |
| **實際資料表** | **25** | `__tablename__` 全數列舉（見 §8.16） |
| Alembic Migration | 14 | 0001～0014 |
| 測試檔 | 26 | tests/（含 test_health、test_group_leader_group_buy_stats_api） |

## 3. 分類總覽

| 分類 | 定義 | 數量（功能群） |
|---|---|---:|
| A | 已完整存在於正式規格 | **34** |
| B | 已實作，正式規格完全未記載 | **7** |
| C | 已實作，正式規格只記載部分行為 | **7** |
| D | 已實作，與正式規格直接衝突 | **3** |
| E | 純內部／工程實作細節 | 8 群 |
| F | Bug／安全缺口，不得升格 | 2 |

A 類（34 功能群，正式規格已完整涵蓋，僅列名）：註冊與 Email 驗證碼、登入登出與 Token、個人資料、私人聯絡方式、收藏核心行為、購物車全套（唯一性／累加／角色／替換／失效／團主限制）、下單交易、訂單狀態機、取消申請、訂單合併、拆單、訂單狀態歷史、已收金額顯示、團主申請（含選填原因與平台規範勾選）、團主資料與公開名稱、預設團規、開團建立、開團編輯凍結、每角色上限（含 0）、提前結單、開團可用狀態、開團比較、團主儀表板、我的開團、商品訂購總覽、訂單管理（單筆操作）、團主公告（範圍／零收件人／預覽／修改刪除）、平台公告、通知核心（列表／未讀數／已讀／導向）、管理員 Dashboard（含目前開團清單）、活動管理（含結束重開）、商品管理（含圖片排序上下架）、角色支援（搜尋／新增／刪除）、圖片上傳、公開瀏覽與搜尋（商品＋角色）。

---

## 4. B 類——已實作、正式規格完全未記載（7 項）

### B-1 忘記密碼／重設密碼
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 忘記密碼申請、重設連結驗證、重設密碼（**僅限一般用戶／Member namespace**：`request_password_reset` 使用 `user_repository.get_by_email`，該查詢只取 `role != admin`；僅 Admin 使用該 Email 時回通用成功但不寄信；第一版無 Admin 重設流程——2026-08-04 修正） |
| 使用者角色 | Visitor（未登入操作；目標帳號為一般用戶帳號） |
| 前端 Route／入口 | `/forgot-password`、`/reset-password`（LoginPage 提供入口連結） |
| 後端 Endpoint | `POST /auth/password-reset-requests`、`GET /auth/password-reset-tokens/{token}`、`POST /auth/password-reset` |
| 主要 Service | `auth_service`（＋`models/password_reset.py`、migration `0008_password_reset_token`） |
| 對應測試 | `test_auth_api.py` |
| 目前正式規格位置 | **無**（章 4 未載；章 20 亦未列為延後） |
| 缺少或衝突內容 | 完整功能未記載。注意：00 §5「明確排除項」列有「忘記密碼」，與現況衝突（該清單本身未被正式規格收錄，僅為舊矩陣記載） |
| 建議 REQ 主題代碼 | **AUTH**（REQ-AUTH-090 起：申請節流、Token 效期單次性、重設後行為） |
| 涉及更新 CD | **是**（CD 全文無忘記密碼；需新增決策條目） |
| 取代現有 D-NN | 否（新功能採認，無對應差異） |

### B-2 公開團主列表（團主目錄）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 公開團主列表：關鍵字（團主名稱）篩選、四種排序、統計欄位、分頁 |
| 使用者角色 | Visitor／全部 |
| 前端 Route／入口 | `/group-leaders`（**Header「團主」導覽入口**） |
| 後端 Endpoint | `GET /group-leaders`（`keyword`、`sort=created_desc/created_asc/group_buy_desc/completed_order_desc`、分頁） |
| 主要 Service | `group_leader_public_service.list_public_profiles`（回傳含 `group_buy_count`、`completed_order_count`） |
| 對應測試 | `test_public_content_api.py` |
| 目前正式規格位置 | 無（REQ-LEADER-100 僅載個別公開頁；ch17 端點總覽僅列 `/group-leaders/{id}`） |
| 缺少或衝突內容 | 整頁未記載；且 **REQ-SEARCH-010 驗收文字「Header 僅含 Logo、搜尋欄與登入狀態區」與 Header 實有「團主」入口矛盾**（CD §4 僅禁止活動／商品入口，未禁團主入口）。列表 keyword 為頁內篩選，與 CD §4「全站搜尋不搜團主名稱」不同層，無直接衝突但需明文區分 |
| 建議 REQ 主題代碼 | **LEADER**（公開目錄）＋修正 REQ-SEARCH-010 驗收文字 |
| 涉及更新 CD | **是**（CD §4 導覽結構需補「Header 提供團主入口」與團主目錄定位） |
| 取代現有 D-NN | 否 |

### B-3 單一開團接單商品列表（公開頁）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 某一次開團的完整接單商品清單頁（先看全部再挑一項下單） |
| 使用者角色 | Visitor／全部 |
| 前端 Route／入口 | `/group-buys/:groupBuyId/products`（自團主公開頁點活動進入） |
| 後端 Endpoint | 復用 `GET /group-buys/{id}`（無新端點） |
| 主要 Service | `group_buy_service` |
| 對應測試 | `test_public_content_api.py`（開團詳情） |
| 目前正式規格位置 | 無（ch18 REQ-UI-020 路由表未列；03 §4 亦無此 Route） |
| 缺少或衝突內容 | 頁面與路由未記載；瀏覽動線（團主頁→開團商品清單→單一商品購買）未載 |
| 建議 REQ 主題代碼 | **UI**（路由）＋ **GROUPBUY**（公開動線） |
| 涉及更新 CD | 建議補（CD §4 導覽） |
| 取代現有 D-NN | 否 |

### B-4 同一開團訂單一鍵標記已出貨
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 一鍵將指定開團全部「已付款」訂單標記為已出貨，回報略過筆數 |
| 使用者角色 | Group Leader |
| 前端 Route／入口 | `/group-leader/orders`（依開團篩選後的批次操作） |
| 後端 Endpoint | `POST /group-leader/group-buys/{group_buy_id}/orders/mark-all-shipped` |
| 主要 Service | `group_leader_order_service.mark_all_shipped`（僅處理 `paid`，其餘略過並回報） |
| 對應測試 | `test_group_leader_order_api.py` |
| 目前正式規格位置 | 無（REQ-ORDER-130 僅載單筆 paid→shipped；05 §24 無此端點） |
| 缺少或衝突內容 | 批次操作未記載（語意為多筆合法轉換的批次執行，不新增狀態） |
| 建議 REQ 主題代碼 | **ORDER**（批次出貨規則：範圍、略過語意、通知行為） |
| 涉及更新 CD | **是**（CD §7.4 操作清單需補批次出貨） |
| 取代現有 D-NN | 否 |

### B-5 Health Check（對外技術端點）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 服務健康檢查 |
| 使用者角色 | 系統／部署平台 |
| 前端 Route／入口 | 無（對外技術端點） |
| 後端 Endpoint | `GET /api/v1/health` → `{"data":{"status":"ok"}}` |
| 主要 Service | `main.py` 直接處理 |
| 對應測試 | `test_health.py` |
| 目前正式規格位置 | 無（ch17 端點總覽未列） |
| 缺少或衝突內容 | 技術需求未記載 |
| 建議 REQ 主題代碼 | **API**（技術端點） |
| 涉及更新 CD | 否（技術端點，規格層記載即可） |
| 取代現有 D-NN | 否 |

### B-6 申請審核頁自動刷新
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 30 秒輪詢＋切回分頁即時刷新（靜默更新） |
| 使用者角色 | Admin（申請列表／詳情）、Member（申請狀態頁） |
| 前端 Route／入口 | `/admin/group-leader-applications(/:id)`、`/group-leader-application` |
| 後端 Endpoint | 復用既有查詢端點 |
| 主要 Service | `frontend/src/hooks/useAutoRefresh.js`（hook 本身屬 E；「頁面自動更新」為使用者可見行為） |
| 對應測試 | 無後端測試（前端行為） |
| 目前正式規格位置 | 無 |
| 缺少或衝突內容 | 自動更新行為（頻率、可見性條件、靜默不閃動）未記載 |
| 建議 REQ 主題代碼 | **UI**（自動刷新行為） |
| 涉及更新 CD | 否 |
| 取代現有 D-NN | 否 |

### B-7 列表每頁筆數選擇器（2026-08-04 修正：三組規則，非全站一律）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 每頁筆數規則分三組——A：共用 `ListFooter` 選項 **5／10／20**、僅一頁仍顯示（/admin/activities、/admin/products、/admin/group-leader-applications、/admin/announcements、/group-leader/announcements）；B：頁內選項 **10／20／50**（/orders、/group-leader/group-buys、/group-leader/orders）；C：/favorites **固定每頁 8 筆**、有分頁、無選擇器；其他列表不因本項推定必須具有選擇器 |
| 使用者角色 | 依各頁角色 |
| 前端 Route／入口 | `ListFooter.jsx`（A 組五頁）；各頁自帶下拉（B 組）；FavoritesPage `PAGE_SIZE = 8`（C 組） |
| 後端 Endpoint | 既有 `page_size` 參數 |
| 主要 Service | — |
| 對應測試 | 各列表 API 測試涵蓋 page_size |
| 目前正式規格位置 | REQ-API-040 僅載後端預設 20／上限 100；UI 選擇器未載 |
| 缺少或衝突內容 | 使用者可操作的每頁筆數 UI（選項 5／10／20）未記載 |
| 建議 REQ 主題代碼 | **UI** |
| 涉及更新 CD | 否 |
| 取代現有 D-NN | 否 |

---

## 5. C 類——已實作、規格只記載部分行為（7 項）

### C-1 會員訂單列表進階篩選
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 我的訂單：狀態＋活動名稱＋團主名稱＋近 N 天＋分頁筆數 |
| 角色／入口 | Member／`/orders` |
| Endpoint | `GET /orders?status&activity_name&group_leader_name&created_within_days` |
| Service／測試 | `order_service.get_my_orders`／`test_order_api.py` |
| 規格位置 | ch8 僅載訂單規則；02 §15.1 僅載狀態篩選（引用層） |
| 缺少內容 | 活動名稱／團主名稱部分比對、近 N 天（1–365）篩選未載 |
| 建議代碼 | **ORDER**（列表查詢行為） |
| 更新 CD | 否（查詢功能，規格層補即可） |
| 取代 D-NN | 否 |

### C-2 收藏頁排序
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 收藏列表四種排序（加入時間新→舊／舊→新、名稱、官方價高→低） |
| 角色／入口 | Member／`/favorites` |
| Endpoint | `GET /favorites/products?sort=created_desc|created_asc|name_asc|price_desc` |
| Service／測試 | `favorite_service.list_favorites`／`test_favorite_api.py` |
| 規格位置 | REQ-PRODUCT-100／110 載收藏行為與下架顯示；排序未載 |
| 缺少內容 | 排序選項（依圖 11 下拉）與分頁 |
| 建議代碼 | **PRODUCT**（收藏列表行為） |
| 更新 CD | 否 |
| 取代 D-NN | 否 |

### C-3 通知摘要卡與類型篩選
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 通知中心右側摘要（未讀數＋系統／團主各總數）＋類型篩選下拉 |
| 角色／入口 | Member／`/notifications` |
| Endpoint | `GET /notifications/summary`、`GET /notifications?notification_type=` |
| Service／測試 | `notification_service`／`test_notification_api.py` |
| 規格位置 | REQ-ANN-140 載「篩選已讀或未讀」；REQ-ANN-130 載類型標籤 |
| 缺少內容 | 摘要卡（含 system_count／group_leader_count 為**總筆數含已讀**之定義）與**類型篩選**未載 |
| 建議代碼 | **ANN** |
| 更新 CD | 否（05 §20.2b 已記錄使用者決議，規格層補即可） |
| 取代 D-NN | 否 |

### C-4 管理員批次新增商品（含部分失敗重試）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 商品新增為批次頁：一次多列、逐項送出、成功項鎖定、失敗項保留原因可補送；幣別於活動層級選一次套用整批 |
| 角色／入口 | Admin／`/admin/products/new`（ProductBatchCreatePage） |
| Endpoint | 復用 `POST /admin/products`（**無批次端點**，前端逐項送出） |
| Service／測試 | `admin_product_service.create_product`／`test_admin_product_api.py` |
| 規格位置 | REQ-ADMIN-050 僅載「建立商品」；03 §38.2a 已載批次（引用層） |
| 缺少內容 | 批次建立流程、部分失敗語意（已成功不重送）、活動層級幣別一次選取 |
| 建議代碼 | **ADMIN** |
| 更新 CD | 否（03 §38.2a 為既有裁決紀錄） |
| 取代 D-NN | 否（與 D-14 相關但不取代） |

### C-5 Admin 活動列表搜尋篩選
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 活動管理列表：狀態篩選＋名稱關鍵字＋分頁；詳情含 product_count／group_buy_count |
| 角色／入口 | Admin／`/admin/activities` |
| Endpoint | `GET /admin/activities?status&keyword`；`GET /admin/activities/{id}` |
| Service／測試 | `admin_activity_service`／`test_admin_activity_api.py` |
| 規格位置 | REQ-ADMIN-040 載管理操作；查詢行為僅於引用層（05 §27.1） |
| 缺少內容 | 列表搜尋／篩選與詳情統計欄位未於規格層記載 |
| 建議代碼 | **ADMIN** |
| 更新 CD | 否 |
| 取代 D-NN | 否 |

### C-6 Admin 商品列表搜尋篩選
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 商品管理列表：活動／上下架／角色／關鍵字四維篩選＋分頁 |
| 角色／入口 | Admin／`/admin/products` |
| Endpoint | `GET /admin/products?activity_id&is_active&character_id&keyword` |
| Service／測試 | `admin_product_service.get_products`／`test_admin_product_api.py` |
| 規格位置 | 同 C-5（僅引用層 05 §28.1） |
| 缺少內容 | 四維篩選未於規格層記載 |
| 建議代碼 | **ADMIN** |
| 更新 CD | 否 |
| 取代 D-NN | 否 |

### C-7 送單確認與取消申請獨立路由
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 訂單確認獨立頁與取消申請獨立頁 |
| 角色／入口 | Member／`/orders/confirm`、`/orders/:orderId/cancel` |
| Endpoint | 復用 `POST /orders`、`POST /orders/{id}/cancellation-requests` |
| Service／測試 | `order_service`、`cancellation_service`／`test_order_api.py` |
| 規格位置 | 行為已載（REQ-ORDER-030：完整頁面區塊；REQ-ORDER-190～210）；**路由未載**（ch18 REQ-UI-020 無此二 Route；02 §14.1 原記載確認區塊於購物車頁內） |
| 缺少內容 | 兩條會員 Route 未列入路由總表 |
| 建議代碼 | **UI**（路由表補列） |
| 更新 CD | 否 |
| 取代 D-NN | 否 |

---

## 6. D 類——與正式規格直接衝突（3 項）

### D 級-1 Admin／Member 同 Email 雙帳號 namespace＋密碼決定登入帳號
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 管理員與一般用戶 Email 命名空間分離：同一 Email 可各有一個帳號；登入逐一比對密碼決定登入哪個帳號（同密碼時管理員優先） |
| 使用者角色 | Visitor（登入）、Admin、Member |
| 前端 Route／入口 | `/login`（依 is_admin 導向 `/admin`）、`/register` |
| 後端 Endpoint | `POST /auth/login`、`POST /auth/register` |
| 主要 Service | `auth_service.login`（list_by_email 逐一 verify）；migration `0014_admin_email_namespace`（兩個部分唯一索引） |
| 對應測試 | `test_auth_api.py`、`test_users_api.py` |
| 目前正式規格位置 | REQ-AUTH-040「Email 大小寫不敏感且**不可重複**」；REQ-ROLE-060 註「同一真人需另用一般會員帳號」（未說明可同 Email） |
| 衝突內容 | **直接衝突**：實作為「會員側唯一＋管理員側唯一」（同 Email 最多兩帳號），且為 **2026-07-31 使用者裁決**（記錄於 migration docstring 與 auth_service），但 CD v1.1（2026-08-03）§3.3 仍寫全域不可重複，正式規格照 CD 收錄 |
| 建議 REQ 主題代碼 | **AUTH**（namespace 規則＋登入解析規則）＋修正 REQ-AUTH-040、補充 REQ-ROLE-060 |
| 涉及更新 CD | **是**（CD §3.3 需依 2026-07-31 裁決修訂——裁決日晚於規則、早於 CD v1.1 定稿，屬 CD 漏收） |
| 取代現有 D-NN | 否（新衝突；若負責人確認採認，正式規格直接修訂，不需新 D） |

### D 級-2 活動搜尋端點（依新裁決採認）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 活動名稱搜尋（後端＋測試保障；前端不顯示） |
| 使用者角色 | Public（API 呼叫） |
| 前端 Route／入口 | 無（前端搜尋頁僅商品＋角色） |
| 後端 Endpoint | `GET /search/activities`；`GET /search` 回應含 activities 區段 |
| 主要 Service | `search_service`（activity_repository.search_activities） |
| 對應測試 | `test_public_content_api.py`（斷言活動區段） |
| 目前正式規格位置 | REQ-SEARCH-030（MUST：只搜商品與角色）＋D-01（後端殘留待同步） |
| 衝突內容 | 新裁決「正式 API 可呼叫或測試明確保障→納入需求」與 CD §4／REQ-SEARCH-030 直接衝突。採認即為「後端活動搜尋為正式技術需求、前端不顯示」的分層規格 |
| 建議 REQ 主題代碼 | **SEARCH**（分層：API 提供活動搜尋、前台 UI 不顯示）或維持排除（由負責人擇一） |
| 涉及更新 CD | **是**（CD §4 與 §16.1 需重裁：採認→改寫規則；不採認→維持 D-01 待移除） |
| 取代現有 D-NN | **是——取代 D-01**（採認後 D-01 差異消滅，轉為分層規格） |

### D 級-3 角色改名端點（依新裁決採認）
| 欄位 | 內容 |
|---|---|
| 功能名稱 | 修改角色名稱（API＋測試保障；無前端入口） |
| 使用者角色 | Admin（API 呼叫） |
| 前端 Route／入口 | 無（2026-07-30 裁決移除介面） |
| 後端 Endpoint | `PATCH /admin/characters/{character_id}` |
| 主要 Service | `admin_character_service.update_character` |
| 對應測試 | `test_admin_character_api.py` |
| 目前正式規格位置 | REQ-PRODUCT-090（不提供角色改名）＋D-10 |
| 衝突內容 | 新裁決採認範圍含「正式 API 可呼叫、測試明確保障」→ 與 CD §5.2「不提供改名」衝突。採認即為「API 層保留改名能力、無 UI 入口」的分層規格 |
| 建議 REQ 主題代碼 | **PRODUCT** 或 **ADMIN**（API 層能力）或維持排除（由負責人擇一） |
| 涉及更新 CD | **是**（CD §5.2 與 §16.10 需重裁） |
| 取代現有 D-NN | **是——取代 D-10**（採認後轉為分層規格） |

---

## 7. E 類（純內部工程，不升格）與 F 類（不得升格）

**E（8 群）**：repositories 層與私有 Service helper；schemas／Pydantic 模型本身；`client.js`／`tokenStorage.js`；Context 內部實作與 `useAutoRefresh` hook 本體；共用視覺元件（icons、MediaImage、PageLoader 等）；`order_number_counter` 取號機制（規格已載結果行為）；`tests/factories.py`／`utils.py`／`conftest.py`；alembic 版本管理本身。

**F（2 項，不得升格為需求）**：
1. **單一標價商品可改活動實際幣別**（幣別一致性檢查排除自身之漏洞）——已記錄於 D-14，維持缺陷定位。
2. **Admin 帳號部分會員端點未被後端一致排除**（若實測可呼叫）——屬 D-06 記載的權限缺口，維持缺陷定位，不因「可呼叫」而採認。

---

## 8. 指定特查項逐項結論

| # | 特查項 | 結論 |
|---|---|---|
| 8.1 | 忘記密碼與重設密碼 | **B-1**（3 端點＋2 頁＋獨立資料表；00 §5 排除清單與現況衝突） |
| 8.2 | Admin／Member Email namespace 與登入選擇 | **D-1**（2026-07-31 裁決已實作；CD 漏收） |
| 8.3 | 公開團主列表、搜尋、排序與統計 | **B-2**（含 Header「團主」入口；REQ-SEARCH-010 驗收文字需修正） |
| 8.4 | 單一開團接單商品列表 | **B-3**（`/group-buys/:id/products`，復用詳情 API） |
| 8.5 | 管理員批次新增商品與部分失敗重試 | **C-4**（前端逐項送出、無批次端點） |
| 8.6 | 會員訂單列表篩選、分頁與每頁筆數 | **C-1**＋**B-7** |
| 8.7 | 收藏頁排序、統計與分頁 | **C-2**（四種排序；統計＝分頁 total） |
| 8.8 | 通知摘要、類型篩選與自動刷新 | **C-3**（摘要＋類型篩選）；通知頁無輪詢，自動刷新在申請頁＝**B-6** |
| 8.9 | 同一開團訂單一鍵標記已出貨 | **B-4**（僅 paid、回報略過數） |
| 8.10 | 活動搜尋 | **D-2**（採認則取代 D-01） |
| 8.11 | 角色改名 | **D-3**（採認則取代 D-10） |
| 8.12 | Health Check | **B-5**（`GET /api/v1/health`＋test_health） |
| 8.13 | Admin 活動與商品列表的搜尋、篩選、統計 | **C-5**＋**C-6**（統計：活動詳情含兩計數；商品列表無 summary 卡） |
| 8.14 | 全部前端 Routes 是否存在於 UI 規格 | 40 條中 **34 條已載**；未載 6 條：`/forgot-password`、`/reset-password`、`/group-buys/:id/products`、`/group-leaders`、`/orders/confirm`、`/orders/:id/cancel`（見 B-1／B-2／B-3／C-7）。另 `/admin/products/new` 已載但語意變更為批次頁（C-4） |
| 8.15 | 全部 API Endpoint 是否有對應需求 | 115 個中 **107 個**可對應正式規格（直接或經 ch17 引用 05）；無對應 8 個：password-reset ×3（B-1）、`GET /group-leaders`（B-2）、mark-all-shipped（B-4）、health（B-5）、`GET /search/activities`（D-2）、`PATCH /admin/characters/{id}`（D-3） |
| 8.16 | 25 張資料表是否全列入正式規格 | **22 張已列**（REQ-DB-020）；未列名 3 張：`email_verification_code`（規則已載於 REQ-AUTH-020，表名未列）、`password_reset_token`（B-1）、`group_buy_product_character`（規則已載於 REQ-GROUPBUY-040，表名未列）。實際 25 張與 D-12 記載一致，本稽核已取得全名清單 |

## 9. 反向缺口（規格記載、實作不存在——非 A–F 分類，供負責人裁決）

| 項目 | 規格位置 | 實作現況 |
|---|---|---|
| `/announcements/:id` 公開公告詳情頁 | REQ-UI-020（源自 03 §4.1、§15） | AppRoutes 無此 Route；公開公告顯示於團主頁／開團頁，非公開者顯示於通知中心（05 §20.1 導向規則），03 §15 已過時 |
| `/group-leader/announcements/new`、`/:id` 獨立路由 | REQ-UI-020（源自 03 §4.3） | 實作為單一管理頁（圖 27 列表＋表單面板），無獨立子路由 |
| 開團「活動」可修改（無訂單時） | REQ-GROUPBUY-110（CD §10.3） | 已記錄為 D-15，本稽核維持原判 |

## 10. 無法判定的功能

**無。** 全部盤點項均可歸入 A–F 或反向缺口。

## 11. 建議後續處理彙總

1. **需專案負責人裁決 3 項**（D 類）：Email namespace 採認與 CD §3.3 修訂；活動搜尋採認（取代 D-01）或維持排除；角色改名採認（取代 D-10）或維持排除。
2. **CD 需新增／修訂條目**：忘記密碼（B-1）、團主目錄與 Header 團主入口（B-2）、一鍵出貨（B-4）、Email namespace（D-1）、（視裁決）搜尋與改名。
3. **正式規格 v1.1 待補**：B-1～B-7 新 REQ；C-1～C-7 補充行為；REQ-SEARCH-010 驗收修正；REQ-DB-020 補 3 張表名；ch18 路由表補 6 條；反向缺口 2 條路由自規格移除或改寫。
4. 上述修訂屬後續工作，本稽核未修改任何規格或程式檔案。

---
*稽核方法：全數靜態盤點（AppRoutes、pages、api、context、hooks、components、api/v1 路由裝飾器、services、schemas、models `__tablename__`、alembic versions、tests 檔名與關鍵測試、CD 與正式規格全文對照）；未執行任何測試、Migration、資料庫操作、套件安裝或部署。*
