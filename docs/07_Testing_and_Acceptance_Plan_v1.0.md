# 07_Testing_and_Acceptance_Plan_v1.0

**Project Name:** WuWaGroup  
**Document Type:** Testing and Acceptance Plan  
**Frontend:** React、Vite、JavaScript  
**Backend:** Python、FastAPI  
**Database:** PostgreSQL  
**Primary Test Tools:** pytest、FastAPI TestClient／httpx、Playwright  
**Related Documents:** Project Specification v2.1、User Flow v2.1、UI / Wireframe Specification v2.1、Database Design v2.1、API Design v2.1、Business Rules v1.0  
**Version:** 1.0  
**Last Updated:** 2026-07-18  

---

# Change Log

| Version | Date | Description |
|---|---|---|
| 1.0 | 2026-07-18 | 從零建立 WuWaGroup 第一版測試與驗收計畫，涵蓋前端、API、資料庫、權限、交易並行、瀏覽器與使用者驗收 |

---

# Table of Contents

1. Document Purpose  
2. Test Authority and Principles  
3. Test Scope  
4. Quality Objectives  
5. Test Types and Tools  
6. Test Environments  
7. Test Accounts and Data  
8. Priority and Defect Classification  
9. Entry and Exit Criteria  
10. Automation Strategy  
11. General Execution Rules  
12. Authentication and Member Test Cases  
13. Group Leader Test Cases  
14. Activity, Product, Character and Image Test Cases  
15. Public Browsing and Search Test Cases  
16. Group Buy Test Cases  
17. Follow List Test Cases  
18. Order, Queue and Quantity Test Cases  
19. Cancellation Request Test Cases  
20. Announcement and Notification Test Cases  
21. Administrator Test Cases  
22. API Contract, Permission and Security Test Cases  
23. Database, Transaction and Concurrency Test Cases  
24. UI, RWD and Browser Test Cases  
25. Critical End-to-End Scenarios  
26. User Acceptance Test  
27. Regression Test Set  
28. Traceability Matrix  
29. Test Execution Records  
30. Defect Report Template  
31. Release Acceptance Checklist  
32. Final Test Decisions  

---

# 1. Document Purpose

本文件將前六份正式規格轉換為可執行的測試與驗收依據，用於開發中驗證、整合測試、上線前驗收與回歸測試。

主要目的：

- 確認前端流程、API、資料庫與業務規則一致。
- 確認角色權限與私人聯絡資料不會外洩。
- 確認跟團數量、先喊順序、取消申請與公告通知在並行操作下仍正確。
- 提供可重複執行的自動化測試範圍。
- 定義第一版是否可上線的完成條件。

本文件不取代前六份規格。若測試案例與前六份文件衝突，依下列優先順序處理：Business Rules → API Design／Database Design → Project Specification／User Flow／UI Specification → 本文件。

---

# 2. Test Authority and Principles

## 2.1 Server and Database Are Final Authority

前端顯示、按鈕停用與 Route Guard 只改善使用者體驗。所有價格、數量、狀態、權限、擁有權與公告收件人規則，必須由 FastAPI 與 PostgreSQL 再次驗證。

## 2.2 Historical Data Must Remain Stable

訂單成立後，商品名稱、圖片、售價、團主名稱、聯絡方式與團規使用快照。後續資料變動不得改寫歷史訂單。

## 2.3 Failed Transactions Must Leave No Partial Result

建立訂單、替換跟團清單、審核團主、處理取消申請、發布／修改／刪除公告等操作失敗時，資料庫必須完整 Rollback。

## 2.4 Test Repeatability

自動化案例不得依賴執行順序；每個案例應建立自己的必要資料，完成後清除或由 Transaction Rollback 隔離。

---

# 3. Test Scope

## 3.1 Included

- React 頁面、表單、導向、錯誤顯示、Loading 與防重複提交。
- FastAPI Request／Response、狀態碼、錯誤碼、分頁、排序與篩選。
- PostgreSQL Constraint、Index、Transaction、Row Lock、快照與刪除規則。
- Visitor、Member、Group Leader、Administrator 的權限與資源擁有權。
- 團主申請、活動、商品、角色、圖片、開團、收藏、跟團清單、訂單、取消申請、公告與通知。
- 桌面版 Chrome、桌面版 Firefox、手機版 Chrome 尺寸。
- 上線前使用者驗收。

## 3.2 Excluded from First Version

- 線上付款、退款、物流串接、聊天室、評價、行動 App。
- Refresh Token、後端 Logout、會員帳號停用、團主資格停用、公告停用。
- Safari 實機與大量手機型號相容性。
- 壓力測試與災難復原的正式認證；僅執行核心並行與基本負載檢查。

---

# 4. Quality Objectives

| Quality Area | Acceptance Objective |
|---|---|
| Functional correctness | P0、P1 功能符合前六份規格，無錯誤狀態跳轉或資料遺失 |
| Data integrity | 不超賣、不產生半筆訂單、不合併加喊訂單、不破壞快照 |
| Security and privacy | 未登入或非擁有者無法取得私人聯絡資料與後台資料 |
| API consistency | Response、Error、Pagination、Money、Datetime 格式一致 |
| Usability | 核心流程可在桌面與手機尺寸完成，錯誤可理解且不清除有效輸入 |
| Compatibility | Chrome 與 Firefox 核心流程一致，手機版 Chrome 無阻擋操作問題 |
| Maintainability | 核心後端規則有自動化測試；不以無意義覆蓋率取代業務測試 |

---

# 5. Test Types and Tools

| Test Type | Main Tool | Focus |
|---|---|---|
| Backend unit test | pytest | Pydantic 驗證、Service 規則、狀態轉換、金額計算 |
| API integration test | pytest + TestClient／httpx | Endpoint、權限、錯誤碼、Transaction 與資料庫結果 |
| Database integration test | pytest + PostgreSQL test database | Constraint、Index、Row Lock、Rollback、Cascade |
| Frontend component test | React test tooling as implemented | 表單狀態、條件顯示、按鈕、錯誤與 Loading |
| End-to-end browser test | Playwright | Visitor／Member／Leader／Admin 完整流程 |
| Manual exploratory test | Browser DevTools | 邊界操作、RWD、視覺與非預期流程 |
| User acceptance test | Staging environment | 實際使用者能否完成核心任務 |

第一版不設定強制整體 Coverage 百分比。核心業務規則、權限、訂單交易、先喊順序、取消與公告同步必須有直接測試。

---

# 6. Test Environments

| Environment | Purpose | Database | Rules |
|---|---|---|---|
| Local | 開發與快速測試 | 本機獨立 PostgreSQL | 可重建；不得連正式資料庫 |
| Automated Test | pytest／CI | 專用測試資料庫 | 每次執行建立乾淨 Schema 或 Migration 後清理 |
| Staging | 上線前整合與 UAT | 獨立驗收資料庫 | 設定接近正式環境；不得使用真實敏感資料 |
| Production Smoke Test | 上線後最小檢查 | 正式資料庫 | 僅執行不破壞資料的查詢與受控測試帳號流程 |

### Browser Matrix

| Target | Required |
|---|---|
| Desktop Chrome latest stable | Yes |
| Desktop Firefox latest stable | Yes |
| Mobile Chrome viewport | Yes |
| Safari physical device | No, first version |

---

# 7. Test Accounts and Data

## 7.1 Standard Accounts

| Code | Role / State | Purpose |
|---|---|---|
| V-01 | Visitor | Public browsing and access denial |
| M-01 | Normal member | Favorites, follow list, orders and cancellation |
| M-02 | Normal member | Concurrent order and notification recipient deduplication |
| M-03 | Member with pending leader application | Application conflict |
| L-01 | Approved but incomplete leader profile | Completion gate tests |
| L-02 | Completed group leader | Group buy, order and announcement management |
| L-03 | Another completed group leader | Ownership isolation |
| A-01 | Administrator only | Admin management; no automatic leader permission |

## 7.2 Standard Activities and Products

- Open activities: `3.4 官方周邊`、`Solar5 主題周邊`。
- Ended activities: `3.3 官方周邊`、`日本二周年線下活動`。
- Active and inactive products in the same activity.
- Products with one character, multiple characters and no character.
- Group buys using bank transfer, cash on delivery／pickup payment and other payment method.

## 7.3 Data Rules

- 測試 Email 使用專用網域或隨機 UUID，避免重複。
- 測試聯絡資料不得使用真實個人資料。
- 金額使用可精確驗證的 TWD Decimal，例如 390.00。
- 並行測試固定記錄伺服器建立時間與 UUID，以驗證穩定排序。

---

# 8. Priority and Defect Classification

## 8.1 Test Priority

| Priority | Meaning | Examples |
|---|---|---|
| P0 | 阻擋上線 | 無法登入、超賣、越權取得私人資料、Transaction 產生半筆資料 |
| P1 | 核心功能 | 開團、正式下單、狀態更新、取消、公告與通知錯誤 |
| P2 | 一般功能 | 排序篩選、收藏、圖片順序、一般錯誤顯示 |
| P3 | 顯示與低風險 | 非阻擋文字、細微排版、低使用率邊界 |

## 8.2 Defect Severity

| Severity | Definition | Release Rule |
|---|---|---|
| S0 Critical | 資料外洩、資料毀損、超賣、完全無法使用 | 必須修正並回歸 |
| S1 Major | 核心流程無法完成或結果錯誤 | 原則上必須修正 |
| S2 Minor | 有替代方式但體驗或非核心結果不正確 | 評估後可延後 |
| S3 Cosmetic | 文字、間距或視覺小問題 | 可記錄至後續版本 |

---

# 9. Entry and Exit Criteria

## 9.1 Entry Criteria

- 相關功能已完成基本開發並通過 Lint／Build。
- Alembic Migration 可在空資料庫成功執行。
- 測試環境與測試帳號可用。
- API 規格與 Business Rules 沒有未決需求。
- 已知阻擋測試的環境問題已排除。

## 9.2 Exit Criteria

- 所有 P0 案例通過。
- 所有 P1 案例已執行，無未處理 S0／S1 缺陷。
- 核心 E2E 與 UAT 場景通過。
- Chrome、Firefox 與手機版 Chrome 核心流程通過。
- Migration、Rollback、並行下單與權限測試通過。
- 已知 S2／S3 缺陷有明確紀錄、風險與是否接受的決策。

---

# 10. Automation Strategy

## 10.1 Must-Automate Areas

- 註冊／登入驗證與 Token 到期。
- 團主申請唯一待審核限制及資料完成門檻。
- 開團編輯限制。
- 跟團清單替換 Transaction。
- 訂單建立、數量占用、Rollback、加喊獨立與先喊順序。
- 訂單狀態轉換與拒絕原因。
- 取消申請狀態、同時一筆 pending 與再次申請。
- 公告收件人、去重、公開零收件人、修改同步與刪除 Cascade。
- Ownership、角色權限與私人聯絡資料。

## 10.2 Recommended Test Layers

1. Service unit tests validate pure rules and state matrices.  
2. API integration tests validate authentication, ownership, database writes and error responses.  
3. Playwright covers only high-value user journeys, avoiding duplicate browser tests for every backend edge case.  
4. Manual exploratory tests focus on crop UI, responsive layout, visual clarity and unusual navigation.  

---

# 11. General Execution Rules

- 金額比較使用 Decimal，不使用 JavaScript 或 Python float 直接比較。
- Datetime API assertion 使用 UTC ISO 8601；前端顯示再驗證 Asia/Taipei。
- Ownership 測試對非擁有者優先期待 404，避免洩漏資源存在。
- 每個敏感按鈕至少測試一次快速雙擊／重複 Request。
- 所有錯誤案例同時檢查 HTTP Status、`error.code`、資料庫是否未被修改。
- 每個刪除案例檢查應刪除與應保留資料。
- 測試結果欄位使用：`Pass`、`Fail`、`Blocked`、`Not Run`。

---

# 12. Authentication and Member Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| AUTH-001 | P0 | 成功註冊會員 | Email 未使用 | 輸入有效 Email、8～72 字元且含英文與數字的密碼、暱稱、至少一項聯絡方式；送出 | 201；建立會員；頭像可為 null；不回傳 Token；前端導向登入 | BR 6.1～6.4；API Auth Register | Not Run |
| AUTH-002 | P1 | Email Trim、轉小寫與不分大小寫唯一 | 已存在 member@example.com | 以 ` Member@Example.com ` 註冊 | 回傳 EMAIL_ALREADY_EXISTS；不建立第二筆會員 | BR-AUTH-001～005 | Not Run |
| AUTH-003 | P1 | 至少一項私人聯絡方式 | 無 | 三項聯絡方式皆 null 或空白 | 422 CONTACT_REQUIRED；不建立會員 | BR 6.1；7.2 | Not Run |
| AUTH-004 | P1 | 密碼最小長度與內容 | 無 | 分別提交 7 字元、只有英文、只有數字的密碼 | 422 VALIDATION_ERROR；指出密碼規則；不建立會員 | BR 6.3 | Not Run |
| AUTH-005 | P2 | 密碼最大長度 | 無 | 提交 72 字元有效密碼，再提交 73 字元密碼 | 72 字元成功；73 字元回 422 | BR 6.3 | Not Run |
| AUTH-006 | P1 | 密碼確認一致 | 無 | password 與 password_confirmation 不同 | PASSWORD_CONFIRMATION_MISMATCH；不建立會員 | BR-AUTH-006 | Not Run |
| AUTH-007 | P0 | 正確登入與 Session 建立 | 有效會員 | 輸入正確 Email、密碼；登入後取得 auth/me | 200；Access Token 有效 8 小時；auth/me 回傳正確會員與 permissions | BR 6.5；API Login／auth/me | Not Run |
| AUTH-008 | P0 | 錯誤登入不洩漏帳號存在 | 一個存在與一個不存在 Email | 分別輸入錯誤密碼 | 兩者皆 401 AUTH_INVALID_CREDENTIALS，訊息一致 | BR-AUTH-005、008 | Not Run |
| AUTH-009 | P1 | Token 到期處理 | 過期 Token；目前頁有 redirectPath | 進入受保護頁或提交操作 | 401 AUTH_TOKEN_EXPIRED；清除登入狀態；導向登入；登入後回原頁；敏感操作不自動重送 | BR 6.5～6.6 | Not Run |
| AUTH-010 | P1 | 註冊成功不自動登入 | 無 | 完成註冊後檢查 sessionStorage 與頁面 | sessionStorage 無 Token；顯示登入頁 | BR 6.4 | Not Run |
| AUTH-011 | P1 | Email 不可由會員修改 | 已登入會員 | PATCH users/me 額外傳入 email | 422 或忽略禁止欄位；資料庫 Email 不變 | BR-AUTH-004；API Current User | Not Run |
| AUTH-012 | P0 | 密碼與 Token 不出現在 Log／Response | 可檢視測試 Log | 執行成功與失敗登入 | Response、錯誤與 Log 不含明文密碼、hash、完整 Token | BR-AUTH-007、009；Security | Not Run |
| PROF-001 | P1 | 會員讀取自己的完整資料 | M-01 已登入 | GET users/me | 回傳 Email、暱稱、頭像、私人聯絡方式與申請／團主摘要；不包含密碼 | BR 7.1～7.5 | Not Run |
| PROF-002 | P2 | 更新暱稱與頭像 | M-01 已登入 | PATCH users/me 傳入新暱稱、avatar_url | 資料更新；Email 與角色不變 | BR 7.1 | Not Run |
| PROF-003 | P1 | 更新聯絡方式後仍至少一項 | M-01 有一項聯絡方式 | 將所有聯絡方式清空 | 422 CONTACT_REQUIRED；原資料保留 | BR 7.2 | Not Run |
| PROF-004 | P2 | 空白聯絡方式正規化 | M-01 | PATCH contacts，部分欄位傳 `   ` | 空白欄位存為 null，仍保留至少一項有效聯絡方式 | BR 2.3；7.2 | Not Run |
| PROF-005 | P0 | 私人聯絡方式不可由公開 API 取得 | Visitor 或其他會員 | 查詢公開商品、活動、團主、公告與搜尋 API | Response 不含會員私人聯絡方式 | BR 7.3；31.2 | Not Run |
| PROF-006 | P0 | 團主只看自己訂單會員的聯絡快照 | L-02 與 L-03 各有訂單 | L-02 讀自己與 L-03 的訂單詳情 | 自己訂單可見快照；他人訂單回 404 | BR 5.5；7.5；31.2 | Not Run |
| PROF-007 | P1 | 訂單聯絡快照不受會員後續修改影響 | M-01 已建立訂單 | 修改會員聯絡方式後讀舊訂單 | 舊訂單仍顯示建立時快照；新訂單使用新資料 | BR 7.5；19.6 | Not Run |

---

# 13. Group Leader Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| LEAD-001 | P1 | 送出最簡團主申請 | M-01 無 pending 申請與團主資料 | POST group-leader-applications，Body 空物件或無額外欄位 | 201；狀態 pending；不要求名稱、原因、公開聯絡方式 | BR 8.1 | Not Run |
| LEAD-002 | P1 | 同時只能一筆 pending 申請 | M-03 已有 pending | 再次 POST 申請 | 409 GROUP_LEADER_APPLICATION_PENDING；無新資料 | BR 8.3 | Not Run |
| LEAD-003 | P1 | 拒絕後可重新申請 | 最新申請 rejected | 再次 POST 申請 | 建立新 pending；保留舊申請歷史 | BR 8.4 | Not Run |
| LEAD-004 | P1 | 已有團主資料不可再申請 | L-01 或 L-02 | POST 申請 | 409 GROUP_LEADER_PROFILE_ALREADY_EXISTS | BR 8.2 | Not Run |
| LEAD-005 | P0 | 核准申請原子性 | pending 申請 | A-01 核准 | 申請 approved 且建立一筆不完整 profile；任一步失敗全部 Rollback | BR 8.5～8.6；DB transaction | Not Run |
| LEAD-006 | P1 | 拒絕申請不要求 review note | pending 申請 | A-01 以空 Body 拒絕 | 申請 rejected；review note 不存在；可再次申請 | BR 8.5、8.7 | Not Run |
| LEAD-007 | P0 | 不完整團主只能編輯資料 | L-01 | 嘗試開團、發布公告、查看團主後台其他功能 | 阻擋並導向 profile completion；公開團主頁不可見 | BR 9.1 | Not Run |
| LEAD-008 | P1 | 完成團主公開資料 | L-01 | 設定唯一 display_name 與至少一項公開聯絡方式 | profile_completed=true 或等價計算結果；可公開、開團、公告 | BR 9.1～9.3 | Not Run |
| LEAD-009 | P1 | 團主名稱全域唯一且大小寫不敏感 | L-02 名稱為 月影團 | L-01 設定相同名稱或大小寫變體 | GROUP_LEADER_DISPLAY_NAME_UNAVAILABLE；原資料不變 | BR-LEADER-001～002 | Not Run |
| LEAD-010 | P1 | 團主名稱設定後不可修改 | L-02 已設定名稱 | PATCH profile 傳入新 display_name | 欄位不接受或回衝突；名稱不變 | BR-LEADER-003～005 | Not Run |
| LEAD-011 | P2 | 修改介紹與公開聯絡方式 | L-02 completed | PATCH profile 修改 introduction 與 contacts | 更新成功；仍至少一項公開聯絡；名稱不變 | BR 9.3 | Not Run |
| LEAD-012 | P2 | 預設團規只影響新開團 | L-02 已有舊開團 | 更新 default_rules，再建立新開團 | 舊開團團規不變；新開團可帶入新預設值 | BR 9.4 | Not Run |
| LEAD-013 | P1 | 公開團主頁內容正確 | L-02 completed | Visitor GET public leader profile | 顯示頭像、名稱、介紹、公開聯絡、加入時間、統計、目前開團、公開公告；不含私人聯絡 | BR 9.5；14.6 | Not Run |

---

# 14. Activity, Product, Character and Image Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| ACT-001 | P1 | 動態建立活動 | A-01 | 建立 `墜夢奇境`，不提供固定分類 | 201；首頁 open 區自動出現；資料無 activity_type | BR 10.1～10.2 | Not Run |
| ACT-002 | P2 | 活動預設新到舊 | 多筆活動不同 created_at | GET activities | created_at DESC；open／ended 依篩選正確 | BR 10.5 | Not Run |
| ACT-003 | P1 | 活動結束 | open 活動 | POST admin activities/{id}/end | status=ended；不可建立新開團；既有開團 effective_status=activity_ended | BR 10.3～10.4 | Not Run |
| ACT-004 | P1 | 活動重新開啟 | ended 活動；其中有已提前結單開團 | POST reopen | status=open；活動可新開團；已提前結單開團仍 closed | BR 10.4 | Not Run |
| ACT-005 | P1 | 活動名稱必填但不要求全域唯一 | 已有同名活動 | 建立空白名稱；再建立與既有活動相同或相似名稱 | 空白回 422；相似或相同名稱可建立不同活動；不建立空白名稱資料 | BR 10.2、10.6；DB | Not Run |
| PROD-001 | P1 | 建立 TWD 商品 | open 活動 | 建立 active product，輸入官方價格、主圖與名稱 | 201；official_currency 固定 TWD；同活動名稱唯一 | BR 11.1～11.3；28.1 | Not Run |
| PROD-002 | P1 | 同活動商品名稱不可重複 | 活動內已有壓克力立牌 | 建立相同名稱或正規化後重複名稱 | 409；不建立第二筆 | BR 11.3 | Not Run |
| PROD-003 | P2 | 不同活動可使用相同商品名稱 | 兩項活動 | 分別建立同名商品 | 兩筆皆成功 | BR 11.3 | Not Run |
| PROD-004 | P1 | 商品下架與重新上架 | active 商品且有收藏／歷史訂單 | deactivate 後查公開頁與收藏，再 reactivate | 公開列表／搜尋不顯示；收藏仍顯示已下架；歷史資料保留；重新上架後恢復公開 | BR 11.4；23.4 | Not Run |
| PROD-005 | P2 | 活動商品卡只顯示圖片與名稱 | active product | 瀏覽 activity detail | 卡片無角色標籤與價格；可進商品詳情 | BR 11.5 | Not Run |
| CHAR-001 | P1 | 角色建議搜尋與明確新增 | 已有今汐；輸入不存在名稱 | 商品表單輸入部分名稱；選既有；再按 `新增角色「名稱」` | 選既有建立 chip；不存在角色只有明確按鈕後才建立 | BR 12.2～12.4 | Not Run |
| CHAR-002 | P1 | 角色 Trim、大小寫不敏感唯一與去重 | 已有角色 | 以空白、前後空白、大小寫變體建立或重複加到同商品 | 空白拒絕；重複名稱 conflict；同商品不重複關聯 | BR-CHAR-001～005 | Not Run |
| CHAR-003 | P1 | 有商品關聯角色不可刪除 | 角色關聯商品 | DELETE character | 409 CHARACTER_HAS_PRODUCT_RELATIONS | BR 12.5 | Not Run |
| CHAR-004 | P2 | 無關聯角色可修正名稱與刪除 | unlinked character | PATCH name，再 DELETE | 名稱更新；刪除成功；不影響其他角色 | BR 12.5 | Not Run |
| IMG-001 | P1 | 支援 JPG、PNG、WebP | 各格式有效檔案 | 依角色上傳 avatar/activity/product | 成功；實際內容驗證通過；可轉存 WebP | BR 13.1、13.6 | Not Run |
| IMG-002 | P1 | 無前端固定檔案大小限制但有伺服器安全上限 | 設定測試安全上限 | 上傳低於與高於安全上限檔案 | 低於成功；高於以明確錯誤拒絕；服務不失效；前端不宣稱固定產品限制 | BR 13.2 | Not Run |
| IMG-003 | P2 | 自由裁切固定比例圖片 | 可操作裁切介面 | 上傳非目標比例圖片，拖曳、縮放、選擇範圍後確認 | 頭像／主商品圖 1:1；活動 16:9；裁切範圍符合使用者選擇 | BR 13.3～13.4 | Not Run |
| IMG-004 | P2 | 額外商品圖片不強制比例且可排序 | 商品有三張額外圖 | 上傳不同比例；使用上／下按鈕調整順序 | 不裁成固定比例；sort_order 按操作更新；詳情輪播依新順序 | BR 13.4、13.7 | Not Run |
| IMG-005 | P2 | 商品圖庫放大與導覽 | 商品多圖 | 點主要圖、左右切換、手機橫向滑動 | 放大檢視正確；首尾與縮圖狀態正確；手機可滑動 | BR 13.8；UI | Not Run |

---

# 15. Public Browsing and Search Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| PUB-001 | P1 | 首頁動態活動區 | 多筆 open／ended 活動 | Visitor 開首頁 | 簡化 Hero；目前與已結束活動依狀態與 created_at 顯示；無固定分類與 Footer | BR 14.1；UI Home | Not Run |
| PUB-002 | P1 | 全域搜尋三區摘要 | 活動、商品、角色均有匹配 | GET search?q=今&limit_per_type=5 | activities/products/characters 分區；各區有 total_count；不共用單一 pagination | BR 14.2～14.4 | Not Run |
| PUB-003 | P2 | 各搜尋區查看更多分頁 | 商品結果超過一頁 | GET search/products page=2；另測 activity、character | 每類獨立 pagination；不影響其他類型 | BR 14.4；API Search | Not Run |
| PUB-004 | P1 | 搜尋空白字串拒絕 | 無 | q 為空白 | 422 SEARCH_QUERY_REQUIRED | BR 14.3 | Not Run |
| PUB-005 | P1 | 公開搜尋不顯示下架商品 | active 與 inactive matching products | Visitor 搜尋 | 只回 active；角色 related_product_count 依公開規則一致 | BR 14.5 | Not Run |
| PUB-006 | P2 | 角色結果可連到相關商品 | 角色有多項商品 | 點角色結果或使用 character_id 搜尋 | 顯示該角色 active 商品；count 正確 | BR 12.1；14.2 | Not Run |
| PUB-007 | P1 | Breadcrumb 導航 | 商品、開團與團主頁 | 依序進入深層頁並點 Breadcrumb | 路徑與返回頁正確；手機不阻擋主要操作 | BR 14.7；UI | Not Run |
| PUB-008 | P1 | 公開開團與團規頁 | 可用與不可用開團 | Visitor 查看 detail、rules、availability | 顯示價格、付款、二補、滿贈、期限、聯絡、剩餘量與有效狀態；不可用原因正確 | BR 16.7～16.8；17.5 | Not Run |

---

# 16. Group Buy Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| GB-001 | P0 | 只有完整團主可建立開團 | Member、L-01、L-02 | 三者分別 POST group-leader/group-buys | 只有 L-02 成功；其他回權限或 profile incomplete 錯誤 | BR 15.1 | Not Run |
| GB-002 | P1 | 建立前先選 open activity | open 與 ended activity | 分別選擇建立 | open 成功；ended 回 ACTIVITY_NOT_OPEN | BR 15.2 | Not Run |
| GB-003 | P1 | 至少一項且只能選該活動 active 商品 | 多活動、active/inactive products | 提交空 products、跨活動、inactive、重複商品 | 各自 422／409；不建立部分開團 | BR 15.3 | Not Run |
| GB-004 | P1 | 付款方式銀行匯款 | L-02 | payment_method=bank_transfer | 建立成功；不要求 payment_method_note | BR 15.5 | Not Run |
| GB-005 | P1 | 取貨付款付款方式 | L-02 | payment_method=cash_on_delivery | 建立成功；商品頁可用「付款方式＝取貨付款」篩選找到 | BR 15.5；17.3 | Not Run |
| GB-006 | P1 | 其他付款方式必填說明 | L-02 | payment_method=other，分別不傳與傳入說明 | 無說明 422；有說明成功並公開顯示 | BR 15.5 | Not Run |
| GB-007 | P1 | 二補、滿贈與期限驗證 | open activity | 提交期限已過、滿贈不符合活動、有效組合 | 無效拒絕；有效建立 | BR 15.6～15.8 | Not Run |
| GB-008 | P1 | 團規與主要聯絡不可空 | L-02 | 團規或 contact_value 空白 | 422；不建立開團 | BR 15.9 | Not Run |
| GB-009 | P1 | 無正式訂單時可完整編輯 | 開團 order_count=0 | 修改付款、二補、滿贈、團規、期限、聯絡、價格、上限、增刪商品 | 全部合法欄位成功；公開頁立即反映 | BR 16.1～16.2 | Not Run |
| GB-010 | P0 | 有正式訂單後凍結核心欄位 | 開團已有至少一張訂單 | 嘗試修改付款、二補、滿贈、團規、價格、商品集合 | 409 GROUP_BUY_FIELD_LOCKED 或等價錯誤；資料不變 | BR 16.3 | Not Run |
| GB-011 | P1 | 有訂單後仍可改期限與聯絡 | 已有正式訂單 | PATCH deadline、contact | 更新成功；舊訂單快照不變；新訂單使用新快照 | BR 16.3、16.5；19.6 | Not Run |
| GB-012 | P0 | 接單上限不可低於占用量 | occupied_quantity=12 | 將 max_quantity 設 11、12、20 | 11 回 MAX_QUANTITY_BELOW_OCCUPIED；12、20 成功；available 即時計算 | BR 16.4 | Not Run |
| GB-013 | P1 | 提前結單不可重開 | open group buy | close 後嘗試新增清單、下單與重開 | status closed；不可跟團／下單；無 reopen API 或回 conflict | BR 16.6 | Not Run |
| GB-014 | P1 | effective status 優先原因 | 組合 expired、activity ended、full、closed | 查 detail 與列表 | effective_status 與 is_available 按規則一致；不保存錯誤衍生值 | BR 16.7～16.8 | Not Run |
| GB-015 | P1 | 預設開團新到舊 | 同商品多開團 | GET products/{id}/group-buys 無 sort | created_at DESC | BR 17.1 | Not Run |
| GB-016 | P2 | 價格與截止時間排序 | 多筆不同價格／期限 | 依 price_asc、price_desc、deadline_asc、deadline_desc 查詢 | 順序完全正確；相同值有穩定次排序 | BR 17.2 | Not Run |
| GB-017 | P2 | 開團篩選組合 | 資料涵蓋 available、付款方式、二補、滿贈 | 單項與多項組合篩選 | 只回同時符合條件資料；清除篩選恢復完整列表 | BR 17.3～17.4 | Not Run |
| GB-018 | P1 | 公開剩餘量不代表保留 | remaining=1；兩會員同時查看 | 兩人皆看到 1，先後送單 | 顯示可相同；只有先完成 Transaction 者成功，另一人數量不足 | BR 17.5；18.6；20.7 | Not Run |

---

# 17. Follow List Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| FL-001 | P1 | 一人一張、只屬於一筆開團 | M-01 無清單 | 加入 GB-A 商品 | 建立一張 follow_list 與 item | BR 18.1 | Not Run |
| FL-002 | P1 | 相同商品再次加入累加數量 | 同商品 quantity=2 | 再加入 quantity=3 | 同一 item quantity=5，不新增重複 item | BR 18.2 | Not Run |
| FL-003 | P1 | 同開團不同商品加入同清單 | GB-A 清單 | 加入 GB-A 第二商品 | 同一 follow_list 新增 item | BR 18.3 | Not Run |
| FL-004 | P0 | 不同開團未確認替換時保留原清單 | 已有 GB-A 清單 | 加入 GB-B，replace_existing=false | 409 FOLLOW_LIST_GROUP_BUY_CONFLICT；原清單完整保留 | BR 18.4 | Not Run |
| FL-005 | P0 | 不同開團替換為單一 Transaction | 已有 GB-A 清單 | 加入 GB-B，replace_existing=true；模擬建立新 item 失敗 | 成功時完整替換；失敗時 GB-A 原清單仍完整存在 | BR 18.4；30.1、30.4 | Not Run |
| FL-006 | P1 | 數量必須大於零 | 有效清單 | 新增或更新 quantity=0／負數 | 422 INVALID_QUANTITY；原數量不變 | BR 18.5 | Not Run |
| FL-007 | P1 | 清單不保留數量 | remaining=1 | M-01 加入清單但不下單；M-02 下單 | M-02 可占用；M-01 清單保留但變為不可送出 | BR 18.6～18.7 | Not Run |
| FL-008 | P1 | 失效清單保留並標記原因 | 清單建立後開團截止／商品額滿／活動結束 | GET follow-list | 清單與 items 保留；is_submittable=false；顯示原因；可移除或清空 | BR 18.7 | Not Run |
| FL-009 | P2 | 刪除最後項目同時移除空清單 | 清單只有一 item | DELETE item | 204；follow_list 一併刪除；GET 回 data null | BR 18.8 | Not Run |
| FL-010 | P2 | 清空清單具冪等性 | 有或無清單 | DELETE follow-list 兩次 | 皆 204；無殘留資料 | BR 18.8；API idempotency | Not Run |

---

# 18. Order, Queue and Quantity Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| ORD-001 | P0 | 未確認團規不可下單 | 有效清單 | rules_accepted=false 或缺少 | RULES_NOT_ACCEPTED；訂單不建立；清單保留 | BR 19.1 | Not Run |
| ORD-002 | P0 | 後端不信任前端價格與快照 | 有效清單 | 嘗試額外提交低價、假名稱、假總額 | 禁止欄位被拒絕或忽略；訂單採資料庫價格與快照 | BR 19.2 | Not Run |
| ORD-003 | P0 | 成功建立正式訂單 | 可用開團與有效清單 | POST orders rules_accepted=true | 201；pending_confirmation；建立 order/items/snapshots；商品總額正確；清單於 commit 後清除 | BR 19.3～19.6 | Not Run |
| ORD-004 | P0 | 下單失敗完整 Rollback 且保留清單 | 有效清單；模擬 snapshot 或 item 寫入失敗 | POST order | 無 order／partial items；數量未占用；清單完整保留 | BR 19.4～19.5；30.4 | Not Run |
| ORD-005 | P1 | 訂單歷史快照穩定 | 已建立訂單 | 修改商品名稱／圖片、團主聯絡、團規後讀舊訂單 | 舊訂單全部維持建立時資料 | BR 19.6；32.5 | Not Run |
| ORD-006 | P1 | 加喊建立獨立訂單 | M-01 已對同開團有第一張訂單 | 重新建立清單並送出第二張 | 建立不同 order_id／order_number；不合併 items 或數量 | BR 19.7；20.5 | Not Run |
| ORD-007 | P0 | 先喊順序使用 created_at ASC、id ASC | 同開團多筆訂單 | 查團主訂單列表 | 較早建立排前；同 timestamp 以 id ASC 穩定排序 | BR 20.4～20.6 | Not Run |
| ORD-008 | P0 | 第二張加喊必排在第一張後 | 同會員第一張已成立 | 立即送第二張並查列表 | 第二張排序在第一張後，不因同會員而合併或提前 | BR 20.5 | Not Run |
| ORD-009 | P0 | 占用量只計特定狀態 | 各狀態訂單 | 計算 group_buy_product occupied_quantity | pending_confirmation、pending_payment、paid、shipped、completed 均占用；只有 cancelled、rejected 釋放占用 | BR 20.1～20.3 | Not Run |
| ORD-010 | P0 | 取消／拒絕釋放數量 | 占用量達上限 | 拒絕訂單或核准取消 | occupied 減少；available 增加；其他會員可下單 | BR 20.3；21.4；22.6 | Not Run |
| ORD-011 | P0 | 並行下單不超賣 | remaining=1；M-01、M-02 各要 1 | 同步送出兩個 POST orders | 恰一筆成功；另一筆 INSUFFICIENT_AVAILABLE_QUANTITY／conflict；occupied 不超過 max | BR 20.7；30.2～30.3 | Not Run |
| ORD-012 | P0 | 並行多商品鎖定無死鎖且原子 | 兩清單含相同多商品、順序相反 | 同步下單 | 依 UUID 固定順序鎖定；無長時間死鎖；每張訂單全成或全敗 | BR 30.2～30.4 | Not Run |
| ORD-013 | P1 | 會員訂單列表狀態篩選 | M-01 多狀態訂單 | GET orders?status=paid 等 | 只回本人且符合狀態；代表圖為第一項商品圖 | BR 19.8；User Flow | Not Run |
| ORD-014 | P0 | 訂單擁有權隔離 | M-01、M-02 各有訂單 | M-02 GET M-01 order | 404；無內容外洩 | BR 5.5；29.4 | Not Run |
| ORD-015 | P1 | 接受訂單合法轉換 | pending_confirmation | L-02 accept | pending_payment；建立系統通知；重複 accept 回 conflict | BR 21.2～21.3 | Not Run |
| ORD-016 | P0 | 拒絕原因必填且不可修改 | pending_confirmation | 無原因 reject；有原因 reject；之後嘗試修改 | 無原因 422；有原因變 rejected 並釋放數量；原因不可改；訂單不可恢復 | BR 21.4 | Not Run |
| ORD-017 | P1 | 付款、出貨、完成狀態鏈 | pending_payment | mark-paid → mark-shipped → complete；另嘗試跳級 | 合法鏈成功；跳級或重複操作回 ORDER_STATUS_CONFLICT | BR 21.5～21.8 | Not Run |
| ORD-018 | P1 | 商品總額只含商品項目 | 需要二補且有後續運費描述的開團 | 建立含多商品訂單 | 商品總額=sum(unit_price×quantity)，不包含二補、國際／國內運費與其他費用；標籤為「商品總額」 | BR 28.2～28.4 | Not Run |

---

# 19. Cancellation Request Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| CAN-001 | P1 | 允許狀態可提出取消 | pending_confirmation、pending_payment、paid 各一筆 | 會員建立 cancellation request | 各建立 pending request；order 狀態暫時不變 | BR 22.1、22.5 | Not Run |
| CAN-002 | P1 | 禁止狀態不可提出取消 | shipped、completed、cancelled、rejected | 建立 request | CANCELLATION_NOT_ALLOWED；無資料建立 | BR 22.2 | Not Run |
| CAN-003 | P2 | 取消原因選填與空白轉 null | 可取消訂單 | 不傳 reason、傳空白、傳文字 | 前兩者 reason=null；文字保留 | BR 22.3 | Not Run |
| CAN-004 | P1 | 同時最多一筆 pending | 已有 pending request | 再次申請 | CANCELLATION_REQUEST_ALREADY_EXISTS；不建立第二筆 pending | BR 22.4 | Not Run |
| CAN-005 | P0 | 核准取消原子更新 | pending request；order 為占用狀態 | L-02 approve，可有或無 response_note | request approved、order cancelled、數量釋放、通知建立；任一步失敗全部 Rollback | BR 22.6；30.1 | Not Run |
| CAN-006 | P1 | 拒絕取消保留訂單狀態 | pending request；order pending_payment | reject request | request rejected；order 仍 pending_payment；response_note 可 null | BR 22.7 | Not Run |
| CAN-007 | P1 | 被拒後符合條件可再次申請 | 已有 rejected request；order 仍 paid | 再次申請 | 建立新 pending；舊 rejected 歷史保留 | BR 22.8～22.9 | Not Run |
| CAN-008 | P1 | 被拒後狀態已變 shipped 不可再申請 | rejected history；order shipped | 再次申請 | CANCELLATION_NOT_ALLOWED | BR 22.2、22.8 | Not Run |
| CAN-009 | P0 | 取消申請擁有權與團主權限 | 其他會員／其他團主 | 他人建立或處理 request | 404 或權限拒絕；資料不變 | BR 5.5；29.4 | Not Run |
| CAN-010 | P1 | 訂單詳情顯示取消歷史 | 同訂單有 rejected 歷史與目前 pending | 會員與所屬團主讀詳情 | 可識別目前 pending 與歷史紀錄；其他人不可見 | BR 22.9 | Not Run |

---

# 20. Announcement and Notification Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| ANN-001 | P0 | 未完成團主不可發布公告 | L-01 | POST group-leader/announcements | profile incomplete error；無 announcement／notification | BR 24.1 | Not Run |
| ANN-002 | P1 | 團主整體未完成訂單範圍 | L-02 多開團；會員含未完成與完成訂單 | 建立 scope=leader_unfinished 公告 | 收件人為曾跟該團主且仍有未完成訂單的 distinct users；完成／取消／拒絕不納入 | BR 24.2～24.4 | Not Run |
| ANN-003 | P1 | 指定開團未完成訂單範圍 | GB-A 各狀態訂單 | 建立 scope=group_buy_unfinished、group_buy_id=GB-A | 只通知 GB-A 中 pending_confirmation、pending_payment、paid、shipped 的 distinct users | BR 24.2～24.4 | Not Run |
| ANN-004 | P0 | 相同會員多筆訂單只收一則 | M-01 對範圍內有兩筆未完成訂單 | 發布公告 | M-01 只有一筆 announcement notification；recipient_count 去重 | BR 24.4 | Not Run |
| ANN-005 | P1 | 公開公告零收件人仍可發布 | 範圍無未完成訂單 | is_public=true 發布 | 201；recipient_count=0；leader_unfinished 顯示於團主頁，group_buy_unfinished 顯示於指定開團頁 | BR 24.5～24.6 | Not Run |
| ANN-006 | P1 | 不公開公告零收件人不可發布 | 範圍無未完成訂單 | is_public=false 發布 | 409 ANNOUNCEMENT_NO_RECIPIENTS；無公告 | BR 24.6 | Not Run |
| ANN-006A | P1 | 零收件人公開公告不可改為不公開 | 已存在 recipient_count=0、is_public=true 公告 | PATCH is_public=false | 409 ANNOUNCEMENT_NO_RECIPIENTS；公告仍維持公開；通知集合不變 | BR 24.6、24.9 | Not Run |
| ANN-007 | P1 | 標題與內容必填且純文字 | L-02 | 空白 title/content；含 HTML script 文字 | 空白拒絕；HTML 不執行，依純文字保存／顯示 | BR 24.7；29.6；31.5 | Not Run |
| ANN-008 | P0 | 發布公告與通知原子性 | 有收件人 | 模擬通知寫入中途失敗 | 公告與所有通知皆不建立；無部分收件人 | BR 30.5 | Not Run |
| ANN-009 | P0 | 修改公告同步既有通知 | 公告已有已讀與未讀通知 | PATCH title/content | 相關通知 title/message 同步；不新增通知；read status/read_at 不變 | BR 24.9；26.6 | Not Run |
| ANN-010 | P0 | 刪除團主公告只刪相關通知 | 會員另有系統與其他公告通知 | DELETE announcement | 公告及其 notification 刪除；其他通知保留 | BR 24.10；26.6；32.4 | Not Run |
| ANN-011 | P0 | 團主只能管理自己的公告與開團 | L-02、L-03 | L-02 指定 L-03 group_buy 或修改／刪除 L-03 公告 | 404／ANNOUNCEMENT_GROUP_BUY_MISMATCH；無資料變動 | BR 5.5；24.2 | Not Run |
| ANN-012 | P1 | 平台公告通知所有已註冊會員 | 多名會員含團主與管理員帳號 | A-01 建立平台公告 | 所有已註冊會員各一通知；無獨立公開公告頁 | BR 25.1～25.3 | Not Run |
| ANN-013 | P0 | 平台公告修改同步通知 | 平台公告已產生通知 | PATCH admin announcement | 既有通知同步內容，不重發、不改已讀 | BR 25.4；26.6 | Not Run |
| ANN-014 | P0 | 平台公告刪除 Cascade | 平台公告與通知 | DELETE admin announcement | 只刪該公告及其通知 | BR 25.5；32.4 | Not Run |
| NOTI-001 | P1 | 通知列表、未讀數與來源導向 | 各來源通知 | GET notifications／unread-count；點擊通知 | 排序正確；count 正確；依 source 導向訂單、公告或申請相關頁 | BR 26.1～26.5 | Not Run |
| NOTI-002 | P2 | 單筆已讀具冪等性 | 未讀通知 | PATCH read 兩次 | 第一次設定 read_at；第二次保持原 read_at | BR 26.3～26.4 | Not Run |
| NOTI-003 | P2 | 全部已讀不影響他人 | M-01、M-02 均有未讀 | M-01 read-all | 只更新 M-01；回 updated_count；M-02 不變 | BR 26.4 | Not Run |
| NOTI-004 | P1 | 無一般通知刪除 API | 會員已登入 | 嘗試 DELETE notifications/{id} | 404／405；通知保留，除非來源公告被刪除 | BR 26.4；32.4 | Not Run |

---

# 21. Administrator Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| ADM-001 | P1 | Admin Dashboard 僅回簡化統計 | A-01 | GET admin/dashboard | pending applications、open activities、active products、current group buys 與 quick links；無停用統計 | BR 27.1 | Not Run |
| ADM-002 | P0 | 管理員不自動取得團主功能 | A-01 無 group_leader_profile | 呼叫 group-leader endpoints | 拒絕；Admin role 不代表 leader | BR 5.4；27.7 | Not Run |
| ADM-003 | P1 | 只有管理員可審核申請 | pending application | M-01、L-02、A-01 分別 approve/reject | 只有 A-01 成功 | BR 27.2 | Not Run |
| ADM-004 | P1 | 管理員活動生命週期 | A-01 | create、update、end、reopen | 全部符合活動規則；無固定分類 | BR 27.3；10 | Not Run |
| ADM-005 | P1 | 管理員商品與圖片管理 | A-01 | create、update、deactivate、reactivate、extra images reorder/delete | 狀態、歷史保留與圖片順序正確 | BR 27.4；11；13 | Not Run |
| ADM-006 | P1 | 角色只以支援型 API 管理 | A-01 | suggestions、explicit create、rename、delete unlinked | 無獨立複雜角色分頁需求；規則正確 | BR 27.5；12 | Not Run |
| ADM-007 | P1 | 管理員平台公告管理 | A-01 | create、update、delete | 通知原子性與同步正確；沒有 disable API | BR 27.6；25 | Not Run |
| ADM-008 | P1 | 已移除後台範圍不可存取 | A-01 | 嘗試 admin users、admin group-leaders、suspend/deactivate/announcement disable 舊路由 | 404／405；UI 無入口 | BR 27.7；33.2 | Not Run |

---

# 22. API Contract, Permission and Security Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| API-001 | P1 | Response envelope 一致 | 可成功呼叫的單筆、列表、Action | 檢查 JSON | 單筆／Action 使用 data；列表使用 data+pagination；刪除可 204 | API Response Format | Not Run |
| API-002 | P1 | Error envelope 一致 | 觸發 validation、ownership、conflict | 檢查錯誤 JSON | error.code、message、details 格式一致；無 stack trace | API Error Format；BR 29 | Not Run |
| API-003 | P2 | Pagination 邊界 | 列表資料超過一頁 | page=0、page_size=0、101、正常值 | 無效 422；正常 pagination 計數一致 | API Pagination | Not Run |
| API-004 | P1 | Money 使用字串與 Decimal | 含小數金額 | 讀寫價格與訂單總額 | JSON 為字串兩位小數；資料庫 NUMERIC；無浮點誤差 | API Money；BR 28 | Not Run |
| API-005 | P1 | Datetime UTC 傳輸 | 測試固定時間 | 檢查 API 與 UI | API ISO 8601 UTC Z；UI Asia/Taipei 正確換算 | API Datetime；BR 28.5～28.6 | Not Run |
| API-006 | P0 | JWT 缺少、無效與過期 | 三種 Token 狀態 | 呼叫受保護 API | 401 與相應 error code；不執行資料修改 | BR 31.1；API Auth | Not Run |
| API-007 | P0 | 角色權限矩陣 | Visitor、Member、Leader、Admin | 呼叫 public/member/leader/admin endpoints | 只允許規格角色；Admin 不自動 leader | BR 5；API Permission Matrix | Not Run |
| API-008 | P0 | 資源擁有權以 404 隱藏存在 | 他人 order/group-buy/announcement | 非 owner GET/PATCH/DELETE | 404；Response 不含目標資訊 | BR 5.5；29.4 | Not Run |
| API-009 | P0 | SQL Injection 防護 | 搜尋、keyword、文字欄位 | 提交典型 SQL injection 字串 | 視為普通字串或驗證拒絕；資料庫未遭修改；無 SQL 錯誤洩漏 | BR 31；API Security | Not Run |
| API-010 | P0 | XSS 防護與純文字 | 公告、團規、介紹輸入 | 提交 `<script>`、事件屬性等 | 不執行；React 不用 dangerouslySetInnerHTML；內容安全顯示 | BR 29.6；31.5 | Not Run |
| API-011 | P1 | 圖片上傳權限與內容驗證 | 不同角色、偽造副檔名 | Member 上傳 activity；Admin 上傳 avatar；偽裝格式 | 不符 category 權限拒絕；實際內容不符拒絕；無路徑穿越 | BR 13.6；31.4 | Not Run |
| API-012 | P1 | CORS 限制 | 允許與未允許 Origin | 發送 preflight／API Request | 允許 Origin 成功；未知 Origin 不取得授權；正式環境非 wildcard | API CORS | Not Run |
| API-013 | P1 | 重複提交保護 | 可建立資源的表單 | 快速雙擊或送出相同並行 request | 前端按鈕 disabled；後端 Constraint／Transaction 防止重複或安全回 conflict | BR-GEN-007；29.5 | Not Run |

---

# 23. Database, Transaction and Concurrency Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| DB-001 | P0 | Migration 從空資料庫成功 | 空 PostgreSQL database | 執行 Alembic upgrade head | 所有 table、enum、constraint、index 建立；無手動修補 | Database Design | Not Run |
| DB-002 | P1 | Migration 可在既有測試資料升級 | 上一版結構與合法資料 fixture | 執行升級 | 資料保留或按 migration 計畫轉換；無意外遺失 | Database Design／Alembic | Not Run |
| DB-003 | P0 | Email 與團主名稱 case-insensitive unique | 既有正規化資料 | 直接 DB 插入大小寫重複 | Constraint／Index 阻擋 | BR-AUTH；BR-LEADER；DB indexes | Not Run |
| DB-004 | P1 | 同活動商品名稱唯一 | activity/product | 直接插入同 activity 重複名稱與不同 activity 同名 | 前者阻擋；後者允許 | BR 11.3；DB constraint | Not Run |
| DB-005 | P1 | 角色全域唯一與關聯唯一 | character/product | 插入重複角色、重複 product-character relation | DB 阻擋重複 | BR 12.1～12.4 | Not Run |
| DB-006 | P0 | 取消申請 partial unique pending | 同 order 有 rejected history | 建立新 pending，再建立第二 pending | 第一筆允許；第二筆由 partial unique index 阻擋 | BR 22.4、22.8；DB | Not Run |
| DB-007 | P0 | 公告通知 user+announcement 唯一 | 同會員多訂單 | 嘗試建立重複 announcement notification | DB unique 阻擋；recipient_count 去重 | BR 24.4；DB | Not Run |
| DB-008 | P0 | 公告刪除 Cascade 僅影響關聯通知 | 多來源通知 | 刪除 announcement row | 相關 notifications cascade；order/application/system 其他通知保留 | BR 24.10、25.5、32.4 | Not Run |
| DB-009 | P0 | 訂單拒絕原因狀態 Constraint | group_order | 直接寫 rejected+null reason、非 rejected+reason | 資料庫／Service 規則阻擋不一致資料 | BR 21.4；DB constraint | Not Run |
| DB-010 | P0 | 開團 max quantity 與 occupied 檢查 | occupied=5 | 交易中將上限改 4 | Service 鎖定並拒絕；無 race 造成 max<occupied | BR 16.4；30 | Not Run |
| DB-011 | P0 | Row Lock 競爭與 Rollback | 並行 order fixture | 兩 transaction 鎖相同 group_buy_product；一筆故意失敗 | 另一筆取得最新狀態再驗證；失敗 transaction 不留下寫入 | BR 30.2～30.4 | Not Run |
| DB-012 | P1 | 歷史資料刪除策略 | 訂單、收藏、圖片、角色、公告等關聯 | 執行允許與禁止的刪除 | 歷史訂單／快照保留；可直接刪除項目依規格；有關聯角色禁止刪除 | BR 32 | Not Run |

---

# 24. UI, RWD and Browser Test Cases

| Case ID | Priority | 測試目的 | 前置條件 | 操作步驟與輸入資料 | 預期結果 | 相關規則／文件 | 測試結果 |
|---|---|---|---|---|---|---|---|
| UI-001 | P1 | 桌面 Chrome 核心流程 | Desktop Chrome | 完成瀏覽→登入→加入清單→下單→查看訂單 | 無阻擋錯誤；畫面與資料一致 | UI／User Flow | Not Run |
| UI-002 | P1 | 桌面 Firefox 核心流程 | Desktop Firefox | 重跑核心 Member 與 Leader 流程 | 功能與 Chrome 一致 | Browser Matrix | Not Run |
| UI-003 | P1 | 手機版 Chrome 導航 | Mobile viewport | 操作主導航、搜尋、商品、清單、通知、個人頁 | 導航可開關；不遮擋內容；主要按鈕可點 | UI Mobile Navigation | Not Run |
| UI-004 | P2 | 活動 16:9 與商品 1:1 顯示 | 多尺寸圖片 | 查看首頁、活動、商品卡 | 不變形；裁切與 object-fit 一致 | BR 13.4；UI | Not Run |
| UI-005 | P1 | 表單 Loading 與防雙送 | 模擬慢速 API | 提交註冊、下單、公告、審核 | 按鈕 disabled／顯示進度；不產生重複資料 | BR 29.5 | Not Run |
| UI-006 | P1 | API 驗證錯誤映射到欄位 | 表單無效資料 | 觸發 VALIDATION_ERROR fields | 對應欄位顯示訊息；其他輸入保留 | API Error；UI forms | Not Run |
| UI-007 | P1 | 下單確認為完整頁面區段 | 有效清單 | 進下單確認頁 | 清楚顯示商品、商品總額、團規與勾選；不是小型 Modal | User Flow Decision 7 | Not Run |
| UI-008 | P1 | 下單失敗保留畫面與清單 | 造成數量不足 | 提交訂單 | 顯示最新原因；清單與數量仍可編輯；不跳到成功頁 | BR 19.5 | Not Run |
| UI-009 | P2 | 開團排序與篩選控制 | 多筆開團 | 切換所有排序與可跟團／付款方式／二補／滿贈篩選 | URL／狀態與結果一致；可清除；預設新到舊 | BR 17 | Not Run |
| UI-010 | P2 | 通知點擊導向與已讀 | 未讀通知 | 點擊通知 | 標記已讀並進相關頁；若來源公告已刪除，顯示可理解狀態 | BR 26.5 | Not Run |
| UI-011 | P2 | 基本鍵盤與可讀性 | 桌面瀏覽器 | Tab 操作表單、按鈕、Dialog／裁切器 | 焦點可見、順序合理、可用鍵盤完成主要操作；label 對應欄位 | General usability | Not Run |
| UI-012 | P3 | 無 Footer 與簡化 Hero 一致 | 公開頁 | 檢查首頁與各頁底部 | 無 Footer；Hero 非輪播；不出現未規格功能入口 | UI Decisions | Not Run |

---

# 25. Critical End-to-End Scenarios

下列場景必須以 Playwright 或 staging 手動完整執行。每個場景需保存執行日期、瀏覽器、測試帳號、結果與證據。

| Scenario ID | Priority | Scenario | Steps | Acceptance |
|---|---|---|---|---|
| E2E-001 | P0 | 新會員完成首次下單 | Visitor 瀏覽活動與商品 → 註冊 → 回登入 → 登入返回原商品 → 加入跟團清單 → 查看團規並勾選確認 → 正式下單 → 查看訂單詳情 | 建立一張 pending_confirmation 訂單；清單清空；資料與快照正確 |
| E2E-002 | P0 | 團主申請至首次開團 | 會員申請團主 → 管理員核准 → 團主設定唯一名稱與公開聯絡 → 建立開團 → 公開商品頁看到新開團 | 核准前不可開團；完成資料後可開團；公開資料無私人聯絡 |
| E2E-003 | P0 | 先喊與加喊 | 兩會員競爭有限數量；其中一人完成第一張後再加喊第二張 | 不超賣；訂單依伺服器順序；第二張不合併且排在第一張後 |
| E2E-004 | P0 | 訂單完整狀態流程 | 團主 accept → mark paid → mark shipped → complete；會員每步查看通知與訂單 | 狀態合法前進；每步通知導向正確；不可跳級 |
| E2E-005 | P0 | 取消申請拒絕後重申與核准 | 會員在 pending_payment 申請 → 團主拒絕 → 會員再次申請 → 團主核准 | 保留兩筆歷史；同時僅一 pending；核准後訂單 cancelled 並釋放數量 |
| E2E-006 | P0 | 團主公告生命週期 | 發布指定開團公告 → 會員收到去重通知 → 部分會員讀取 → 團主修改 → 團主刪除 | 修改同步且不重設已讀；刪除只移除該公告通知 |
| E2E-007 | P1 | 活動結束與重新開啟 | 管理員結束活動 → 公開開團不可下單 → 管理員重新開啟 | 活動重新可建立新團；提前結單開團不自動重開 |
| E2E-008 | P1 | 下架商品歷史保留 | 會員收藏與下單 → 管理員下架商品 → 查看搜尋、收藏與訂單 → 重新上架 | 搜尋隱藏；收藏顯示下架；訂單不變；重新上架恢復 |

---

# 26. User Acceptance Test

## 26.1 UAT Participants

- 一名一般會員使用者。
- 一名實際會管理團購的團主使用者。
- 一名管理員／專案負責人。

## 26.2 UAT Tasks

| UAT ID | Persona | Task | Pass Condition | Result |
|---|---|---|---|---|
| UAT-001 | Member | 在不知道內部資料結構的情況下找到指定活動與商品，選擇合適開團 | 能理解排序、篩選、價格、付款、剩餘量、二補、滿贈與截止時間 | Not Run |
| UAT-002 | Member | 完成註冊、登入、收藏、加入清單與下單 | 無需協助即可完成；清楚知道商品總額不含後續費用 | Not Run |
| UAT-003 | Member | 發現清單失效後處理 | 能看懂原因，清單不消失，可修改或清空 | Not Run |
| UAT-004 | Member | 查看訂單進度與提出取消 | 能找到狀態、拒絕原因、取消結果與相關通知 | Not Run |
| UAT-005 | Group Leader | 完成申請核准後建立公開資料與第一團 | 能理解必填條件；不會誤把私人聯絡資料當公開資料 | Not Run |
| UAT-006 | Group Leader | 管理訂單、先喊順序、取消申請與公告 | 能明確辨識不可合併的加喊訂單與可執行操作 | Not Run |
| UAT-007 | Administrator | 審核團主、建立活動／商品、管理角色與平台公告 | 能在簡化後台完成所有第一版管理任務 | Not Run |

## 26.3 UAT Sign-off

| Field | Value |
|---|---|
| UAT Date |  |
| Build / Commit |  |
| Staging URL |  |
| Member Sign-off |  |
| Group Leader Sign-off |  |
| Administrator Sign-off |  |
| Accepted Exceptions |  |
| Final Decision | Accepted / Rejected |

---

# 27. Regression Test Set

## 27.1 Smoke Regression on Every Merge

- Backend test database migration.
- Public activities, product detail and search.
- Favorites and follow-list add/remove.
- One successful order and one rollback failure.
- Ownership denial for another member order.
- Leader application approval transaction.
- One group-buy creation and locked-field update test.
- One legal order status transition and one conflict.
- Announcement create/update/delete synchronization.

## 27.2 Full Regression Before Release

- Execute all P0 and P1 cases in this document.
- Execute all Critical End-to-End Scenarios.
- Execute Chrome, Firefox and Mobile Chrome browser matrix.
- Re-run all previously fixed S0／S1 defects.
- Verify Alembic migration on empty and populated test databases.
- Complete UAT and sign-off.

## 27.3 Change-Based Regression

| Changed Area | Required Regression |
|---|---|
| Authentication / JWT | AUTH, API permissions, redirectPath, all protected route smoke tests |
| Group buy / quantity | GB, FL, ORD, DB concurrency, cancellation quantity release |
| Order status | ORD, CAN, notification and announcement recipient calculations |
| Announcement / notification | ANN, NOTI, DB cascade and read-state preservation |
| Product / activity | ACT, PROD, search, favorites, public group buys and historical snapshots |
| Database migration | All DB cases plus one complete E2E order flow |
| UI routing / auth context | Login redirect, protected routes, notification navigation and mobile menu |

---

# 28. Traceability Matrix

| Requirement Area | Primary Source | Test Suites |
|---|---|---|
| Roles and permissions | Business Rules 5、31 | AUTH, PROF, LEAD, ADM, API |
| Registration and authentication | Business Rules 6 | AUTH, API, UI |
| Member profile and contacts | Business Rules 7 | PROF, ORD, API |
| Group leader application and profile | Business Rules 8～9 | LEAD, ADM, E2E-002 |
| Activities | Business Rules 10 | ACT, PUB, ADM, E2E-007 |
| Products and characters | Business Rules 11～12 | PROD, CHAR, PUB, ADM |
| Images | Business Rules 13 | IMG, API-011, UI |
| Public browsing and search | Business Rules 14 | PUB, UI |
| Group buy creation and edit | Business Rules 15～17 | GB, DB, UI |
| Follow list | Business Rules 18 | FL, ORD, E2E-001 |
| Order creation, quantity and priority | Business Rules 19～21 | ORD, DB, E2E-003～004 |
| Cancellation | Business Rules 22 | CAN, ORD, E2E-005 |
| Favorites | Business Rules 23 | PROD-004, API smoke, E2E-008 |
| Announcements and notifications | Business Rules 24～26 | ANN, NOTI, DB, E2E-006 |
| Administrator | Business Rules 27 | ADM, UAT-007 |
| Money and time | Business Rules 28 | ORD-018, API-004～005 |
| Validation and errors | Business Rules 29 | AUTH, API, UI |
| Transactions and concurrency | Business Rules 30 | FL-005, ORD, CAN-005, ANN-008, DB |
| Security and privacy | Business Rules 31 | PROF, API, DB |
| Retention and delete | Business Rules 32 | PROD-004, ANN delete, DB-012 |
| First-version boundaries | Business Rules 33 | ADM-008, UI-012, release checklist |

---

# 29. Test Execution Records

## 29.1 Test Run Summary

| Field | Value |
|---|---|
| Test Run ID |  |
| Date |  |
| Environment | Local / Test / Staging / Production Smoke |
| Frontend Build / Commit |  |
| Backend Build / Commit |  |
| Database Migration Revision |  |
| Browser / Version |  |
| Tester |  |
| Total Cases |  |
| Passed |  |
| Failed |  |
| Blocked |  |
| Not Run |  |
| Open S0 / S1 |  |
| Decision | Pass / Fail / Conditional Pass |

## 29.2 Evidence Rules

- 自動化測試保存測試報告、失敗 stack trace 與必要的資料庫狀態。
- Playwright 失敗保存 screenshot、trace 或 video。
- 手動案例至少記錄實際結果；失敗需附畫面或 API Response。
- 涉及私人聯絡資料的證據需遮蔽或使用假資料。
- 並行案例需記錄兩個 Request 的開始、完成、狀態碼、order_id 與資料庫占用量。

---

# 30. Defect Report Template

| Field | Content |
|---|---|
| Defect ID | BUG-YYYYMMDD-NNN |
| Title | 簡短描述錯誤結果 |
| Severity / Priority | S0～S3 / P0～P3 |
| Environment | URL、Build、Browser、Database revision |
| Related Case | Case ID |
| Preconditions | 帳號、資料與狀態 |
| Reproduction Steps | 逐步操作 |
| Input | Request、表單值或檔案 |
| Actual Result | 實際畫面、Response 與資料庫結果 |
| Expected Result | 依規格應有結果 |
| Evidence | Screenshot、trace、log、SQL query result |
| Frequency | Always / Intermittent / Once |
| Data Impact | 是否造成重複、遺失、外洩或不一致 |
| Workaround | 有／無 |
| Fix Version |  |
| Regression Result |  |

---

# 31. Release Acceptance Checklist

- [ ] 前端 production build 成功。
- [ ] 後端啟動與 health check 正常。
- [ ] Alembic upgrade head 可在乾淨資料庫完成。
- [ ] 所有 P0 測試通過。
- [ ] 所有 P1 測試已執行，沒有未接受的 S0／S1 缺陷。
- [ ] 註冊、登入、Token 8 小時與到期導向通過。
- [ ] 團主申請、核准與 profile completion gate 通過。
- [ ] 活動動態建立、結束與重新開啟通過。
- [ ] 商品下架／上架、角色與圖片管理通過。
- [ ] 開團建立、編輯鎖定、排序與篩選通過。
- [ ] 跟團清單替換 Transaction 與失效保留通過。
- [ ] 訂單原子建立、失敗保留清單與歷史快照通過。
- [ ] 並行下單不超賣，先喊順序與加喊獨立通過。
- [ ] 訂單狀態與拒絕原因不可修改通過。
- [ ] 取消申請允許狀態、pending 唯一、重申與歷史通過。
- [ ] 公告收件人去重、零收件人規則、修改同步與刪除通過。
- [ ] 通知已讀、全部已讀與來源導向通過。
- [ ] 私人聯絡資料、Ownership 與 Admin／Leader 權限通過。
- [ ] Chrome、Firefox 與 Mobile Chrome 核心流程通過。
- [ ] UAT 已完成並簽核。
- [ ] 所有接受的已知缺陷均記錄風險與後續處理。
- [ ] 正式環境設定未使用測試 Secret、測試資料庫或 wildcard CORS。

---

# 32. Final Test Decisions

1. 第七份文件為 WuWaGroup 第一版最後一份正式規劃文件。
2. 測試範圍同時涵蓋前端、API、資料庫、權限、交易、並行、RWD、瀏覽器與 UAT。
3. 自動化工具使用 pytest、FastAPI TestClient／httpx 與 Playwright。
4. 第一版不設定固定程式碼覆蓋率百分比；核心業務規則必須直接測試。
5. 桌面版 Chrome、桌面版 Firefox 與手機版 Chrome 尺寸為必要瀏覽器範圍。
6. 測試使用獨立資料庫，不得直接在正式資料庫執行破壞性案例。
7. P0 為阻擋上線，P1 為核心功能，P2 為一般功能，P3 為顯示與低風險。
8. 所有 P0 必須通過，且不可存在未處理 S0／S1 缺陷。
9. 先喊順序、加喊獨立、數量占用與並行不超賣為必要 P0 驗收項目。
10. 私人聯絡資料與資源擁有權為必要 P0 安全驗收項目。
11. 公告修改同步通知且不重設已讀，公告刪除只刪關聯通知，均為必要 P0 項目。
12. 測試案例結果使用 Pass、Fail、Blocked、Not Run。
13. 每次正式發布前執行完整 P0／P1 回歸、核心 E2E、Browser Matrix 與 UAT。
14. 本文件與 Business Rules v1.0 共同作為第一版上線驗收依據。

---

# End of Document
