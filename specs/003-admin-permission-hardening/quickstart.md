# Quickstart: Admin 權限硬化驗證指南

**Feature**: specs/003-admin-permission-hardening

## 前置條件

1. `backend/.env` 含 `TEST_DATABASE_URL`（D-02 隔離機制；本機值同 `DATABASE_URL`，隔離靠 schema）。
2. 測試 schema 已建置（新 clone 或主庫有新 migration 後執行）：

   ```powershell
   cd backend
   venv\Scripts\python scripts\build_test_schema.py
   ```

## 後端驗證

```powershell
cd backend
venv\Scripts\python -m pytest tests\test_admin_permission_hardening.py -v   # 新增測試
venv\Scripts\python -m pytest                                               # 完整回歸（FR-009 條件 3）
```

**預期**：新增測試全過（49 端點逐一 403 `ADMIN_MEMBER_ACCESS_FORBIDDEN`、
零資料異動、團主雙情境、非 Admin 回歸）；既有 258 案例全過、無行為變化。

手動抽查（本機起後端後，以 Admin token 打任一受限端點）：

```powershell
# 預期 403 + {"error":{"code":"ADMIN_MEMBER_ACCESS_FORBIDDEN",...}}
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/follow-list/items `
  -H "Authorization: Bearer <ADMIN_TOKEN>" -H "Content-Type: application/json" `
  -d '{\"group_buy_product_id\":\"...\",\"quantity\":1}'
```

## 前端驗證（使用者瀏覽器實測，FR-009 條件 4）

以 Admin 帳號登入前台，逐項確認：

1. Header 無購物車、無通知鈴；頭像選單只有「管理員後台」。
2. 直接輸入下列網址，全部**立即**導向 `/admin`（不閃現頁面內容）：
   `/profile`、`/favorites`、`/notifications`、`/follow-list`、`/orders`、
   `/orders/confirm`、`/group-leader-application`、`/group-leader`、
   `/group-leader/group-buys`、`/group-leader/orders`、`/group-leader/announcements`。
3. 商品詳情頁無收藏按鈕、開團詳情頁無跟團／下單面板。
4. 以一般會員與團主帳號重測上述頁面：行為與修改前相同。

## 驗收對照

| 驗證 | 對應 |
|---|---|
| 新增測試全過（49/49） | SC-001、SC-002、SC-006、FR-003/004/006/007 |
| 完整 pytest 全過 | SC-004、FR-005、FR-009 條件 3 |
| 前端逐項確認 | SC-003、FR-008、FR-009 條件 4 |
| 文件同步（兩份） | SC-005、FR-009 |

契約細節見 [contracts/admin-restriction.md](./contracts/admin-restriction.md)；
端點與 Dependency 設計見 [research.md](./research.md)。
