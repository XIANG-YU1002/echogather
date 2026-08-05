# Tasks: Admin 權限硬化（admin-permission-hardening）

**Input**: `specs/003-admin-permission-hardening/`（spec.md、plan.md、research.md、contracts/admin-restriction.md、data-model.md、quickstart.md）

**Tests**: spec FR-007 明文要求逐端點測試——測試任務為必要項。

**Organization**: 依 User Story 分階段；US1（會員端點）與 US2（團主後台）共用 Foundational 的 Dependency，故 Phase 2 完成後兩者即可獨立驗證。

## Phase 1: Setup

- [X] T001 確認測試環境可用：`backend/.env` 有 `TEST_DATABASE_URL`，執行 `venv\Scripts\python scripts\build_test_schema.py`（於 `backend/`）重建 `wuwa_test` schema，再跑 `venv\Scripts\python -m pytest tests\test_db_isolation_guard.py` 確認隔離防呆通過

## Phase 2: Foundational（阻擋所有 Story 的前置）

- [X] T002 在 `backend/app/api/deps.py` 新增 `get_current_member_user`：依賴 `get_current_user`，`user.role == UserRole.ADMIN` 時 raise `AppError(403, "ADMIN_MEMBER_ACCESS_FORBIDDEN", "管理員帳號不可使用會員或團主功能。")`，否則回傳 user；加入 `__all__`
- [X] T003 在 `backend/app/api/deps.py` 將 `get_current_group_leader_profile` 的依賴由 `get_current_user` 改為 `get_current_member_user`（`get_current_active_group_leader_profile` 鏈不動），docstring 註明 Admin 前置拒絕（FR-006）
- [X] T004 在 `backend/tests/conftest.py` 新增 admin 測試 fixture：沿用既有測試使用者建立方式建立 `role=UserRole.ADMIN` 的使用者與其 Bearer token（僅新增 fixture，不改既有 fixture 與 D-02 架構）

**Checkpoint**: Foundational 完成——US1／US2 可開始。

## Phase 3: User Story 1 - 後端拒絕 Admin 使用會員功能（P1）

**Goal**: 收藏 3、購物車 5、訂單 5、團主申請 2 共 15 端點，Admin 一律 403 `ADMIN_MEMBER_ACCESS_FORBIDDEN`，零資料異動；非 Admin 行為不變。

**Independent Test**: `pytest tests/test_admin_permission_hardening.py -k member` 全過，且既有 favorites／follow_list／orders／applications 測試全過。

- [X] T005 [P] [US1] `backend/app/api/v1/favorites.py`：3 個端點的 `Depends(get_current_user)` 替換為 `Depends(get_current_member_user)`（依 contracts #1–3）
- [X] T006 [P] [US1] `backend/app/api/v1/follow_list.py`：5 個端點替換（contracts #4–8）
- [X] T007 [P] [US1] `backend/app/api/v1/orders.py`：5 個端點替換（contracts #9–13）
- [X] T008 [P] [US1] `backend/app/api/v1/group_leader_applications.py`：2 個端點替換（contracts #14–15）
- [X] T009 [US1] 建立 `backend/tests/test_admin_permission_hardening.py`：定義參數化端點清單（與 contracts 完全一致的 49 筆 method+path，含各端點所需的路徑參數替身），先實作會員 15 端點的 Admin 拒絕測試——斷言 403、`error.code`、回應格式 `{"error":{code,message,details}}`；寫入類端點（POST/PATCH/DELETE）加 before/after 筆數快照斷言零異動（FR-004）
- [X] T010 [US1] 同檔新增非 Admin 回歸煙霧案例：一般會員收藏、購物車、下單、團主申請各 1 例（沿用既有測試工具，行為與修改前一致）

**Checkpoint**: US1 可獨立驗收（SC-001 的會員部分）。

## Phase 4: User Story 2 - 後端拒絕 Admin 使用團主後台（P1）

**Goal**: 團主後台 34 端點（profile 4、group-buys 10、orders 14、announcements 6）Admin 一律先收到 403 `ADMIN_MEMBER_ACCESS_FORBIDDEN`（不得先回 404／PROFILE_INCOMPLETE）。

**Independent Test**: `pytest tests/test_admin_permission_hardening.py -k leader` 全過，且既有 group_leader 相關測試全過。

- [X] T011 [US2] 確認 T003 依賴鏈後 4 個團主 router 檔（`group_leader_profile.py`、`group_leader_group_buys.py`、`group_leader_orders.py`、`group_leader_announcements.py`）無需修改即生效；以實際請求驗證任一端點 Admin 得 403（若有端點未經 `get_current_group_leader_profile` 鏈，先更新 contracts 清單與本檔再實作）
- [X] T012 [US2] 在 `backend/tests/test_admin_permission_hardening.py` 補團主後台 34 端點的 Admin 拒絕測試（參數化，斷言同 T009），並加清單數量斷言（總數 == 49，SC-006 防漏測）
- [X] T013 [US2] 同檔新增團主雙情境測試：(a) Admin 無團主資料 → 403 `ADMIN_MEMBER_ACCESS_FORBIDDEN`；(b) 測試中直接為 Admin 建立 `group_leader_profile` 後再呼叫 → 仍為同一 403（FR-006、Edge Case）
- [X] T014 [US2] 同檔新增非 Admin 團主回歸煙霧案例：有效團主呼叫 dashboard 或 group-buys 列表 1 例，行為不變
- [X] T015 [US2] 執行完整後端測試 `venv\Scripts\python -m pytest`（於 `backend/`），既有 258 案例＋新增案例全數通過（FR-005、FR-009 條件 3）；如有失敗，修正本 feature 引入的問題後重跑

**Checkpoint**: 後端全部完成（SC-001、SC-002、SC-006）。

## Phase 5: User Story 3 - 前端入口與 Route Guard（P2）

**Goal**: Admin 看不到五類功能入口；直接輸入受保護網址一律導向 `/admin`，不閃現內容。

**Independent Test**: 依 quickstart.md「前端驗證」逐項於瀏覽器確認（由使用者實測）。

- [X] T016 [P] [US3] `frontend/src/layouts/MemberLayout.jsx`：在 `initializing` 檢查之後、未登入檢查之後新增——`user?.permissions?.is_admin` 為 true 時 `return <Navigate to="/admin" replace />`
- [X] T017 [P] [US3] `frontend/src/layouts/GroupLeaderLayout.jsx`：在 `!user.group_leader` 檢查**之前**新增同樣的 Admin 判斷導向 `/admin`
- [X] T018 [US3] 逐頁確認 Admin 登入時 FR-008 清單的 CTA 均不顯示：收藏（ProductDetailPage 等）、加入購物車／跟團／下單（GroupBuyDetailPage 已確認隱藏）、我的訂單、團主申請、團主後台入口（Header、AvatarMenu 已確認隱藏）；發現漏隱藏才修改該顯示條件，並記錄於本檔
- [X] T019 [US3] 跑 `npm run lint`（於 `frontend/`，先把 `C:\Program Files\nodejs` 加進 `$env:PATH`）；請使用者依 quickstart.md 於瀏覽器以 Admin、一般會員、團主三種帳號實測（FR-009 條件 4；未經使用者確認不得視為通過）

**Checkpoint**: SC-003 達成（以使用者實測為準）。

## Phase 6: User Story 4 - 文件同步（P3）

**Goal**: FR-009 五條件全部成立後，D-06 標記為已解決。

**Independent Test**: 檢視兩份文件 D-06 條目與實測結果一致。

- [X] T020 [US4] 確認 FR-009 五條件全部成立（清單完成、49 拒絕測試過、完整 pytest 過、前端驗收過、回歸無變化）；任一不成立則停在此、D-06 維持「待同步」
- [X] T021 [P] [US4] 更新 `docs/CURRENT_DECISIONS.md` §16.6：D-06 改「已解決（已實作）」，附 Feature 路徑 `specs/003-admin-permission-hardening/`、共用 Dependency（`get_current_member_user`）、測試檔 `backend/tests/test_admin_permission_hardening.py` 與驗證結果；更新文件版本號與日期
- [X] T022 [P] [US4] 更新 `docs/EchoGather_Product_Specification_v1.0.md` §21 D-06：同上標記與附註，保留編號；更新文件版本號與日期
- [X] T023 [US4] 將 research.md〈盤點附帶發現〉第 1、3 項（notifications API 未排除 Admin、users/me 定位）以待裁決差異形式記入文件（新差異編號由專案負責人裁決；本任務僅登錄事實，不實作）

## Phase 7: Polish

- [X] T024 對照 plan.md「允許修改的檔案」核對 `git status` 實際變更清單，確認無夾帶（Constitution 原則 VI）；整理變更摘要供使用者確認後續 commit／PR（未經使用者同意不 commit）

## Dependencies

- Phase 2（T002–T004）阻擋全部 Story
- US1（T005–T010）與 US2（T011–T014）在 Phase 2 後可並行；T015 需兩者完成
- US3（T016–T019）不依賴後端，Phase 2 後即可做；驗收依賴使用者實測
- US4（T020–T023）依賴 US1＋US2＋US3 全部完成
- T024 最後

## Parallel Example

- Phase 3 開頭：T005、T006、T007、T008 四檔互不相依，可同時改
- Phase 5 開頭：T016、T017 可同時改
- Phase 6：T021、T022 可同時改

## Implementation Strategy

MVP = Phase 1–4（後端強制，D-06 的安全核心）；Phase 5 為體驗同步；Phase 6 僅在全部驗收後執行。每個 Checkpoint 停下來可獨立驗證。
