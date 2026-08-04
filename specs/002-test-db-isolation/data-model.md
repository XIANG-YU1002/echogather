# Data Model: 測試資料庫隔離（002-test-db-isolation）

**Date**: 2026-08-04 ｜ **Spec**: [spec.md](./spec.md) ｜ **Research**: [research.md](./research.md)

本功能不新增、不修改任何業務資料表。「資料模型」在此指
**設定項、資料區（schema）與其狀態規則**。

## 1. 設定項（`backend/.env` → `app.core.config.Settings`）

| 欄位 | 型別／預設 | 用途 | 消費者 | 驗證規則 |
|---|---|---|---|---|
| `database_url` | str（必填，既有） | 主要連線（Transaction pooler 6543）→ `public` | `app.core.database.engine`（既有，不變） | 不變 |
| `alembic_database_url` | str = ""（既有） | 正式 Migration 連線（Session pooler 5432） | `alembic/env.py`（既有路徑，不變） | 不變 |
| `test_database_url` | str = ""（**新增**） | 測試專用連線（Session pooler 5432）→ 測試 schema | 僅 `tests/_isolation.py` 與 `scripts/build_test_schema.py` | 空字串＝未設定 → guard 中止測試（FR-003） |
| `test_database_schema` | str = "wuwa_test"（**新增**） | 測試 schema 名稱 | 同上 | 空白或 `public`（不分大小寫）→ guard 中止（FR-004） |

不變式（invariants）：

- 應用程式正式執行路徑（`app/` 下所有模組）MUST NOT 讀取
  `test_database_url`／`test_database_schema`（FR-009 的結構保證）。
- `database.py` 的 engine 建立參數與 `get_db` 行為 MUST 與現況逐字元相同。

## 2. 資料區（PostgreSQL schema）

| 資料區 | 內容 | 讀寫者 | 生命週期 |
|---|---|---|---|
| `public` | 主要開發資料（18+ 資料表、13 ENUM、alembic_version） | 網站正式運作、正式 Migration | 既有，本功能 MUST NOT 增刪改其結構與資料 |
| `wuwa_test`（設定可改名） | 與 `public` 相同結構的空資料表、同名 ENUM、自己的 alembic_version | 僅 pytest 與建置腳本 | 由建置腳本建立；可隨時 DROP CASCADE 重建；測試資料一律於測試結束回滾 |

狀態轉換（測試 schema）：

```text
不存在 ──build_test_schema.py──▶ 結構最新（空資料）
   ▲                                   │
   │                              測試執行（交易內寫入→回滾，狀態不變）
   │                                   │
   └────── DROP CASCADE ◀── 結構過期（主庫新增 migration 後）
                │
                └─ 同腳本內接著重建 → 結構最新
```

## 3. 連線資源

| 資源 | 位置 | 設定 | 與現況差異 |
|---|---|---|---|
| 主要 engine | `app/core/database.py`（既有） | Transaction pooler、pool_size=10 | 無 |
| test engine | `tests/_isolation.py`（新增） | `test_database_url`、NullPool、`connect` 事件 `SET search_path TO <test_schema>` | 新增；conftest 改用它，不再 import `app.core.database.engine` |
| 建置連線 | `scripts/build_test_schema.py`（新增） | 同 test engine，建置期 search_path 依 R4 附加 extension 解析 schema | 新增 |

## 4. Guard 檢查模型（`tests/_isolation.py`）

輸入：`settings.test_database_url`、`settings.test_database_schema`。
執行時機：pytest session 開始、任何測試案例執行之前（R6）。

| # | 檢查 | 不通過時 | 對應需求 |
|---|---|---|---|
| G1 | `test_database_url` 非空 | 中止：缺 TEST_DATABASE_URL，不退回 DATABASE_URL | FR-003 |
| G2 | `test_database_schema` 非空且 ≠ `public` | 中止：測試不得指向主要資料區 | FR-004 |
| G3 | 實連 `SELECT current_schema()` ＝ 設定值 | 中止：search_path 未生效 | FR-004 |
| G4 | 測試 schema 存在（G3 同連線檢查） | 中止：提示先執行建置腳本 | FR-007（提示路徑） |

G1／G2 為純函式檢查（可被安全測試直接單元測試，FR-008）；
G3／G4 需實際連線。任一不通過 → 已執行測試案例數 = 0（SC-002）。
