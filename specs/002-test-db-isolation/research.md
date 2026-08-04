# Research: 測試資料庫隔離（002-test-db-isolation）

**Date**: 2026-08-04 ｜ **Spec**: [spec.md](./spec.md) ｜ **Plan**: [plan.md](./plan.md)

本檔記錄 Phase 0 的技術決策。所有結論皆以實際讀取專案程式碼為依據
（`app/core/config.py`、`app/core/database.py`、`alembic/env.py`、
`alembic/versions/0001`、`tests/conftest.py`，以及全庫 grep）。

---

## R1. 測試連線走哪個 pooler

**Decision**: 測試（與測試 schema 結構建置）一律走 **Session pooler（5432）**；
`TEST_DATABASE_URL` 的值即為 Session pooler 連線字串。

**Rationale**:
- 隔離機制依賴連線層的 `SET search_path`（session 狀態）。Transaction pooler
  （6543）在交易之間可能換到不同後端連線，session 狀態不保證存活——這正是
  `database.py` 需要 `prepare_threshold=None` 的同一類原因。
- Session pooler 專案上限 15 連線（`config.py` 註解實測記載），對單機序列執行的
  pytest 綽綽有餘（conftest 一次只開 1 條 connection）。
- 專案已有先例：Alembic DDL 因穩定性考量走 Session pooler（`env.py` 註解），
  測試 schema 建置本質也是 DDL，理由相同。

**Alternatives considered**:
- *Transaction pooler + 每語句 SET*：不可靠且侵入查詢流程，否決。
- *直連（direct connection, 5432 db host）*：同樣可行，但本機環境已驗證可用
  Session pooler，且 `.env` 取得容易，維持一種連線字串即可。

---

## R2. search_path 的設定機制

**Decision**: 在 test engine 上掛 SQLAlchemy `connect` 事件監聽器，
每建立一條 DBAPI 連線即執行 `SET search_path TO <test_schema>`；
guard 於測試 session 開始時以 `SELECT current_schema()` 實連驗證生效。

**Rationale**:
- 不依賴 pooler 是否轉送 startup packet 的 `options` 參數（Supavisor 對
  `options=-csearch_path=...` 的支援不需納入賭注）；事件監聽器在任何連線
  方式下行為一致。
- `current_schema()` 實連驗證讓 FR-004 的「不得指向主要資料區」是
  **執行期事實**而非僅設定值檢查。

**Alternatives considered**:
- *URL `options` 參數*：對 pooler 轉送行為有假設，且把關鍵設定藏在連線字串裡
  不利 guard 檢查，否決。
- *`schema_translate_map`*：只作用於 SQLAlchemy 編譯期的 Table 物件，
  管不到 raw SQL 與 alembic migration 的未限定 SQL，否決。

---

## R3. 測試執行期 search_path 不含 public

**Decision**: 測試執行期連線的 `search_path` 設為 `<test_schema>` 單一值
（不含 `public`）。

**Rationale**: spec Edge Case 明定：測試 schema 缺表時，受影響測試應以
「資料表不存在」失敗，**MUST NOT 靜默回退到主庫取得資料表**。
`search_path` 若含 `public`，缺表時 PostgreSQL 會自動找到 `public` 下的同名表，
直接違反此規則且難以察覺。表的 DEFAULT 運算式（如 `gen_random_uuid()`）
在 CREATE TABLE 時即以完整限定名固化在表定義中，執行期不需要 extension schema
出現在 search_path。

**Alternatives considered**: `'<test_schema>, public'`——查詢永遠先命中測試
schema、看似無害，但缺表回退是靜默的隔離破口，否決。

---

## R4. 結構建置方式與 extension 解析（含待運行時驗證項）

**Decision**: 測試 schema 結構以 **`alembic upgrade head`** 建置（非
`Base.metadata.create_all`），由 `backend/scripts/build_test_schema.py` 執行：

1. guard 檢查（同 conftest 邏輯）；
2. `DROP SCHEMA IF EXISTS <test_schema> CASCADE` → `CREATE SCHEMA <test_schema>`
   （達成 FR-007「可重複執行／重建不留舊資料」）；
3. 以 search_path 綁定的連線執行 alembic `upgrade head`，
   `version_table` 建於測試 schema 內（隨 search_path 自然落位）。

**Rationale**:
- Migrations 含大量 raw SQL 物件：13 個 ENUM 型別、部分索引（partial index）、
  CHECK 約束、`pg_trgm` GIN 索引等。`create_all` 只能重現 `Base.metadata`
  描述得到的部分，無法保證與主庫結構一致（spec User Story 3）。
- ENUM 型別是 schema-scoped，migration 以未限定 SQL 建立 → 隨 search_path
  落入測試 schema，與 `public` 下的同名 ENUM 互不干擾。
- `CREATE EXTENSION IF NOT EXISTS`（pgcrypto、pg_trgm）是資料庫層級操作，
  已安裝時為 no-op，不影響 `public`。
- 主庫結構日後演進時，重跑同一支腳本即追上（spec Edge Case），
  且測試結構永遠與 migration 系譜（0001–0014）對齊，不會出現第二套結構定義。

**待運行時驗證項（實作時第一步確認，不影響設計方向）**：
pgcrypto／pg_trgm 的函式所在 schema（Supabase 慣例為 `extensions`，
但 0001 的 `CREATE EXTENSION` 若當時實際執行過，也可能落在 `public`）。
建置腳本執行 migration 時的 search_path 需能解析 `gen_random_uuid()` 與
`gin_trgm_ops`：
- 若在 `extensions`（預期）：建置期 search_path 設 `'<test_schema>, extensions'`。
- 若在 `public`：建置期 search_path 設 `'<test_schema>, public'`——
  **僅限建置腳本執行 migration 的這條連線**；全新 schema 從 0001 依序建表，
  未限定的表引用永遠先命中測試 schema，`public` 僅供函式／operator class 解析。
  測試執行期連線仍依 R3 不含 `public`。
驗證方式：`SELECT e.extname, n.nspname FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace WHERE e.extname IN ('pgcrypto','pg_trgm')`。

**實測結果（2026-08-04，T001）**：伺服器 PostgreSQL 17.6；`pgcrypto` 位於
`extensions`、**`pg_trgm` 位於 `public`**；`gen_random_uuid()` 在 PG13+ 為
pg_catalog 內建函式（主庫 `app_user.id` 的 DEFAULT 即為未限定引用），
不依賴 extension 所在 schema。另實測 Session pooler 上 `SET search_path`
跨語句（獨立 round-trip）存活，R1／R2 前提成立。
→ 建置期 search_path 採 `'<test_schema>, extensions, public'`
（`public` 供 `gin_trgm_ops` 解析；全新 schema 從 0001 依序建表，
未限定表引用永遠先命中測試 schema）。測試執行期仍依 R3 僅 `<test_schema>`。

**Alternatives considered**:
- *`Base.metadata.create_all`*：結構保真度不足（見上），只在 alembic 路線
  完全不可行時作為退路，目前無此跡象，否決。
- *複製 public 結構（pg_dump --schema-only 重放）*：引入第二套結構來源與
  額外工具依賴，且 dump 內容帶 `public.` 限定名需改寫，否決。

---

## R5. 設定項設計

**Decision**: `Settings` 新增兩個欄位（pydantic-settings 自動從 `backend/.env` 讀取）：

- `test_database_url: str = ""`——空字串＝未設定。應用程式任何執行路徑都不讀它
  （唯一消費者是 conftest 與建置腳本），預設空字串保證 FR-009。
- `test_database_schema: str = "wuwa_test"`——測試 schema 名稱。
  guard 拒絕 `public`（不分大小寫）與空白值。

**Rationale**:
- 沿用專案唯一的設定機制（`Settings`／`.env`），與 `alembic_database_url`
  的既有先例一致，不另闢 `os.environ` 直讀路徑。
- schema 名稱獨立成欄位，guard 才能明確判定「測試資料區是什麼」，
  而不是從連線字串反解（R2 的否決理由之一）。
- 預設 `wuwa_test` 讓乾淨環境只需設定 `TEST_DATABASE_URL` 一個值即可跑
  （SC-004 的 2 步上限：填 env、跑建置腳本）。

**Alternatives considered**: schema 名稱無預設、強制填寫——多一步人工設定
換不到安全性（guard 已擋 `public`），否決。

---

## R6. guard（防呆）的位置與行為

**Decision**: guard 邏輯集中於新檔 `backend/tests/_isolation.py`
（底線開頭，pytest 不收集），conftest 於 **pytest session 開始、
執行任何測試之前**呼叫；不通過即以明確訊息讓整個測試 session 失敗中止。
檢查序：

1. `settings.test_database_url` 為空 → 中止：「未設定 TEST_DATABASE_URL，
   測試不會退回使用 DATABASE_URL」＋設定指引（FR-003）。
2. `settings.test_database_schema` 為空或等於 `public` → 中止（FR-004）。
3. 以 test engine 實連，`SELECT current_schema()` ≠ 設定的測試 schema →
   中止（search_path 未生效即視同指向主要資料區，FR-004）。
   同一連線順帶確認測試 schema 存在，不存在時提示先跑建置腳本。

**Rationale**: 三層檢查對應 spec 的兩個錯誤情境＋執行期驗證；
放在 session 層級保證「被執行的測試案例數為 0」（SC-002）。
邏輯獨立成模組使 FR-008 的安全測試可直接對 guard 函式做單元測試
（以覆寫設定值的方式測兩種拒絕情境），不需真的錯連主庫。

**Alternatives considered**: 放在 `db_session` fixture 內逐測試檢查——
測試已開始收集執行、訊息重複出現，且無法保證 0 案例被執行，否決。

---

## R7. conftest 的 test engine 與既有 fixture 相容性

**Decision**: `_isolation.py` 提供 `create_test_engine()`：
`TEST_DATABASE_URL` + psycopg3 + `poolclass=NullPool` + `connect` 事件設
search_path（R2）。conftest 以它建立 module 層級 test engine，
`db_session`／`client` fixture 的結構（connection → transaction →
savepoint session → rollback）與 `_never_send_real_email` 完全不變，
僅把 `engine` 來源從 `app.core.database` 換成 test engine。

**Rationale**:
- ~~`NullPool`~~ → **修訂（2026-08-04 實作實測）**：改用小型常駐池
  （`pool_size=1, max_overflow=2, pool_pre_ping=True`）。NullPool 讓每個測試
  重付一次對 ap-south-1 的 TCP+TLS 握手，實測整體套件慢到跑不完；
  單連線重用與原主 engine 的行為一致，連線歸還時只 rollback 不重置
  session 狀態，search_path 保留，程序結束連線即釋放，不長期佔用
  Session pooler 名額。
- 既有 rollback 模式已驗證可靠（FR-006 要求保留），不重新發明。
- `app.core.database.engine` 仍會在 import 時建立（SQLAlchemy lazy connect，
  不實際連線），對測試無副作用，不需改動 `database.py`。

**Alternatives considered**: 改 `database.py` 讓 engine 依環境切換——
把測試邏輯滲入正式程式路徑，違反 FR-009 的結構保證原則，否決。

---

## R8. alembic env.py 的最小擴充

**Decision**: `env.py` 的 `run_migrations_online()` 開頭加入慣用模式：
`config.attributes.get("connection")` 有值時直接用該連線跑 migration，
否則走既有 `engine_from_config` 路徑。建置腳本以
`config.attributes["connection"] = <search_path 已綁定的連線>` 傳入。

**Rationale**: 這是 Alembic 官方文件記載的標準做法（"Sharing a Connection"），
向後完全相容：正式 migration 流程（CLI `alembic upgrade head`）不設 attributes，
行為與現況完全相同。

**Alternatives considered**: 建置腳本設環境變數讓 env.py 分支——
隱式全域狀態、易誤觸正式路徑，否決。

---

## 決策總覽

| # | 主題 | 決策 |
|---|---|---|
| R1 | Pooler | 測試與建置走 Session pooler（5432） |
| R2 | search_path 機制 | engine `connect` 事件 `SET search_path`＋實連驗證 |
| R3 | 執行期 search_path | 僅 `<test_schema>`，不含 `public` |
| R4 | 結構建置 | 建置腳本：guard → drop/create schema → `alembic upgrade head`；extension schema 於實作時驗證 |
| R5 | 設定項 | `test_database_url`（預設空）＋ `test_database_schema`（預設 `wuwa_test`） |
| R6 | guard | `tests/_isolation.py`；session 開始前三層檢查，不過即中止 |
| R7 | test engine | NullPool＋事件監聽；既有 fixture 結構不變 |
| R8 | env.py | `config.attributes["connection"]` 慣用擴充，向後相容 |

所有 NEEDS CLARIFICATION：無（唯一運行時驗證項 R4 已定義兩種結果的處理路徑）。
