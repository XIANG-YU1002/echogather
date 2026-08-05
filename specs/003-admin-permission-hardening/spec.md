# Feature Specification: Admin 權限硬化（admin-permission-hardening）

**Feature Branch**: `fix/admin-permission-hardening`（spec 目錄：`specs/003-admin-permission-hardening`）

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "Admin 權限硬化（admin-permission-hardening，對應正式規格差異 D-06 / CD §16.6）。正式規格（REQ-ROLE-060；CD §2.2、§3.1、§13.1）要求：Admin 是獨立管理用途帳號，只能使用管理後台，不得使用收藏、購物車、下單、團主申請與團主後台；此限制必須由後端強制，不能只靠前端隱藏。範圍：(1) 盤點收藏、購物車、訂單建立、團主申請、團主後台所有後端 Endpoint；(2) 建立共用的後端權限 Dependency，Admin 呼叫這些 API 一律拒絕；(3) 統一 HTTP 狀態碼與錯誤碼；(4) 補齊每類端點的 Admin 拒絕測試；(5) 前端 Route Guard 與入口顯示同步確認。完成後將 D-06 標記為已解決（同步 CURRENT_DECISIONS.md §16.6 與產品規格 §21）。本 Feature 僅處理 D-06，不涉及活動幣別（D-14）或其他差異項。"

**權威來源**：REQ-ROLE-060（`docs/EchoGather_Product_Specification_v1.0.md`）；CD §2.2、§3.1、§13.1、§16.6（`docs/CURRENT_DECISIONS.md`）。差異登錄：產品規格 §21 D-06。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 後端一律拒絕 Admin 使用會員功能（Priority: P1）

Admin 帳號（無論透過瀏覽器、API 工具或任何用戶端）呼叫收藏、購物車（跟團清單）、訂單（下單／取消申請／拆單申請）、團主申請等會員專屬 API 時，後端一律拒絕，不建立、不修改、不回傳任何會員功能資料。

**Why this priority**: 這是 D-06 的核心——限制必須由後端強制，前端隱藏不算數。任何一個端點漏擋都等於差異未解決。

**Independent Test**: 以 Admin 帳號的登入憑證逐一呼叫盤點清單中的每個會員功能端點，全部收到相同的拒絕回應，且資料庫無任何資料被建立或修改。

**Acceptance Scenarios**:

1. **Given** 已登入的 Admin 帳號，**When** 呼叫任一收藏端點（查詢／加入／移除收藏），**Then** 收到統一的權限拒絕回應，收藏資料無任何變動。
2. **Given** 已登入的 Admin 帳號，**When** 呼叫任一購物車端點（查詢／加入項目／改數量／移除項目／清空），**Then** 收到統一的權限拒絕回應，購物車資料無任何變動。
3. **Given** 已登入的 Admin 帳號，**When** 呼叫任一訂單端點（建立訂單／查詢我的訂單／訂單明細／取消申請／拆單申請），**Then** 收到統一的權限拒絕回應，無訂單或申請被建立。
4. **Given** 已登入的 Admin 帳號，**When** 呼叫團主申請端點（送出申請／查詢我的申請），**Then** 收到統一的權限拒絕回應，無申請被建立。
5. **Given** 已登入的一般會員帳號，**When** 呼叫上述任一端點，**Then** 行為與本次修改前完全相同（不受影響）。

---

### User Story 2 - 後端一律拒絕 Admin 使用團主後台（Priority: P1）

Admin 帳號呼叫團主後台 API（團主資料、團主儀表板、開團管理、團主訂單管理、團主公告）時，後端一律拒絕。Admin 不因管理員身分取得團主功能；同一真人若需要團主功能，必須另外使用一般會員帳號。

**Why this priority**: 與 User Story 1 同屬 D-06 的後端強制要求，缺一即差異未解決。

**Independent Test**: 以 Admin 帳號憑證逐一呼叫盤點清單中的每個團主後台端點，全部收到相同的拒絕回應。

**Acceptance Scenarios**:

1. **Given** 已登入的 Admin 帳號（無團主資料），**When** 呼叫任一團主後台端點，**Then** 收到統一的權限拒絕回應，而非「找不到團主資料」等其他錯誤——拒絕原因必須明確是「Admin 不得使用」。
2. **Given** 已登入且團主資格有效的一般會員，**When** 呼叫團主後台端點，**Then** 行為與本次修改前完全相同（不受影響）。

---

### User Story 3 - 前端不提供 Admin 進入會員／團主功能的入口（Priority: P2）

Admin 登入前台網站時，看不到收藏、購物車、下單、團主申請與團主後台的入口；直接輸入這些頁面的網址時會被導離（Route Guard），不會停留在功能頁面上操作後才收到錯誤。

**Why this priority**: 後端強制（P1）已保證安全；前端同步是使用體驗與一致性，屬確認與補漏性質。

**Independent Test**: 以 Admin 帳號登入前台，逐頁確認入口不顯示、直接輸入網址被導離。

**Acceptance Scenarios**:

1. **Given** 已登入的 Admin 帳號，**When** 瀏覽前台任一頁面，**Then** 不顯示收藏、購物車、下單、團主申請與團主後台的按鈕或連結。
2. **Given** 已登入的 Admin 帳號，**When** 直接輸入會員或團主專屬頁面的網址，**Then** 前端 MUST 導向 `/admin`，不得停留或短暫顯示受限制頁面的內容。（未登入使用者仍沿用既有流程導向登入頁，不受本規則影響。）
3. **Given** 一般會員或訪客，**When** 瀏覽前台，**Then** 入口顯示與導向行為與本次修改前完全相同。

---

### User Story 4 - 差異登錄同步為已解決（Priority: P3）

實作完成並通過測試後，D-06 在 `docs/CURRENT_DECISIONS.md` §16.6 與產品規格 §21 差異表標示為已解決（已實作），編號保留、不重排、不重用。

**Why this priority**: 文件同步是收尾條件，依 Constitution 原則 V／VII 必須與實作狀態一致。

**Independent Test**: 檢視兩份文件的 D-06 條目狀態與描述是否與實測結果一致。

**Acceptance Scenarios**:

1. **Given** 全部 Admin 拒絕測試通過，**When** 更新兩份文件，**Then** D-06 狀態為已解決（已實作），並附實作與驗證位置（本 spec 目錄）。

---

### Edge Cases

- Admin 帳號同時擁有歷史遺留的收藏／購物車／訂單資料時：本次僅阻擋 API 使用，不清理、不遷移既有資料（如有發現，記錄為待辦，不順手處理）。
- Admin 帳號若（因歷史操作）已存在團主資料：仍一律拒絕進入團主後台——判斷依據是帳號角色，不是有無團主資料。
- 未登入或 Token 無效的請求：維持既有的未登入錯誤行為，不因本次修改而改變（Admin 限制只針對「已通過身分驗證且角色為 Admin」的請求）。
- 公開端點（商品／活動／開團瀏覽、搜尋）可選擇性辨識使用者身分：Admin 瀏覽公開內容不在禁止範圍，維持現狀。
- 功能範圍界線：本 Feature 僅處理 D-06 明確列出的五類功能——收藏、購物車、訂單與訂單申請、團主申請、團主後台。Admin 的登入、登出、取得目前登入帳號資料等認證基礎能力維持現狀。會員個人中心、私人聯絡資料與會員通知中心不在本次實作範圍；本 Feature 不得自行將其擴張為 Admin 正式可用功能。若盤點發現其現況與「Admin 只使用管理後台」的正式規格衝突，必須記錄為新的規格與實作差異，交由後續 Feature 裁決，不得在本次順手修改。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 盤點並列出收藏、購物車（跟團清單）、訂單（下單與訂單申請）、團主申請、團主後台五類的全部後端端點，形成明確的端點清單，作為實作與測試的依據（盤點結果記錄於本 feature 的 plan／tasks 文件）。
  Plan 階段的端點盤點 MUST 以「HTTP Method＋完整 Path＋目前權限 Dependency＋預定替換 Dependency」逐項列出，不得只列模組名稱。清單至少分為：
  1. 收藏端點
  2. 購物車端點
  3. 會員訂單、取消申請與拆單申請端點
  4. 團主申請端點
  5. 團主資料、Dashboard、開團、團主訂單與團主公告端點

  每一端點 MUST 對應至少一個 Admin 拒絕測試。若盤點中發現漏列端點，必須先更新清單與 Tasks，再進行實作。
- **FR-002**: 後端 MUST 以單一共用的權限檢查機制（而非在各端點各自撰寫判斷）阻擋 Admin 帳號使用 FR-001 清單中的所有端點。
  共用權限機制 MUST 採分層 Dependency，維持下列語意：

  ```text
  get_current_user
  └── get_current_member_user
      └── get_current_group_leader
  ```

  - `get_current_user`：允許所有已登入帳號，包括 Admin，供認證基礎能力與管理後台使用。
  - `get_current_member_user`：先驗證登入，再拒絕 `role = admin`，供收藏、購物車、會員訂單與團主申請使用。
  - `get_current_group_leader`：必須先通過 `get_current_member_user`，再檢查團主資料與團主資格。

  Admin 呼叫團主後台時，MUST 先得到 Admin 角色拒絕，不得先回傳「找不到團主資料」或「尚未成為團主」。
- **FR-003**: Admin 帳號呼叫 FR-001 清單中任一端點時，系統 MUST 拒絕並回傳統一的 HTTP 狀態碼與統一的錯誤碼；所有五類端點的拒絕回應格式 MUST 完全一致。
  Plan MUST 依目前專案既有錯誤 Response 格式選定：統一 HTTP Status `403`、單一錯誤碼、單一預設錯誤訊息；收藏、購物車、訂單、團主申請與團主後台不得各自使用不同錯誤碼。建議語意：

  ```text
  ADMIN_MEMBER_ACCESS_FORBIDDEN
  管理員帳號不可使用會員或團主功能。
  ```

  實際名稱可依專案既有錯誤碼命名規則調整，但 Plan 定案後不得在實作階段自行更換。
- **FR-004**: 拒絕發生時，系統 MUST NOT 建立、修改或刪除任何資料。
- **FR-005**: 一般會員、團主與訪客使用 FR-001 清單中端點的行為 MUST 與本次修改前完全相同（回歸不變）。
- **FR-006**: 團主後台端點對 Admin 的拒絕 MUST 以「帳號角色為 Admin」為判斷依據，優先於「是否擁有團主資料」的檢查，使拒絕原因對呼叫端明確可辨。
- **FR-007**: 後端測試 MUST 滿足下列全部要求：
  - 每個受限制 Endpoint 都必須有 Admin 拒絕案例，不得只測每個模組一個代表端點。
  - 測試必須確認：HTTP Status 一致、Error Code 一致、Response 格式一致、Service／Repository 不產生資料異動。
  - 團主後台測試須包含「Admin 沒有團主資料」與「Admin 歷史上意外具有團主資料」兩種情境，兩者都必須得到相同的 Admin 權限拒絕。
  - 非 Admin 回歸案例至少每一類一例；既有相關測試必須全部通過。
  - 測試必須使用已完成的獨立測試資料庫機制（D-02），不得連線主要開發或正式資料庫。
- **FR-008**: 前端 MUST 確認並補齊 Admin 的入口與 Route 限制。Admin 可瀏覽公開活動、商品、角色、開團、團主公開頁與搜尋內容，但下列會員／團主操作按鈕、連結、選單與入口 MUST NOT 顯示：
  - 收藏與取消收藏
  - 購物車入口、加入購物車、修改購物車
  - 跟團、立即下單或前往訂單確認
  - 我的訂單與訂單申請
  - 申請成為團主
  - 團主後台入口
  - 團主資料、開團管理、團主訂單與團主公告入口

  Admin 直接進入對應受保護 Route 時，Route Guard MUST 導向 `/admin`。前端隱藏或導向僅用於使用體驗，後端 FR-002～FR-006 仍為最終安全防線。
- **FR-009**: 僅在下列條件全部成立後，才可將 D-06 標記為已解決：
  1. FR-001 完整端點清單完成；
  2. 所有清單端點的 Admin 拒絕測試通過；
  3. 所有既有後端測試通過；
  4. 前端入口與 Route Guard 驗收通過；
  5. 一般會員與團主回歸行為無變化。

  完成後同步更新：`docs/CURRENT_DECISIONS.md` §16.6 與 `docs/EchoGather_Product_Specification_v1.0.md` §21 D-06。
  D-06 MUST 保留原編號並標記「已解決（已實作）」，附 Feature 路徑、共用 Dependency、測試檔案與驗證結果。若任一類 Endpoint 尚未覆蓋，D-06 必須維持「待同步」。
- **FR-010**: 本次 MUST NOT 超出 D-06 範圍，具體包括：
  - 不修改活動幣別（D-14）與開團活動修改（D-15）相關的程式與文件。
  - 不修改 D-02 已完成的測試資料庫架構，除非只為新增本 Feature 測試設定。
  - 不處理 Admin 歷史收藏、購物車、訂單或團主資料（不清理、不遷移）。
  - 不順便重構全部認證或權限系統。
  - 不限制 Admin 瀏覽公開內容。
  - 盤點時發現的其他權限問題只記錄，不自動納入本 Feature。

### Key Entities

- **Admin 帳號**: 角色為 admin 的使用者帳號，僅供管理後台使用；本 feature 的被限制主體。
- **會員功能端點**: 收藏、購物車、訂單、團主申請四類需登入的會員 API。
- **團主後台端點**: 團主資料、儀表板、開團管理、團主訂單管理、團主公告等團主專屬 API。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 以 Admin 帳號呼叫盤點清單中的端點，100% 收到統一的拒絕回應（狀態碼與錯誤碼一致），0 筆資料被建立或修改。
- **SC-002**: 全部既有後端測試與新增的 Admin 拒絕測試 100% 通過（新增測試逐端點覆蓋，無抽樣）。
- **SC-003**: Admin 登入前台後，FR-008 所列會員／團主功能入口與操作 CTA 可見數為 0；直接輸入全部對應受保護 Route 時，100% 導向 `/admin`，且不顯示受限制頁面內容。
- **SC-004**: 一般會員與團主的既有操作流程回歸測試 100% 通過，無行為變化。
- **SC-005**: D-06 在兩份權威文件中的狀態為已解決（已實作），且描述與實測結果一致。
- **SC-006**: Plan 所列受限制 Endpoint 數量與實際 Route 裝飾器盤點結果 100% 一致，每個 Endpoint 均有對應的 Admin 403 測試，零漏測。

## Assumptions

- 拒絕回應沿用系統既有的權限錯誤慣例：HTTP 403 搭配單一權限錯誤碼（與現行「非 Admin 呼叫管理後台 API」的拒絕形式對稱）；確切錯誤碼於 plan 階段依既有錯誤碼清單定案，但五類端點 MUST 使用同一個。
- 「購物車」的內部技術名稱為 `follow_list`（CD 已確認之命名決策），本 spec 中「購物車」即指該功能。
- 公開瀏覽（活動、商品、角色、開團、團主公開頁、搜尋）不屬於 D-06 五類，Admin 維持可瀏覽。Admin 的認證基礎能力（登入、登出、取得目前登入帳號資料）維持現狀。會員個人中心、私人聯絡資料與會員通知中心不在本次範圍，且本 Feature 不將其裁決為 Admin 正式可用功能（見 Edge Cases 的功能範圍界線）。
- 既有 Admin 帳號目前沒有（或即使有也不處理）收藏、購物車、訂單等遺留資料；資料清理不在本次範圍。
- 測試沿用 D-02 已完成的獨立測試資料庫機制：測試一律使用 `TEST_DATABASE_URL` 連往與主要開發、正式資料庫分離的獨立 schema（`wuwa_test`）；未設定或誤指向主要資料庫（public schema）時測試必須直接中止；本 Feature 可據此執行完整後端測試，不對主庫寫入。
