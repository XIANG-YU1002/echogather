"""D-06 Admin 權限硬化測試（specs/003-admin-permission-hardening）。

逐端點驗證：Admin 呼叫收藏、購物車、訂單、團主申請與團主後台共 49 個端點時，
一律回 403 ADMIN_MEMBER_ACCESS_FORBIDDEN、統一回應格式、零資料異動。
端點清單與 contracts/admin-restriction.md 一對一對應，總數斷言防漏測（SC-006）。
"""

import uuid

import pytest
from sqlalchemy import func, select

from app.models.enums import UserRole
from app.models.favorite import ProductFavorite
from app.models.follow_list import FollowList, FollowListItem
from app.models.group_buy import GroupBuy, GroupBuyProduct
from app.models.group_leader import GroupLeaderApplication, GroupLeaderProfile
from app.models.order import (
    CancellationRequest,
    GroupOrder,
    OrderItem,
    OrderMerge,
    OrderUnmergeRequest,
)
from tests.factories import create_group_leader_profile, create_user
from tests.utils import auth_headers, login

EXPECTED_CODE = "ADMIN_MEMBER_ACCESS_FORBIDDEN"
EXPECTED_MESSAGE = "管理員帳號不可使用會員或團主功能。"

# 拒絕必須發生在任何寫入之前；寫入類端點以這些表的筆數快照驗證零異動（FR-004）。
MUTATION_MODELS = [
    ProductFavorite,
    FollowList,
    FollowListItem,
    GroupOrder,
    OrderItem,
    CancellationRequest,
    OrderMerge,
    OrderUnmergeRequest,
    GroupLeaderApplication,
    GroupLeaderProfile,
    GroupBuy,
    GroupBuyProduct,
]

# (method, path_template)——與 contracts/admin-restriction.md #1–#49 完全一致。
# 路徑參數以隨機 UUID 代入：Dependency 在路由解析後、Handler 執行前就會拒絕，
# 不需要真實資源存在。
RESTRICTED_ENDPOINTS = [
    # 類別 1：收藏（3）
    ("GET", "/api/v1/favorites/products"),
    ("POST", "/api/v1/favorites/products/{id}"),
    ("DELETE", "/api/v1/favorites/products/{id}"),
    # 類別 2：購物車（5）
    ("GET", "/api/v1/follow-list"),
    ("POST", "/api/v1/follow-list/items"),
    ("PATCH", "/api/v1/follow-list/items/{id}"),
    ("DELETE", "/api/v1/follow-list/items/{id}"),
    ("DELETE", "/api/v1/follow-list"),
    # 類別 3：會員訂單、取消申請與拆單申請（5）
    ("POST", "/api/v1/orders"),
    ("GET", "/api/v1/orders"),
    ("GET", "/api/v1/orders/{id}"),
    ("POST", "/api/v1/orders/{id}/cancellation-requests"),
    ("POST", "/api/v1/orders/{id}/unmerge-requests"),
    # 類別 4：團主申請（2）
    ("POST", "/api/v1/group-leader-applications"),
    ("GET", "/api/v1/group-leader-applications/me"),
    # 類別 5a：團主資料與儀表板（4）
    ("GET", "/api/v1/group-leader/profile"),
    ("PATCH", "/api/v1/group-leader/profile"),
    ("PATCH", "/api/v1/group-leader/profile/default-rules"),
    ("GET", "/api/v1/group-leader/dashboard"),
    # 類別 5b：開團管理（10）
    ("GET", "/api/v1/group-leader/group-buys"),
    ("GET", "/api/v1/group-leader/group-buys/open"),
    ("POST", "/api/v1/group-leader/group-buys"),
    ("GET", "/api/v1/group-leader/group-buys/{id}"),
    ("GET", "/api/v1/group-leader/group-buys/{id}/product-orders"),
    ("PATCH", "/api/v1/group-leader/group-buys/{id}"),
    ("POST", "/api/v1/group-leader/group-buys/{id}/products"),
    ("PATCH", "/api/v1/group-leader/group-buys/{id}/products/{id2}"),
    ("DELETE", "/api/v1/group-leader/group-buys/{id}/products/{id2}"),
    ("POST", "/api/v1/group-leader/group-buys/{id}/close"),
    # 類別 5c：團主訂單管理（14）
    ("GET", "/api/v1/group-leader/orders"),
    ("GET", "/api/v1/group-leader/orders/{id}/mergeable"),
    ("POST", "/api/v1/group-leader/orders/{id}/merge"),
    ("GET", "/api/v1/group-leader/orders/{id}"),
    ("POST", "/api/v1/group-leader/orders/{id}/accept"),
    ("POST", "/api/v1/group-leader/orders/{id}/reject"),
    ("POST", "/api/v1/group-leader/orders/{id}/mark-paid"),
    ("POST", "/api/v1/group-leader/group-buys/{id}/orders/mark-all-shipped"),
    ("POST", "/api/v1/group-leader/orders/{id}/mark-shipped"),
    ("POST", "/api/v1/group-leader/orders/{id}/complete"),
    ("POST", "/api/v1/group-leader/cancellation-requests/{id}/approve"),
    ("POST", "/api/v1/group-leader/cancellation-requests/{id}/reject"),
    ("POST", "/api/v1/group-leader/unmerge-requests/{id}/approve"),
    ("POST", "/api/v1/group-leader/unmerge-requests/{id}/reject"),
    # 類別 5d：團主公告（6）
    ("GET", "/api/v1/group-leader/announcements"),
    ("GET", "/api/v1/group-leader/announcements/recipient-preview"),
    ("POST", "/api/v1/group-leader/announcements"),
    ("GET", "/api/v1/group-leader/announcements/{id}"),
    ("PATCH", "/api/v1/group-leader/announcements/{id}"),
    ("DELETE", "/api/v1/group-leader/announcements/{id}"),
]


def test_restricted_endpoint_count_matches_contract():
    """SC-006：清單總數必須等於 contracts 盤點的 49；改動端點時兩邊要一起更新。"""
    assert len(RESTRICTED_ENDPOINTS) == 49


def _resolve(path_template: str) -> str:
    return path_template.replace("{id}", str(uuid.uuid4())).replace("{id2}", str(uuid.uuid4()))


def _table_counts(db_session) -> list[int]:
    return [
        db_session.execute(select(func.count()).select_from(model)).scalar_one()
        for model in MUTATION_MODELS
    ]


def _assert_admin_rejected(response):
    assert response.status_code == 403, response.text
    body = response.json()
    # 統一回應格式（05_API_Design §6）：error 物件含 code/message/details
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == EXPECTED_CODE
    assert body["error"]["message"] == EXPECTED_MESSAGE


@pytest.mark.parametrize(("method", "path_template"), RESTRICTED_ENDPOINTS)
def test_admin_rejected_on_every_restricted_endpoint(
    client, db_session, admin_headers, method, path_template
):
    """49 端點逐一驗證：403、統一錯誤碼與格式、寫入類端點零資料異動。"""
    is_write = method in ("POST", "PATCH", "DELETE")
    before = _table_counts(db_session) if is_write else None

    response = client.request(
        method, _resolve(path_template), headers=admin_headers, json={} if is_write else None
    )

    _assert_admin_rejected(response)
    if is_write:
        assert _table_counts(db_session) == before, "Admin 被拒後不得有任何資料異動"


def test_admin_with_leftover_leader_profile_still_rejected(client, db_session):
    """Edge Case／FR-006：Admin 即使意外持有團主資料，仍以角色拒絕（非依資料判斷）。"""
    admin = create_user(db_session, role=UserRole.ADMIN)
    create_group_leader_profile(db_session, user=admin)
    headers = auth_headers(login(client, admin.email, "Passw0rd1"))

    for path in ("/api/v1/group-leader/profile", "/api/v1/group-leader/dashboard"):
        _assert_admin_rejected(client.get(path, headers=headers))


def test_member_endpoints_unchanged_for_regular_member(client, db_session):
    """FR-005 回歸煙霧：一般會員四類會員功能不受影響（完整行為由既有測試涵蓋）。"""
    member = create_user(db_session)
    headers = auth_headers(login(client, member.email, "Passw0rd1"))

    assert client.get("/api/v1/favorites/products", headers=headers).status_code == 200
    assert client.get("/api/v1/follow-list", headers=headers).status_code == 200
    assert client.get("/api/v1/orders", headers=headers).status_code == 200
    application = client.get("/api/v1/group-leader-applications/me", headers=headers)
    assert application.status_code != 403, application.text


def test_leader_endpoints_unchanged_for_regular_leader(client, db_session):
    """FR-005 回歸煙霧：有效團主的團主後台不受影響。"""
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user)
    headers = auth_headers(login(client, leader_user.email, "Passw0rd1"))

    assert client.get("/api/v1/group-leader/dashboard", headers=headers).status_code == 200
    assert client.get("/api/v1/group-leader/group-buys", headers=headers).status_code == 200
