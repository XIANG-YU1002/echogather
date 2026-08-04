# Implementation Plan: 測試資料庫隔離（Test Database Isolation）

**Branch**: `002-test-db-isolation` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-test-db-isolation/spec.md`

## Summary

後端 pytest 目前直接使用 `app.core.database.engine`（`DATABASE_URL`，Transaction pooler
6543）連上主要開發資料庫的 `public` schema，僅靠交易回滾規避殘留（正式規格差異項
D-02）。本功能在同一個 Supabase 專案內建立獨立測試 schema（`wuwa_test`），
測試一律改走 `TEST_DATABASE_URL`（Session pooler 5432）搭配連線層
`search_path` 指定，建立獨立 test engine／session；未設定或指向 `public`
時測試於執行任何案例前中止。測試 schema 結構以 `alembic upgrade head`
在該 schema 內重建（含 enum、部分索引等 raw SQL 物件），確保與主庫結構一致。
主要連線（`DATABASE_URL`）的程式路徑完全不變。

## Technical Context

**Language/Version**: Python 3.11+（後端既有環境，venv）

**Primary Dependencies**: FastAPI、SQLAlchemy 2.x（DeclarativeBase、psycopg3 driver）、
Alembic（forward-only migrations 0001–0014）、pydantic-settings、pytest + TestClient

**Storage**: Supabase PostgreSQL（專案 `kjziqgiqiwknxqejancr`）。
主要資料區＝`public` schema；測試資料區＝新建 `wuwa_test` schema（同專案、軟隔離）。
應用程式走 Transaction pooler（6543，`prepare_threshold=None`）；
Alembic 走 Session pooler（5432，`alembic_database_url`）；
**測試走 Session pooler（5432）**——Transaction mode 不保證 session 層設定
（`SET search_path`）跨語句存活，Session mode 才可靠（詳見 research.md R1）。

**Testing**: pytest（`backend/pytest.ini`，testpaths=tests，25 個測試檔）。
既有 fixture 模式：connection + transaction + savepoint session，測後 rollback；
`_never_send_real_email` 自動攔截寄信。兩者行為皆須保留。

**Target Platform**: 本機開發環境（Windows）＋日後 CI 皆適用；
網站正式運作（本機與 Render）完全不受影響。

**Project Type**: Web application（backend + frontend）；本功能僅動 backend 測試基礎建設。

**Performance Goals**: 無新增效能目標；測試套件執行時間不因隔離機制顯著劣化
（結構重建為一次性／按需操作，不在每次測試執行時進行）。

**Constraints**:
- MUST NOT 變更 `DATABASE_URL` 用途、`app.core.database.engine` 行為與任何業務程式碼。
- MUST NOT 對 `public` schema 做任何結構或資料變更（含 Migration）。
- 測試執行期連線的 `search_path` MUST NOT 含 `public`（防止缺表時靜默回退主庫，
  spec Edge Case）。
- 未設 `TEST_DATABASE_URL` → 收集階段即中止；不退回 `DATABASE_URL`（FR-003）。
- 程式碼中無任何 `public.` 硬編碼（已全庫 grep 驗證），models 無 `schema=` 指定，
  migrations 全為未限定 schema 的 SQL——`search_path` 分流可行的前提成立。

**Scale/Scope**: 變更集中於：`backend/app/core/config.py`（新增 2 個設定欄位）、
`backend/alembic/env.py`（支援外部傳入 connection）、`backend/tests/conftest.py`、
`backend/tests/` 新增 guard 測試、`backend/scripts/build_test_schema.py`（新增）、
`backend/.env`（本機新增 2 個值，.gitignore 已排除）。約 6 個檔案。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 判定 | 說明 |
|---|---|---|
| I. Brownfield 專案保護 | PASS | 本功能是 CD §14 明載「待修正的工程問題」的修正案，非重新設計。不重寫既有功能程式碼；`config.py`／`env.py` 僅做向後相容的最小擴充。涉及測試與資料庫操作，已由專案負責人於 2026-08-04 對話明確同意（「開始」）。 |
| II. 需求與文件權威順序 | PASS | 權威來源：CD §14.1–14.2、REQ-TEST-030、D-02。未新增任何自行推測的產品規則。 |
| III. 正式規格完整性 | PASS | spec.md 各 FR 具 MUST 強度與可驗收判定；本功能無 UI／API 面向，對應章節不適用。 |
| IV. 衝突與不確定事項處理 | PASS | 唯一待運行時驗證項（pgcrypto／pg_trgm extension 所在 schema）已於 research.md R4 列明驗證方式與兩種結果的處理路徑，不涉產品裁決。 |
| V. 規格與實作分離 | PASS | D-02 狀態更新（待同步→已實作）列為交付項，於驗收通過後才執行。 |
| VI. 範圍與變更控制 | PASS | 允許修改檔案清單已於 Technical Context 宣告（Scale/Scope）；禁止修改：`app/` 業務程式碼、`frontend/`、`alembic/versions/`（不新增 migration）、`public` schema。 |
| VII. 文件可追溯性 | PASS | FR ↔ REQ-TEST-030 條號對應已建立於 spec.md。 |
| VIII. 誠實報告與品質檢查 | PASS | 完成宣告以實際執行的 pytest 結果為準；R4 待驗證項不預先宣稱結論。 |

**Post-Phase-1 re-check**: PASS——design 產物未引入新的憲章衝突；
無 Complexity Tracking 需要記載的違規。

## Project Structure

### Documentation (this feature)

```text
specs/002-test-db-isolation/
├── spec.md              # 功能規格（已完成）
├── plan.md              # 本檔案
├── research.md          # Phase 0：技術決策與依據
├── data-model.md        # Phase 1：設定項與資料區模型
├── quickstart.md        # Phase 1：環境設定與驗證指南
├── checklists/
│   └── requirements.md  # 規格品質檢查（已完成）
└── tasks.md             # Phase 2（/speckit-tasks 產生，非本命令）
```

（無 `contracts/`：本功能為純內部測試基礎建設，不新增或變更任何對外 API、
CLI 介面或 UI，依 plan 工作流程規則略過。）

### Source Code (repository root)

```text
backend/
├── app/
│   └── core/
│       ├── config.py            # [修改] 新增 test_database_url、test_database_schema
│       └── database.py          # [不動] 主要 engine／SessionLocal 完全不變
├── alembic/
│   ├── env.py                   # [修改] 支援 config.attributes["connection"] 傳入連線
│   └── versions/                # [不動] 不新增 migration
├── scripts/
│   └── build_test_schema.py     # [新增] 測試 schema 重建：guard → drop/create schema
│                                #        → alembic upgrade head（search_path 綁定）
├── tests/
│   ├── conftest.py              # [修改] 改用獨立 test engine；session 開始前 guard
│   ├── _isolation.py            # [新增] guard 驗證邏輯與 test engine 工廠（供 conftest
│   │                            #        與安全測試共用；底線開頭避免被 pytest 收集）
│   └── test_db_isolation_guard.py  # [新增] FR-008 安全測試
└── .env                         # [本機] 新增 TEST_DATABASE_URL、TEST_DATABASE_SCHEMA

docs/
└── EchoGather_Product_Specification_v1.0.md  # [驗收後修改] D-02 狀態更新（§19.3、§21）
```

**Structure Decision**: 沿用既有 backend 單體結構。隔離邏輯全部收在測試層
（`backend/tests/`）與獨立腳本（`backend/scripts/`），應用程式層只擴充設定欄位；
`app/core/database.py` 一行不動，確保 FR-009（正式運作零影響）由結構保證，
而非靠測試覆蓋保證。

## Complexity Tracking

無憲章違規需要記載。
