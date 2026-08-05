# Research: Admin 權限硬化

**Date**: 2026-08-05 | **Feature**: specs/003-admin-permission-hardening

所有決策以實際閱讀既有程式碼為依據（deps.py、8 個 router、core/errors.py、
frontend Layouts／Header／AvatarMenu／Context、conftest.py）。無外部技術未知項。

## 決策 1：統一錯誤回應（FR-003 定案）

- **Decision**: HTTP `403`；錯誤碼 `ADMIN_MEMBER_ACCESS_FORBIDDEN`；預設訊息「管理員帳號不可使用會員或團主功能。」；格式沿用既有 `AppError` → `{"error": {"code", "message", "details": null}}`。
- **Rationale**: 既有錯誤碼皆為 `SCREAMING_SNAKE_CASE` 語意碼（如 `PERMISSION_DENIED`、`GROUP_LEADER_PROFILE_INCOMPLETE`）。採 spec 建議語意、不重用 `PERMISSION_DENIED`（該碼已用於「非 Admin 呼叫 /admin API」，方向相反，分開利於前端與除錯辨識）。
- **Alternatives considered**: 重用 `PERMISSION_DENIED`（訊息無法區分方向，棄）；HTTP 401（語意錯誤——身分已驗證、是授權被拒，棄）。
- **定案效力**: 依 spec FR-003，實作階段不得更換。

## 決策 2：共用 Dependency 分層與命名（FR-002 定案）

- **Decision**: 在 `backend/app/api/deps.py` 新增：

  ```text
  get_current_user（不變：允許所有已登入帳號，含 Admin）
  └── get_current_member_user（新增：拒絕 role == UserRole.ADMIN → AppError 403）
      └── get_current_group_leader_profile（既有名稱保留；改為依賴 get_current_member_user）
          └── get_current_active_group_leader_profile（既有名稱保留；鏈不變）
  ```

  四類會員端點（favorites、follow_list、orders、group_leader_applications）的
  `Depends(get_current_user)` 逐一替換為 `Depends(get_current_member_user)`；
  團主後台 34 端點不改 router 檔，靠 `get_current_group_leader_profile` 改掛
  `get_current_member_user` 之下自動生效。
- **Rationale**: spec FR-002 要求的是三層**語意**（get_current_user → get_current_member_user → get_current_group_leader）。既有團主層已有兩個成熟名稱（profile／active profile，對應 API Design §4.6 的兩級檢查），保留名稱、只改依賴鏈是最小 diff，且 FastAPI Depends 鏈保證「Admin 先被 403 拒絕、輪不到 404 GROUP_LEADER_PROFILE_NOT_FOUND」（FR-006）。
- **Alternatives considered**: 重新命名為 `get_current_group_leader`（需改 34 處 import／參數，違反最小變更且無行為差異，棄）；router-level `dependencies=[...]`（admin router 的做法，但會員 router 的 handler 需要 user 物件做業務查詢，參數注入better，棄）。

## 決策 3：端點盤點方法（FR-001／SC-006 定案)

- **Decision**: 以 `@router.(get|post|patch|put|delete)` 裝飾器逐檔盤點 8 個 router，
  對照 `router.py` 的 include 順序與各檔 `APIRouter(prefix=...)` 組出完整 Path
  （全域前綴 `/api/v1`）。結果：49 端點（3+5+5+2+4+10+14+6），完整清單見
  contracts/admin-restriction.md。
- **Rationale**: Route 裝飾器是唯一事實來源；SC-006 要求清單與裝飾器盤點 100% 一致。
- **驗證方式**: 測試檔以參數化清單覆蓋全部 49 端點，數量斷言防止漏測。

## 決策 4：測試設計（FR-007 定案）

- **Decision**: 新增 `backend/tests/test_admin_permission_hardening.py`：
  - conftest 新增 admin fixture（建立 role=admin 的使用者與 token；沿用既有的
    測試使用者建立方式，只多設 role）。
  - 參數化 49 筆（method, path）逐端點打 Admin token，斷言：status 403、
    `error.code == "ADMIN_MEMBER_ACCESS_FORBIDDEN"`、回應格式一致；寫入類端點
    另斷言目標資料表無資料異動（before/after count）。
  - 團主後台雙情境：Admin 無團主資料、Admin 被直接塞入團主資料（測試內建構），
    兩者皆 403 同碼。
  - 非 Admin 回歸：每類至少 1 例（一般會員收藏／購物車／下單／團主申請照常、
    團主後台照常）——多數已由既有 258 案例覆蓋，跑全套即為回歸；本檔僅補
    最小煙霧案例明確對照。
  - 全程走 D-02 隔離機制（TEST_DATABASE_URL → wuwa_test），不動主庫。
- **Rationale**: 參數化清單讓「零漏測」可被數量斷言檢查；資料異動檢查滿足 FR-004。
- **Alternatives considered**: 抽樣每模組一端點（spec 明文禁止，棄）。

## 決策 5：前端 Route Guard 與入口（FR-008 現況與缺口）

**已符合現況（唯讀確認，2026-08-05）**：

- `Header.jsx:45,60`——Admin 隱藏購物車連結與通知鈴。
- `AvatarMenu.jsx:48`——Admin 選單只顯示「管理員後台」。
- `CartContext.jsx:13`／`NotificationContext.jsx:24`——Admin 不打購物車／通知 API。
- `GroupBuyDetailPage.jsx:86`——Admin 隱藏跟團／下單面板。

**缺口（需實作）**：

- `MemberLayout.jsx`：只擋未登入；Admin 可直接進 `/profile`、`/favorites`、`/follow-list`、`/orders*`、`/group-leader-application`、`/notifications`。→ 加 `user?.permissions?.is_admin` 判斷，`<Navigate to="/admin" replace />`（在 initializing 之後、渲染之前，滿足「不得短暫顯示內容」）。
- `GroupLeaderLayout.jsx`：Admin 無團主資料時被導向 `/`（非 `/admin`）。→ 在 `!user.group_leader` 檢查**之前**加 Admin 判斷導向 `/admin`。
- 各頁 CTA（收藏按鈕、加入購物車等）需逐頁確認 Admin 隱藏狀況；tasks 列入確認項，發現漏隱藏才改。

- **Decision**: Guard 放在兩個 Layout（統一入口），不逐頁加判斷。
- **Rationale**: 受保護 Route 全部包在這兩個 Layout 下，改兩處即覆蓋全部；與既有「Layout 做導向」慣例一致。

## 決策 6：範圍界線的處理

- `/profile`（個人中心）與 `/notifications`（通知中心）掛在 MemberLayout 下，
  Layout guard 會一併把 Admin 導向 `/admin`。這與 spec「不裁決 Admin 可用」一致
  ——前端本來就沒有給 Admin 的入口（AvatarMenu Admin 分支只有管理員後台）。
- 後端 `users.py`（/users/me 等）、`notifications.py`、`uploads.py`、`auth.py`
  **不列入本次受限清單**（非 D-06 五類）。其中 `notifications.py` 現況允許
  Admin 呼叫但前端不使用——依 spec 記錄為潛在差異，見下節。

## 盤點附帶發現（只記錄，不處理——FR-010／Constitution 原則 I）

1. **會員通知 API 未排除 Admin**：`/api/v1/notifications/*`（5 端點）掛
   `get_current_user`，Admin 可呼叫；前端 Admin 不顯示通知鈴也不輪詢。是否屬
   「Admin 只使用管理後台」的違反，待後續裁決（可能成為新差異項）。
2. **上傳 API**：`/api/v1/uploads`（1 端點）掛 `get_current_user`；Admin 於管理
   後台上傳圖片**必須**經此端點，不得列入受限清單（列入會弄壞管理後台）。
3. `users.py`（/users/me 個人資料、改密碼）掛 `get_current_user`，Admin 可用；
   屬認證基礎能力延伸，spec 已界定維持現狀，其正式定位待後續裁決。

以上 1、3 於 FR-009 文件同步時以一行附註記入 D-06 條目的「後續」欄或新差異項，
由專案負責人裁決編號。
