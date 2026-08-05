# Data Model: Admin 權限硬化

**Feature**: specs/003-admin-permission-hardening | **Date**: 2026-08-05

## 資料庫變更

**無。** 本 feature 不新增資料表、欄位、Enum 值或 Migration（見 plan.md 禁止範圍）。

## 涉及的既有實體（唯讀依據）

- **AppUser**（`app_user`）：`role` 欄位（enum `UserRole`，值含 `member`／`admin`）
  是唯一判斷依據。`get_current_member_user` 以 `user.role == UserRole.ADMIN` 拒絕。
- **GroupLeaderProfile**（`group_leader_profile`）：團主資格資料。本 feature 明定
  其**不參與** Admin 判斷——即使 Admin 帳號意外持有團主資料，仍以 role 拒絕（FR-006、
  Edge Case）。
- **受保護資料（拒絕時零異動，FR-004）**：`favorite_product`、`follow_list_item`、
  `order`／`order_item`、`order_cancellation_request`、`order_unmerge_request`、
  `group_leader_application`、`group_buy`／`group_buy_product`、`group_leader_announcement`。
  測試以 before/after 筆數快照驗證寫入類端點零異動。

## 狀態轉換

無新增狀態。權限判斷為無狀態的請求層檢查。
