# Implementation Plan: Admin 權限硬化（admin-permission-hardening）

**Branch**: `fix/admin-permission-hardening` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-admin-permission-hardening/spec.md`

## Summary

後端以共用分層 Dependency（`get_current_member_user`）統一拒絕 Admin 使用收藏、購物車、訂單、團主申請與團主後台共 49 個端點（403 + `ADMIN_MEMBER_ACCESS_FORBIDDEN`），逐端點補 Admin 拒絕測試；前端補上 MemberLayout／GroupLeaderLayout 的 Admin Route Guard（導向 `/admin`）並確認入口隱藏。完成後將 D-06 標記為已解決。無資料庫變更、無 Migration。

## Technical Context

**Language/Version**: Python 3.11+（後端）、JavaScript ES2022 / React 18（前端）

**Primary Dependencies**: FastAPI（Depends 注入權限）、SQLAlchemy、react-router-dom v6

**Storage**: Supabase PostgreSQL——本 feature **不改 schema、不加 Migration**；`app_user.role`（enum，含 `admin`）已存在

**Testing**: pytest（既有 258 案例；使用 D-02 隔離機制 `TEST_DATABASE_URL` → schema `wuwa_test`）；前端以瀏覽器手動驗收（專案無前端自動化測試慣例）

**Target Platform**: Render（後端）＋ GitHub Pages（前端）；本機開發驗證

**Project Type**: Web application（backend FastAPI + frontend React/Vite）

**Performance Goals**: 無新增性能需求；權限檢查為記憶體內 role 比對，零額外查詢

**Constraints**: 不得改變非 Admin 使用者的任何行為（FR-005）；不得動 D-02 測試架構、D-14、D-15；錯誤格式沿用 `05_API_Design §6`（`{"error": {code, message, details}}`）

**Scale/Scope**: 後端 1 個共用 Dependency＋8 個 router 檔的 Depends 替換（49 端點）＋1 個新測試檔（約 49×拒絕 + 5×回歸 + 2×團主雙情境）；前端 2 個 Layout guard＋入口確認

## Constitution Check

*GATE: 依 `.specify/memory/constitution.md` v1.0.0 逐原則判定。*

| 原則 | 判定 | 說明 |
|---|---|---|
| I. Brownfield 保護 | ✅ | 本 feature 是功能修正非文件整理；已先實際閱讀 deps.py、8 個 router、errors.py、前端 Layout／Header／Context。盤點發現的其他問題只記錄（見 research.md〈盤點附帶發現〉），不順手處理 |
| II. 權威順序 | ✅ | 需求來源：REQ-ROLE-060；CD §2.2、§3.1、§13.1、§16.6。無自行推測的產品規則 |
| III. 規格完整性 | ✅ | spec.md 已含 MUST 強度、正常／例外／邊界、可驗收判定 |
| IV. 衝突處理 | ✅ | 個人中心／通知中心的規格衝突依 spec 界線「記錄為新差異、交後續裁決」 |
| V. 規格與實作分離 | ✅ | D-06 僅在 FR-009 五條件全部成立後才改標「已解決（已實作）」 |
| VI. 範圍控制 | ✅ | 允許修改範圍已宣告（見下）；FR-010 禁止清單已列 |
| VII. 可追溯性 | ✅ | 端點清單、Dependency、測試、文件更新逐項對應 |
| VIII. 誠實報告 | ✅ | 測試必須實際執行後才回報；前端驗收需使用者瀏覽器實測確認 |

**允許修改的檔案（宣告範圍）**：

- `backend/app/api/deps.py`（新增 `get_current_member_user`、改 `get_current_group_leader_profile` 的依賴鏈）
- `backend/app/api/v1/{favorites,follow_list,orders,group_leader_applications,group_leader_profile,group_leader_group_buys,group_leader_orders,group_leader_announcements}.py`（僅替換權限 Depends）
- `backend/tests/test_admin_permission_hardening.py`（新增）；`backend/tests/conftest.py`（僅允許新增 admin 測試 fixture）
- `frontend/src/layouts/MemberLayout.jsx`、`frontend/src/layouts/GroupLeaderLayout.jsx`（Admin guard）；前端入口確認若發現漏隱藏，僅修改對應顯示條件
- `docs/CURRENT_DECISIONS.md` §16.6、`docs/EchoGather_Product_Specification_v1.0.md` §21 D-06（完成後）
- `specs/003-admin-permission-hardening/*`（本 feature 文件）

**禁止**：Migration、`app/core/database.py`、D-02 測試架構（除新增 fixture）、業務 Service／Repository 邏輯、其他差異項。

## Project Structure

### Documentation (this feature)

```text
specs/003-admin-permission-hardening/
├── spec.md
├── plan.md              # 本檔
├── research.md          # Phase 0：決策定案（錯誤碼、Dependency 命名、端點清單依據）
├── data-model.md        # Phase 1：無資料變更說明＋涉及的既有實體
├── quickstart.md        # Phase 1：驗證指南
├── contracts/
│   └── admin-restriction.md  # 受限端點契約（49 端點完整清單＋錯誤回應契約）
└── tasks.md             # /speckit-tasks 產出
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                  # [修改] 新增 get_current_member_user；團主鏈改掛其下
│   │   └── v1/
│   │       ├── favorites.py         # [修改] Depends 替換（3 端點）
│   │       ├── follow_list.py       # [修改] Depends 替換（5 端點）
│   │       ├── orders.py            # [修改] Depends 替換（5 端點）
│   │       ├── group_leader_applications.py  # [修改] Depends 替換（2 端點）
│   │       ├── group_leader_profile.py       # [不改或最小改] 依賴鏈自動生效（4 端點）
│   │       ├── group_leader_group_buys.py    # [不改] 依賴鏈自動生效（10 端點）
│   │       ├── group_leader_orders.py        # [不改] 依賴鏈自動生效（14 端點）
│   │       └── group_leader_announcements.py # [不改] 依賴鏈自動生效（6 端點）
│   └── core/errors.py               # [不改] AppError 既有格式沿用
└── tests/
    ├── conftest.py                  # [修改] 新增 admin 使用者／token fixture
    └── test_admin_permission_hardening.py  # [新增] 逐端點 Admin 拒絕＋回歸測試

frontend/
└── src/
    ├── layouts/
    │   ├── MemberLayout.jsx         # [修改] Admin → Navigate to /admin
    │   └── GroupLeaderLayout.jsx    # [修改] Admin → Navigate to /admin（在團主資料檢查之前）
    ├── components/common/Header.jsx # [確認] 已隱藏購物車／通知鈴（現況通過則不改）
    └── pages/…                      # [確認] 收藏／跟團／下單 CTA 的 Admin 隱藏現況
```

**Structure Decision**: 沿用既有 Web application 結構（`backend/app` + `frontend/src`），不新增目錄。權限集中在 `deps.py`，router 檔只換 Depends；團主後台四個 router 因既有依賴鏈（profile → active profile）而在 deps.py 改一處即全部生效，是「單一共用機制」（FR-002）的最小實作。

## 受限端點盤點（FR-001，權威清單見 contracts/admin-restriction.md）

各類數量（全部掛在 `/api/v1` 之下）：

| 類別 | Router 檔 | 端點數 | 目前 Dependency | 預定 Dependency |
|---|---|---|---|---|
| 1. 收藏 | favorites.py | 3 | `get_current_user` | `get_current_member_user` |
| 2. 購物車 | follow_list.py | 5 | `get_current_user` | `get_current_member_user` |
| 3. 會員訂單／取消／拆單 | orders.py | 5 | `get_current_user` | `get_current_member_user` |
| 4. 團主申請 | group_leader_applications.py | 2 | `get_current_user` | `get_current_member_user` |
| 5. 團主後台 | group_leader_profile.py（4）、group_leader_group_buys.py（10）、group_leader_orders.py（14）、group_leader_announcements.py（6） | 34 | `get_current_group_leader_profile`／`get_current_active_group_leader_profile` | 同名，但依賴鏈改為掛在 `get_current_member_user` 之下 |
| **合計** | 8 檔 | **49** | | |

逐端點的「Method＋完整 Path＋目前 Dependency＋預定 Dependency」完整清單在 [contracts/admin-restriction.md](./contracts/admin-restriction.md)，實作與測試以該清單為準（SC-006 的比對基準）。

## Complexity Tracking

無 Constitution 違規，無需填寫。
