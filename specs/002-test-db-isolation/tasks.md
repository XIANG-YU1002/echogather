# Tasks: 測試資料庫隔離（Test Database Isolation）

**Input**: Design documents from `specs/002-test-db-isolation/`

**Prerequisites**: [plan.md](./plan.md)、[spec.md](./spec.md)、[research.md](./research.md)、[data-model.md](./data-model.md)、[quickstart.md](./quickstart.md)

**Tests**: 本功能規格明確要求安全測試（FR-008）與完整測試套件驗證（SC-001／SC-003），故包含測試任務。

**Organization**: 依 user story 分組。注意：本功能三個 story 有天然的依賴鏈——
US2（防呆）與 US3（結構建置）是 US1（完全分流）的支撐條件，
故執行順序為 US2 → US3 → US1，與優先級（皆為達成 D-02 所必要）不衝突；
US1 是最後的收尾驗證，完成即代表整個功能可驗收。

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup（環境事實確認與本機設定）

**Purpose**: 確認 research.md 的待驗證項、備妥本機 `.env`

- [X] T001 以 Session pooler 實連查詢 pgcrypto／pg_trgm 所在 schema（R4 驗證：`SELECT e.extname, n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace WHERE e.extname IN ('pgcrypto','pg_trgm')`），並確認 Session pooler 連線可用與 `SET search_path` 生效；將實測結果補記於 specs/002-test-db-isolation/research.md R4（一次性驗證腳本放 scratchpad，不進 repo）
- [X] T002 在 backend/.env 加入 `TEST_DATABASE_URL`（Session pooler 5432 連線字串，格式同既有 `ALEMBIC_DATABASE_URL`）；`TEST_DATABASE_SCHEMA` 使用預設 `wuwa_test` 不另設值

**Checkpoint**: extension schema 已知、測試連線字串就緒

---

## Phase 2: Foundational（阻塞性前置，US 開始前必須完成）

**Purpose**: 設定欄位與 alembic 外部連線支援，三個 story 都依賴

- [X] T003 [P] 在 backend/app/core/config.py 的 `Settings` 新增 `test_database_url: str = ""` 與 `test_database_schema: str = "wuwa_test"`（含註解說明僅供測試消費，應用程式不讀取；對應 R5）
- [X] T004 [P] 在 backend/alembic/env.py 的 `run_migrations_online()` 加入 `config.attributes.get("connection")` 慣用模式：有外部傳入連線時直接使用，否則走既有 `engine_from_config` 路徑（向後相容，對應 R8）

**Checkpoint**: 正式 migration 路徑行為不變（無 attributes 時走原路徑）

---

## Phase 3: US2 - 設定錯誤時的安全防呆（P1）🎯 建議 MVP 起點

**Goal**: 未設定 `TEST_DATABASE_URL` 或指向 `public` 時，任何測試案例執行前即中止，絕不退回主要連線

**Independent Test**: 兩種錯誤情境下啟動 pytest，收集階段即中止、已執行案例數 0、錯誤訊息可辨識原因

- [X] T005 [US2] 新增 backend/tests/_isolation.py：`validate_test_db_settings(url, schema)` 純函式（G1：url 非空；G2：schema 非空且不分大小寫 ≠ public，違反時 raise 帶修正指引的明確訊息）與 `create_test_engine(url, schema)`（psycopg3、NullPool、`connect` 事件 `SET search_path TO <schema>`；對應 R2／R6／R7）
- [X] T006 [US2] 在 backend/tests/conftest.py 加入 pytest session 開始前的 guard：呼叫 G1／G2 純函式檢查，通過後實連執行 G3（`SELECT current_schema()` 相符）與 G4（測試 schema 存在，否則提示先跑建置腳本）；任一不通過即中止整個測試 session（此步先不動 `db_session`／`client` fixture）
- [X] T007 [P] [US2] 新增 backend/tests/test_db_isolation_guard.py：FR-008 安全測試——對 `validate_test_db_settings` 直接單元測試「url 為空 → 拒絕」「schema=public／Public／空白 → 拒絕」「合法值 → 通過」，並含一條整合測試斷言目前測試連線的 `current_schema()` 不是 public
- [X] T008 [US2] 實測兩種錯誤情境（以環境變數覆寫方式執行 pytest：暫缺 `TEST_DATABASE_URL`、`TEST_DATABASE_SCHEMA=public`），確認收集階段中止、已執行案例數 0、訊息符合 FR-003／FR-004；記錄實際輸出供驗收（SC-002）

**Checkpoint**: 防呆生效——此時尚未切換 fixture，既有測試仍照舊（guard 通過時）

---

## Phase 4: US3 - 測試資料區可重建且結構與主庫一致（P2）

**Goal**: 一支可重複執行的腳本在 `wuwa_test` 內以 alembic 重建與主庫一致的空結構

**Independent Test**: 執行腳本後測試 schema 資料表清單與 public 一致且為空；重複執行成功；public 結構與資料前後不變

- [X] T009 [US3] 新增 backend/scripts/build_test_schema.py：重用 tests/_isolation.py 的 guard（G1／G2）→ 連線後 `DROP SCHEMA IF EXISTS <schema> CASCADE` + `CREATE SCHEMA <schema>` → 依 T001 實測結果設定建置期 search_path（`<schema>, extensions` 或 `<schema>, public`，對應 R4）→ 以 `config.attributes["connection"]` 傳入連線執行 alembic `upgrade("head")` → 回報建立的資料表數與 `current_schema()` 驗證結果
- [X] T010 [US3] 執行建置腳本並驗證：wuwa_test 資料表清單 = public 資料表清單（含 alembic_version，版號為 0014 head）、所有表空資料；立即重跑一次確認可重建（FR-007）；比對 public 的表清單與各表筆數在建置前後完全相同（US3 驗收情境 3）

**Checkpoint**: 測試 schema 就緒且可重建，主庫零變動

---

## Phase 5: US1 - 測試與主要資料完全分流（P1）—— 收尾驗證

**Goal**: pytest 全面改走測試 schema，完整套件通過，主庫資料前後 100% 不變

**Independent Test**: 快照主庫 → 跑完整 pytest → 再快照比對不變；測試寫入只出現在 wuwa_test 且測後回滾

- [X] T011 [US1] 修改 backend/tests/conftest.py：`db_session`／`client` fixture 的 engine 來源從 `app.core.database.engine` 改為 `tests/_isolation.py` 的 test engine（module 層級建立一次）；connection → transaction → savepoint session → rollback 結構與 `_never_send_real_email` 逐字保留（FR-005／FR-006／FR-010）；移除不再使用的 `app.core.database` engine import
- [X] T012 [US1] 完整驗證（SC-001／SC-003）：快照 public 全部資料表筆數 → 執行完整 `pytest` 全數通過 → 再次快照比對筆數與內容 100% 不變；並確認 wuwa_test 各表於套件跑完後為空（rollback 生效，US1 驗收情境 2）
- [X] T013 [US1] 中斷情境驗證（US1 驗收情境 3）：於一個測試執行中途強制中斷 pytest，確認 public 無任何殘留、wuwa_test 殘留（如有）不影響重跑（必要時以建置腳本重建）

**Checkpoint**: D-02 的工程實體全部完成，quickstart.md 驗證情境表全部走過

---

## Phase 6: Polish & 文件同步

**Purpose**: 交付前檢查與規格差異狀態更新

- [X] T014 對照 quickstart.md「驗證情境」表逐項確認皆已實測（含 FR-009：不設 `TEST_DATABASE_URL` 啟動後端網站照常運作），彙整驗收報告給使用者
- [X] T015 經使用者確認驗收後：更新 docs/EchoGather_Product_Specification_v1.0.md 的 D-02（§21 差異表狀態「待同步」→「已實作」、§19.3 REQ-TEST-030 現況與驗收行改為已達成），並依該文件版本規則更新版號與日期；同步在 docs/目前進度.txt 記錄本功能完成（紀錄層）
- [X] T016 依專案慣例：未經使用者同意不 commit；使用者同意後才建立 commit（建議另開 feature branch `002-test-db-isolation`）

---

## Dependencies

```text
T001, T002 (Setup)
   ↓
T003, T004 (Foundational, 可平行)
   ↓
US2: T005 → T006 → T008；T007 與 T006 可平行
   ↓
US3: T009 → T010（T009 依賴 T004、T005、T001 結果）
   ↓
US1: T011 → T012 → T013（T011 依賴 T005；T012 依賴 T010 的 schema 就緒）
   ↓
T014 → T015 → T016 (Polish；T015 需使用者驗收)
```

## Parallel Opportunities

- T003 ∥ T004（不同檔案、互不依賴）
- T007 ∥ T006（guard 單元測試寫作與 conftest 接線互不阻塞）
- 其餘任務因依賴鏈或同檔修改（conftest.py 出現在 T006 與 T011）需序列執行

## Implementation Strategy

- **MVP**：Phase 1–3（US2 防呆）。即使只完成到此，「錯誤設定打到主庫」的最大風險已被擋下。
- **增量交付**：每個 Checkpoint 都是可停下驗證的狀態；US3 完成後測試 schema 可用，US1 完成即整體可驗收。
- 全程遵守：不動 `app/core/database.py`、不動 `alembic/versions/`、不對 `public` 做任何寫入；發現範圍外問題記錄不順手修（憲章原則 I）。
```
