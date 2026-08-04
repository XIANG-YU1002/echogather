# Quickstart: 測試資料庫隔離（002-test-db-isolation）

**Spec**: [spec.md](./spec.md) ｜ **Plan**: [plan.md](./plan.md)

本指南描述功能完成後，如何在乾淨環境設定並驗證測試隔離。
（實作完成前，以下指令尚不可用。）

## 前置條件

- `backend/venv` 已建立、`requirements.txt` 已安裝。
- `backend/.env` 已含既有必填值（`DATABASE_URL` 等）。

## 設定（人工步驟只有 2 步，對應 SC-004）

### 步驟 1：在 `backend/.env` 加入測試連線

```dotenv
# 測試專用連線：Session pooler（5432），與 ALEMBIC_DATABASE_URL 同一格式
TEST_DATABASE_URL=postgresql+psycopg://postgres.kjziqgiqiwknxqejancr:<password>@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
# 測試 schema 名稱（可省略，預設 wuwa_test）
# TEST_DATABASE_SCHEMA=wuwa_test
```

> 注意：值本身與主要連線指向同一個 Supabase 專案是**正常的**（軟隔離）；
> 隔離單位是 schema，不是連線字串。guard 擋的是 schema 指向 `public`。

### 步驟 2：建置測試 schema（可重複執行＝重建）

```powershell
cd backend
venv\Scripts\python scripts\build_test_schema.py
```

預期輸出：guard 通過 → 重建 `wuwa_test` schema → `alembic upgrade head`
跑完 0001–0014 → 回報資料表數量與 `current_schema()` 驗證結果。

## 執行測試

```powershell
cd backend
venv\Scripts\python -m pytest
```

預期：全數通過；主要資料庫（`public`）任何資料表內容不變。

## 驗證情境（對應 spec 驗收）

| 情境 | 操作 | 預期結果 | 對應 |
|---|---|---|---|
| 正常執行 | 完成步驟 1–2 後跑 pytest | 全綠；`public` 資料前後不變 | US1、SC-001、SC-003 |
| 未設定測試連線 | 暫時註解掉 `TEST_DATABASE_URL` 後跑 pytest | 收集階段即中止，訊息指出缺少設定且不退回 `DATABASE_URL`；執行案例數 0 | US2、FR-003、SC-002 |
| 指向主要資料區 | 暫時設 `TEST_DATABASE_SCHEMA=public` 後跑 pytest | 收集階段即中止，訊息指出不得指向主要資料區；執行案例數 0 | US2、FR-004、SC-002 |
| 重建 | 再跑一次 `build_test_schema.py` | 成功完成、不留舊資料 | US3、FR-007 |
| 結構演進 | 主庫新增 migration 後重跑建置腳本 | 測試 schema 追上新結構 | Edge Case |
| 安全測試本身 | `pytest tests/test_db_isolation_guard.py` | guard 兩種拒絕情境的測試通過 | FR-008 |
| 正式運作不受影響 | 不設 `TEST_DATABASE_URL` 直接啟動後端網站 | 網站照常運作 | FR-009、SC-005 |

## 疑難排解

- **guard 報 schema 不存在**：先跑步驟 2 的建置腳本。
- **建置腳本報 `gen_random_uuid` 或 `gin_trgm_ops` 找不到**：
  建置期 search_path 已固定為 `<測試 schema>, extensions, public`
  （R4 實測：pgcrypto 在 `extensions`、pg_trgm 在 `public`）；
  若仍失敗，回報錯誤訊息即可，勿手動改 `public`。
- **測試報「資料表不存在」**：測試 schema 結構過期，重跑建置腳本；
  這是刻意設計（絕不回退主庫，見 research.md R3）。
