# Feature Specification: EchoGather 正式產品規格文件重整

**Feature Branch**: `001-product-spec-consolidation`（spec 目錄識別名；現行工作分支為 `docs/product-spec-consolidation`）

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: 「EchoGather 正式產品規格文件重整——documentation-only 工作，非產品功能開發。將七份既有規格文件、docs/CURRENT_DECISIONS.md 與現有程式碼／測試中可驗證的資訊，整理成一份完整、一致、可維護且沒有已知矛盾的正式產品規格文件，預定成果為 docs/EchoGather_Product_Specification_v1.0.md。」（原始描述中的來源文件數量，已依 2026-08-04 澄清裁決統一稱為「八份既有來源文件：一份需求追蹤矩陣與七份正式規格文件」，見 Clarifications。）

> 本 Feature 全程受 `.specify/memory/constitution.md`（v1.0.0）約束，特別是原則 I（Brownfield 專案保護）、II（需求與文件權威順序）、IV（衝突與不確定事項處理）、V（規格與實作分離）、VI（範圍與變更控制）、VIII（誠實報告與品質檢查）。
>
> 本 spec 僅定義文件整理工作的範圍與驗收；最終正式規格文件於 `/speckit-implement` 階段才撰寫。本 spec 階段不建立、不修改 `docs/` 內任何檔案。

## Clarifications

### Session 2026-08-04

- Q: 既有來源文件的數量與統一稱呼為何？ → A: 統一稱為「**八份既有來源文件**：一份需求追蹤矩陣（`docs/00_Requirements_Traceability_Matrix.md`）與七份正式規格文件（`docs/01`～`docs/07`）」。「七份正式規格文件」一詞僅在同時明確說明另有一份需求追蹤矩陣時可使用（專案負責人直接裁決）。
- Q: 最終文件 `docs/EchoGather_Product_Specification_v1.0.md` 的定位與收錄深度為何？ → A: 定位為「**產品規格的單一權威入口**」。專案定位與版本範圍、產品與業務規則、使用者角色與權限、功能流程與邊界條件、UI 主要導覽與畫面狀態規則、Database 與 API 的整體設計、測試範圍與驗收標準、延後功能、已知規格與實作差異、需求追溯方式，必須只靠新文件即可查得；每張資料表的完整欄位級定義、每個 API 的完整 Request／Response 範例、每張畫面的完整 Wireframe 細節、每一條測試案例與操作步驟，不要求全文複製，由新文件摘要重要規則並明確引用既有工程文件；新文件不得大量複製工程文件，避免同一細節出現兩份權威版本；被引用工程文件與 CURRENT_DECISIONS 衝突時，以新文件及 CURRENT_DECISIONS 記載的有效規格為準（專案負責人直接裁決，取代並細化同日稍早「規格層收錄＋引用」裁決）。
- Q: 基準實作收編是否修訂本 Feature 範圍？ → A: **2026-08-04 專案負責人核准範圍修訂**：
  允許 `docs/CURRENT_DECISIONS.md` v1.1→v1.2（僅限基準 Commit `0d5c436` 之一次性
  Brownfield 收編）；八份既有來源文件、程式碼、測試與 Migration 仍禁止修改；
  已實作行為仍不得**自動**升格——本次升格係因專案負責人明確裁決；
  CD v1.2 成為新權威版本；已知差異驗收範圍更新為 D-01～D-15
  （D-01、D-10 為已解決保留編號）；AC-008 同步修訂（見下）；
  未來變更仍採 Spec-first。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 專案負責人以單一權威文件裁決產品規格 (Priority: P1)

專案負責人（唯一產品決策者）在裁決產品行為、審核後續開發與驗收成果時，只需開啟 `docs/EchoGather_Product_Specification_v1.0.md` 這個產品規格的單一權威入口，即可查得目前有效的全部已確認**產品與業務規格**；不需再交叉比對八份既有來源文件（一份需求追蹤矩陣與七份正式規格文件）與 CURRENT_DECISIONS，也不會被既有來源文件中已撤回或已被取代的內容誤導。欄位級、逐端點、逐畫面、逐測試案例等工程細節，則依新文件的明確引用查閱對應既有工程文件（FR-003）。

**Why this priority**: 消除「多份文件互相矛盾、閱讀者無法判定何者有效」是本 Feature 的核心目的；此情境不成立，其餘一切皆無價值。

**Independent Test**: 任選 10 條**產品與業務規則**（例如訂單狀態轉換、購物車替換、公開名稱不可修改、幣別鎖定），僅憑新文件回答「目前有效規格為何」，再與 `docs/CURRENT_DECISIONS.md` 比對，答案必須一致，且回答過程無需翻閱其他文件。欄位級／逐端點工程細節不在本測試範圍；該類查詢改為驗證新文件是否提供可直接定位的明確引用（見 SC-001）。

**Acceptance Scenarios**:

1. **Given** 新文件已完成，**When** 就任一產品主題查詢目前有效規格，**Then** 新文件內有明確答案，且與 `docs/CURRENT_DECISIONS.md` 一致。
2. **Given** 既有來源文件與 CURRENT_DECISIONS 對同一主題記載衝突（例如全站搜尋範圍、管理員會員列表），**When** 查閱新文件該主題，**Then** 只呈現以 CURRENT_DECISIONS 為準的有效規格；被取代內容不以正式需求形式出現，必要時以歷史說明標示。
3. **Given** 新文件已完成，**When** 全文檢查，**Then** 無 placeholder、無互相矛盾條文、無已撤回內容被當作有效需求。

---

### User Story 2 - 開發與測試協作者查閱規格並區分規格與實作 (Priority: P2)

後續開發者、測試者或 AI 協作者在進行功能修改、除錯或驗收時，能從新文件查得每條需求的明確規則與驗收方式，並清楚分辨「已確認規格」與「目前實作狀況」——尤其是已知規格與實作差異，不會把待同步規格誤認為已完成，也不會把程式已實作行為誤認為正式需求。

**Why this priority**: 新文件的日常使用者是執行工作的協作者；規格與實作混淆會直接導致錯誤的開發決策。

**Independent Test**: 任選 3 項待同步差異（例如測試仍連主要資料庫 D-02、Admin 後端限制未完整強制 D-06、活動幣別欄位未實作 D-14），僅憑新文件判斷「規格要求什麼、目前實作到哪、差異狀態為何」，判斷結果與 CURRENT_DECISIONS 第 16 節一致。

**Acceptance Scenarios**:

1. **Given** 一項已確認但實作尚未同步的規格（例如活動層級幣別欄位），**When** 查閱新文件，**Then** 該規格以正式需求呈現，且已知差異章節明確標示目前實作狀況與「待同步」狀態。
2. **Given** 因權限檢查缺漏而意外允許的操作（例如 D-06 所涉端點），**When** 查閱新文件，**Then** 該操作不得升格為正式需求，必須標示為 Bug、安全缺口或待同步差異。
3. **Given** 讀者要驗收某條需求，**When** 查閱該需求，**Then** 可找到對應的驗收條件或可判定的驗收方式。

---

### User Story 3 - 新協作者建立正確的專案全貌 (Priority: P3)

新加入的人類或 AI 協作者以新文件作為唯一入門閱讀材料，即可建立正確的專案理解：平台定位、角色權限、全部功能規則、明確不做與延後的範圍，不需先讀完八份既有來源文件。

**Why this priority**: 降低導入成本是重要但非急迫的收益；在 P1／P2 成立後自然達成大半。

**Independent Test**: 讓未接觸過本專案的協作者只讀新文件後回答範圍題（例如「第一版是否提供退款？」「Admin 帳號可以下單嗎？」），答案與 CURRENT_DECISIONS 一致。

**Acceptance Scenarios**:

1. **Given** 只讀過新文件的協作者，**When** 被問及第一版明確不提供的功能，**Then** 能依「延後功能與非第一版範圍」章節正確回答。
2. **Given** 只讀過新文件的協作者，**When** 被問及某角色可否執行某操作，**Then** 能依「使用者角色與權限」章節正確回答。

---

### Edge Cases

- **發現新的規格與實作差異**（CURRENT_DECISIONS 第 16 節未記載）：屬工程差異者記入新文件的已知差異章節並註明為本次整理新發現；需要產品裁決者列入「待專案負責人確認」交付清單，不得寫成正式需求，也不得自行裁決。
- **既有來源文件之間互相矛盾且 CURRENT_DECISIONS 未涵蓋該主題**：不得自行挑選其一寫成正式需求；列入待確認清單提交專案負責人。
- **既有來源文件記載已被撤回的功能**（管理員會員／團主列表管理等）：依 CURRENT_DECISIONS 第 13.2 節，一律標示為不採用的歷史內容，不需重新詢問、不得寫成有效需求。
- **CURRENT_DECISIONS 標示「已完成」的功能**（如團主儀表板依活動分組）：以「已確認＋已實作」記載；不得自行擴充該功能的規則細節超出來源文件記載。
- **CURRENT_DECISIONS 自身疑似內部矛盾**：不得改寫該文件；列入待確認清單交專案負責人裁決。
- **整理量過大無法一次完成**：依 Constitution 原則 VI 分階段交付，每階段有明確章節範圍（分段方式由 `/speckit-plan` 定義）。

## Requirements *(mandatory)*

### 範圍界定

**範圍內（本 Feature 完成時必須交付）**

1. 建立 `docs/EchoGather_Product_Specification_v1.0.md`（於 implement 階段撰寫；本 spec 階段不建立）。
2. 該文件依 FR-003 的收錄深度，整併指定來源的有效內容（見〈內容來源與權威順序〉）。
3. 涵蓋 21 個必要主題章節（見 FR-002）。
4. 建立需求追溯方式，並完成跨文件一致性檢查。
5. 完整保留「已知規格與實作差異」清單（以 CURRENT_DECISIONS 第 16 節為基準，含整理過程新發現項）。

**範圍外（本 Feature 明確不做）**

1. 任何產品功能的新增、修改、重構或重新設計。
2. 修改 `frontend/`、`backend/`、測試、Alembic Migration。
3. 修改或刪除八份既有來源文件（維持凍結）。`docs/CURRENT_DECISIONS.md` 僅允許
   2026-08-04 核准之 v1.2 收編修訂，其餘修改仍屬範圍外。
4. 修改 `README.md`、`.claude/`、套件或環境設定。
5. 決定八份既有來源文件的長期去留（退役、標示 superseded 等，屬未來另行決定事項）。
6. 執行測試、Migration、資料庫操作、套件安裝、部署。
7. 解決已知規格與實作差異本身（僅記錄現況，不修改程式）。
8. 製作面向終端消費者的行銷或使用說明文件。

### Functional Requirements

**產出物與章節**

- **FR-001**: 最終產出 MUST 為單一 Markdown 檔案 `docs/EchoGather_Product_Specification_v1.0.md`，全文繁體中文；資料表名、欄位名、API 路徑、Enum 值、HTTP 狀態碼等技術名詞 MUST 保留英文原文。
- **FR-002**: 文件 MUST 涵蓋以下 21 個主題章節（章節順序與合併方式可由 Plan 階段調整，但涵蓋面不可缺漏）：
  1. 專案定位、目標與第一版範圍
  2. 使用者角色與權限
  3. 帳號、註冊、登入與個人資料
  4. 活動、商品、角色與收藏
  5. 搜尋與導覽
  6. 購物車
  7. 訂單建立、狀態、取消、合併與拆單
  8. 團主申請與團主資料
  9. 開團建立、編輯、結單與數量規則
  10. 付款方式與金額
  11. 團主儀表板、商品訂購總覽與訂單管理
  12. 公告與通知
  13. 管理員功能
  14. 權限、安全、隱私與資料快照
  15. Database Design
  16. API Design
  17. UI 與畫面狀態
  18. 測試與驗收標準
  19. 已知規格與實作差異
  20. 延後功能與非第一版範圍
  21. 需求追溯方式
- **FR-003**: 最終文件定位為**產品規格的單一權威入口**（專案負責人 2026-08-04 澄清裁決，取代並細化同日稍早「規格層收錄＋引用」裁決）：
  - 下列內容 MUST 只靠新文件即可查得：專案定位與版本範圍、產品與業務規則、使用者角色與權限、功能流程與邊界條件、UI 主要導覽與畫面狀態規則、Database 與 API 的整體設計、測試範圍與驗收標準、延後功能、已知規格與實作差異、需求追溯方式。
  - 下列工程細節不要求全文複製進新文件：每張資料表的完整欄位級定義、每個 API 的完整 Request／Response 範例、每張畫面的完整 Wireframe 細節、每一條測試案例與操作步驟。新文件 MUST 摘要其重要規則，並明確引用既有工程文件的對應章節（`04_Database_Design_v2.1`、`05_API_Design_v2.1`、`03_UI_Wireframe_Specification_v2.1`、`07_Testing_and_Acceptance_Plan_v1.0`）。
  - 新文件 MUST NOT 大量複製工程文件內容，避免同一細節出現兩份權威版本。
  - 被引用的既有工程文件若與 CURRENT_DECISIONS 衝突，MUST 以新文件及 CURRENT_DECISIONS 記載的有效規格為準，並於引用處標示衝突與有效規格（見〈衝突處理規則〉）。
  - 此定位與 CURRENT_DECISIONS 第 1 節適用規則 3（工程實作細節仍以 Database Design、API Design、UI Wireframe 為準）一致。
- **FR-004**: 每條正式需求 MUST 使用明確且可檢查的文字，以 MUST／MUST NOT／SHOULD 標示強度，區分正常流程、例外、權限與邊界條件；MUST NOT 使用「通常、可能、視情況」等模糊措辭（Constitution 原則 III）。

**內容整理規則**

- **FR-005**: 內容整理 MUST 遵循〈內容來源與權威順序〉；`docs/CURRENT_DECISIONS.md` MUST 作為產品與業務決策的最高權威來源。
- **FR-006**: 衝突 MUST 依〈衝突處理規則〉處理；MUST NOT 未經專案負責人確認自行裁決產品需求。
- **FR-007**: 全文 MUST 使用〈狀態詞彙〉定義的五種狀態，MUST NOT 另創未定義的同義狀態詞。
- **FR-008**: MUST NOT 加入任何未經確認的需求；程式碼已實作的行為 MUST NOT 因已實作而自動成為正式需求。
- **FR-009**: 已確認規格與目前實作狀況 MUST 分開呈現；「已知規格與實作差異」章節 MUST 完整收錄 CURRENT_DECISIONS 第 16 節全部差異（16.1–16.15，共 15 項；其中 D-01、D-10 依 2026-08-04 裁決為已解決並保留編號，不可遺漏、不可淡化、不可重用編號），並加入整理過程新發現的工程差異。
- **FR-010**: 維運待辦、部署紀錄、實際測試執行紀錄 MUST NOT 寫入產品需求章節；`docs/目前進度.txt`、`docs/測試結果.md`、`docs/部署指南.md` MUST NOT 作為需求來源。
- **FR-011**: 使用者介面名稱與內部技術名稱 MUST 清楚區分並提供對照，至少包含「購物車」（UI 正式名稱）↔ `follow_list`（內部命名，已確認保留）；對照 MUST 註明其為已確認狀態而非待修缺陷。
- **FR-012**: 已被撤回或取代的功能（例如管理員會員／團主列表管理）MUST 以歷史說明標示為不採用，避免日後再次被誤認為需求（Constitution 原則 VI）。

**追溯與品質**

- **FR-013**: 每條正式需求 SHOULD 可追溯至來源（CURRENT_DECISIONS 章節編號或既有來源文件章節編號）；文件 MUST 含「需求追溯方式」章節說明追溯規則與格式（具體格式由 Plan 階段定義）。
- **FR-014**: 文件 MUST 標示版本（v1.0）與日期；MUST 定義後續變更規則（任何修改須更新版本、日期與受影響章節，符合 Constitution 原則 VI）。
- **FR-015**: 完成前 MUST 執行跨文件一致性檢查（新文件對照 CURRENT_DECISIONS 全部章節），檢查結果 MUST 可回報；發現矛盾 MUST 修正，或依性質列為已知差異／待確認事項。
- **FR-016**: 待確認事項 MUST 與正式需求分開存放（獨立章節或清單），並沿用 CURRENT_DECISIONS 第 17 節規則：未裁決前不得當作已確認規格使用。

**工作方式限制**

- **FR-017**: 為判斷目前實作狀況，MAY 唯讀查看 `backend/`、`frontend/` 程式碼與測試；MUST NOT 修改任何程式碼或測試，MUST NOT 執行測試、Migration 或資料庫操作。
- **FR-018**: 本 Feature 全部階段 MUST NOT 修改〈禁止修改的檔案與操作〉所列項目；實際變更檔案清單 MUST 完全落在允許清單內（Constitution 原則 I、VI）。
- **FR-019**: implement 階段撰寫任一章節前，MUST 已完整閱讀該章節對應的全部來源章節；未完整閱讀的來源 MUST NOT 宣稱已完整整理（Constitution 原則 I、VIII）。

### 內容來源與權威順序

| 優先序 | 來源 | 地位 |
|---|---|---|
| 0 | `.specify/memory/constitution.md` v1.0.0 | 治理原則（規範整理程序與品質，不是產品需求來源） |
| 1 | `docs/CURRENT_DECISIONS.md`（v1.1，2026-08-03） | 目前有效產品與業務決策的**最高權威**；衝突時一律以此為準 |
| 2 | **八份既有來源文件**——一份需求追蹤矩陣：`docs/00_Requirements_Traceability_Matrix.md`；七份正式規格文件：`docs/01_Project_Specification_v2.1.md`、`docs/02_User_Flow_v2.1.md`、`docs/03_UI_Wireframe_Specification_v2.1.md`、`docs/04_Database_Design_v2.1.md`、`docs/05_API_Design_v2.1.md`、`docs/06_Business_Rules_v1.0.md`、`docs/07_Testing_and_Acceptance_Plan_v1.0.md` | 合格內容來源；與優先序 1 衝突時，以優先序 1 為準 |
| 3 | `backend/`、`frontend/` 程式碼與測試（唯讀） | 僅用於確認「目前實作狀況」；MUST NOT 自動成為正式需求 |
| —（排除） | `docs/目前進度.txt`、`docs/測試結果.md`、`docs/部署指南.md` | 紀錄層文件；MUST NOT 作為產品需求來源 |

註 1：`00_Requirements_Traceability_Matrix.md` 自我標示為「內部工作文件，非正式規格」；其記載的衝突決議（2026-07-21 裁決與 2026-07-23 撤回）與 CURRENT_DECISIONS 不一致時，仍以 CURRENT_DECISIONS 為準。

註 2：既有來源文件間原有的優先順序（Business Rules → API Design → DB Design → Project Spec → User Flow → UI Wireframe → Testing Plan，見 00 矩陣）僅在 CURRENT_DECISIONS 未涵蓋該主題、且各文件記載一致性需要排序時作為參考；真正衝突仍依〈衝突處理規則〉第 2 條提交裁決。

### 衝突處理規則

1. **既有來源文件 vs CURRENT_DECISIONS**：以 CURRENT_DECISIONS 為準。被取代內容 MUST NOT 進入正式需求；有誤用風險者以歷史說明標示（FR-012）。
2. **既有來源文件之間（CURRENT_DECISIONS 未涵蓋）**：MUST NOT 自行裁決；列入待確認清單提交專案負責人。
3. **文件 vs 程式碼／測試**：屬 CURRENT_DECISIONS 第 16 節既有差異者照實收錄；新發現的工程差異記入已知差異章節並標示為新發現；涉及產品裁決者列入待確認清單。
4. **無法判定者**：MUST 明確標示無法判定與原因，MUST NOT 以推測填補（Constitution 原則 VIII）。
5. **CURRENT_DECISIONS 自身疑似內部矛盾**：MUST NOT 改寫該文件；列入待確認清單交專案負責人裁決。

### 狀態詞彙

採用 Constitution〈狀態詞彙定義〉的五個詞彙，新文件全文 MUST 一致使用：

| 狀態 | 定義 | 可否作為實作依據 |
|---|---|---|
| 已確認 | 已由專案負責人裁決的產品或業務規則 | 可 |
| 已實作 | 程式碼與測試已達成該已確認規格 | 可 |
| 待同步 | 規格已確認，但程式尚未跟上（已知規格與實作差異） | 規格可；現況描述 MUST 註明尚未實作 |
| 延後 | 已確認不屬於第一版範圍 | 不可 |
| 待確認 | 尚未取得明確裁決 | 不可 |

### 產出驗收條件

最終文件交付時 MUST 全數通過下列檢查：

- **AC-001**: FR-002 的 21 個主題章節全部齊備。
- **AC-002**: 全文搜尋無 placeholder（方括號佔位符、TODO、「待補」等）。
- **AC-003**: 與 CURRENT_DECISIONS 全部章節逐節比對無矛盾，比對紀錄可回報。
- **AC-004**: 已知差異 D-01～D-15 全數收錄且狀態標示正確（含 D-01、D-10
  已解決保留編號）。
- **AC-005**: 抽查 10 條正式需求，來源追溯 100% 成立。
- **AC-006**: 抽查歷史衝突主題（全站搜尋範圍、管理員會員／團主列表、首頁活動分類篩選、付款方式），新文件呈現與 CURRENT_DECISIONS 一致。
- **AC-007**: 狀態詞彙使用一致，無未定義的狀態詞。
- **AC-008**: 八份既有來源文件零修改；`docs/CURRENT_DECISIONS.md` 僅允許
  2026-08-04 核准之 v1.2 收編修訂（以 git 驗證）。
- **AC-009**: `frontend/`、`backend/`、測試、Migration 零變更（以 git 驗證）。
- **AC-010**: UI 名稱與內部技術名稱對照存在且正確（至少含「購物車」↔ `follow_list`）。

### 禁止修改的檔案與操作

**禁止修改（本 Feature 全部階段）**

- `docs/CURRENT_DECISIONS.md`（**例外**：2026-08-04 專案負責人核准之 v1.2
  一次性收編修訂；其餘修改仍禁止）
- 八份既有來源文件：`docs/00_Requirements_Traceability_Matrix.md`（需求追蹤矩陣）與 `docs/01`～`docs/07`（七份正式規格文件）
- `docs/目前進度.txt`、`docs/測試結果.md`、`docs/部署指南.md`
- `frontend/`、`backend/`（含測試、Alembic Migration）
- `README.md`、`.claude/`
- 套件與環境設定（`requirements.txt`、`package.json`、`.env` 等）
- `.specify/memory/constitution.md`（如需修訂，另依 Constitution 修訂程序辦理，不在本 Feature 內）

**允許建立或修改**

- `specs/001-product-spec-consolidation/` 下的本 Feature 文件（spec、plan、tasks、checklists 等）
- `.specify/feature.json` 等 Spec Kit 追蹤本 Feature 所必要的狀態檔案
- implement 階段：新增 `docs/EchoGather_Product_Specification_v1.0.md`（全新檔案；不覆寫任何既有檔案）

**禁止執行**

- 程式功能實作、重構
- 測試執行
- Alembic Migration、任何資料庫操作
- 套件安裝
- 部署

### Key Entities

- **正式產品規格文件（產出物）**：`docs/EchoGather_Product_Specification_v1.0.md`；具版本、日期、21 個主題章節、追溯規則與變更規則。
- **來源文件集**：〈內容來源與權威順序〉所列全部來源，含八份既有來源文件（一份需求追蹤矩陣與七份正式規格文件）；每項有明確地位（權威／合格來源／唯讀現況參考／排除）。
- **正式需求條目**：新文件中的單條規格；具強度用詞、狀態標記、來源追溯、驗收方式。
- **已知規格與實作差異項**：規格要求、目前實作狀況、狀態三元組；基準為 D-01～D-15（CURRENT_DECISIONS §16.1～16.15，共 15 項；其中 D-01、D-10 已解決但保留編號），可增加新發現項。
- **待確認事項**：整理過程發現、需專案負責人裁決的問題；與正式需求分開存放，未裁決前不得使用。
- **名稱對照**：使用者介面名稱 ↔ 內部技術名稱的對照關係（例：購物車 ↔ `follow_list`）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 單一權威入口可答性——抽查 10 個產品與業務規則問題，10/10 可僅憑新文件得到答案且與 CURRENT_DECISIONS 一致，0 題需要翻閱其他文件；另抽查 5 個欄位級／逐端點工程細節問題，5/5 可由新文件的明確引用直接定位到既有工程文件的對應章節。
- **SC-002**: 規格與實作零混淆——全部 15 項已知差異（D-01～D-15，含已解決保留編號者）在新文件中的「規格／現況／狀態」三元組與 CURRENT_DECISIONS 第 16 節 100% 相符。
- **SC-003**: 已撤回功能零誤用——已撤回功能在新文件中以有效需求形式出現的次數為 0。
- **SC-004**: 品質門檻全過——AC-001～AC-010 通過率 100%。
- **SC-005**: 範圍零逾越——git 驗證禁止清單檔案異動數為 0。
- **SC-006**: 新協作者理解測試——僅憑新文件回答 10 題角色權限／版本範圍題，正確率 100%。

## Assumptions

- `docs/CURRENT_DECISIONS.md` **v1.2（2026-08-04）**為最新權威版本（含核准之基準收編修訂）；若期間再更新，以更新後版本為準，並重新檢查受影響章節。
- CURRENT_DECISIONS 第 17 節目前為空（無待專案負責人確認的產品規則），故整理起點沒有懸而未決的產品裁決；整理過程新出現者依〈衝突處理規則〉辦理。
- 八份既有來源文件維持凍結，不會被其他工作同時修改；CURRENT_DECISIONS 僅允許已核准之 v1.1→v1.2 修訂。
- 新文件版號自 v1.0 起算，與既有來源文件版號序列（v2.1／v1.0）無關。
- 最終文件的撰寫在 `/speckit-plan` 與 `/speckit-tasks` 之後的 `/speckit-implement` 階段進行；本 spec 階段不產出最終文件。
- 「一份文件」指單一 Markdown 檔案。若整理後篇幅使單檔明顯難以維護，是否拆為主文件＋附錄屬產品負責人裁決事項，不得自行拆分。
