import re

from app.models.enums import OrderStatus
from tests.factories import (
    create_activity,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_order_with_item,
    create_product,
    create_user,
)
from tests.utils import auth_headers, register_and_login


def _setup_group_buy_product(db_session, **overrides):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, **overrides)
    return group_buy, group_buy_product


def _add_follow_list_item(client, headers, group_buy_product_id, quantity):
    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product_id), "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_create_order_success(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=5, unit_price="200.00")
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 2)

    response = client.post("/api/v1/orders", json={"rules_accepted": True}, headers=headers)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "pending_confirmation"
    assert data["product_total_amount"] == "400.00"
    # 訂單編號為每日流水：WG{YYMMDD}-{6 位流水}
    assert re.fullmatch(r"WG\d{6}-\d{6}", data["order_number"]), data["order_number"]

    follow_list_response = client.get("/api/v1/follow-list", headers=headers)
    assert follow_list_response.json()["data"] is None


def test_create_order_requires_rules_accepted(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)

    response = client.post("/api/v1/orders", json={"rules_accepted": False}, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RULES_NOT_ACCEPTED"


def test_create_order_empty_follow_list(client):
    _, token = register_and_login(client)
    response = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=auth_headers(token)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FOLLOW_LIST_EMPTY"


def test_create_order_insufficient_quantity_keeps_follow_list(client, db_session):
    group_buy, group_buy_product = _setup_group_buy_product(db_session, max_quantity=2)
    buyer = create_user(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 2)

    # Another member's confirmed order consumes all remaining quantity in the meantime.
    create_order_with_item(
        db_session, buyer, group_buy, group_buy_product, quantity=2, status=OrderStatus.PAID
    )

    response = client.post("/api/v1/orders", json={"rules_accepted": True}, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_AVAILABLE_QUANTITY"

    follow_list_response = client.get("/api/v1/follow-list", headers=headers)
    assert follow_list_response.json()["data"] is not None


def test_get_my_orders_list_and_detail(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=5, unit_price="150.00")
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 3)
    create_response = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    )
    order_id = create_response.json()["data"]["id"]

    list_response = client.get("/api/v1/orders", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == order_id
    assert items[0]["product_total_amount"] == "450.00"
    # 依圖 07：列表需提供商品項目數與拒絕原因
    assert items[0]["item_count"] == 1
    assert items[0]["rejection_reason"] is None

    detail_response = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["status"] == "pending_confirmation"
    assert len(detail["items"]) == 1
    assert detail["items"][0]["quantity"] == 3
    assert detail["cancellation_requests"] == []
    assert detail["pending_cancellation_request"] is None
    # 依圖 08 新增的欄位
    assert detail["group_leader_id"]
    assert detail["deadline_at"]
    assert "member_facebook_contact" in detail
    assert "member_discord_contact" in detail
    assert "member_line_contact" in detail
    # 建立訂單即寫入一筆狀態歷史
    assert len(detail["status_history"]) == 1
    assert detail["status_history"][0]["status"] == "pending_confirmation"
    assert detail["status_history"][0]["note"] is None


def test_order_number_is_daily_serial(client, db_session):
    """訂單編號為 WG{YYMMDD}-{6 位流水}，同一天內連號遞增。"""
    from datetime import datetime, timezone

    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=10)
    expected_date_key = datetime.now(timezone.utc).strftime("%y%m%d")

    numbers = []
    for _ in range(2):
        _, token = register_and_login(client)
        headers = auth_headers(token)
        _add_follow_list_item(client, headers, group_buy_product.id, 1)
        response = client.post("/api/v1/orders", json={"rules_accepted": True}, headers=headers)
        assert response.status_code == 201, response.text
        numbers.append(response.json()["data"]["order_number"])

    for number in numbers:
        assert re.fullmatch(rf"WG{expected_date_key}-\d{{6}}", number), number

    first_serial = int(numbers[0].split("-")[1])
    second_serial = int(numbers[1].split("-")[1])
    assert second_serial == first_serial + 1


def test_get_my_orders_filters(client, db_session):
    """依圖 07 篩選卡：活動名稱、團主名稱（不分大小寫部分比對）與時間範圍。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(
        db_session, group_leader_profile=leader_profile, activity=activity
    )
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=5)

    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)
    client.post("/api/v1/orders", json={"rules_accepted": True}, headers=headers)

    activity_name = activity.name
    leader_name = leader_profile.display_name

    def count(params):
        response = client.get("/api/v1/orders", params=params, headers=headers)
        assert response.status_code == 200, response.text
        return len(response.json()["data"])

    # 不帶條件時看得到
    assert count({}) == 1
    # 活動名稱部分比對命中／不命中
    assert count({"activity_name": activity_name[:4]}) == 1
    assert count({"activity_name": "絕對不存在的活動"}) == 0
    # 團主名稱部分比對命中／不命中
    assert count({"group_leader_name": leader_name[:3]}) == 1
    assert count({"group_leader_name": "絕對不存在的團主"}) == 0
    # 時間範圍：剛建立的訂單落在近 7 天內
    assert count({"created_within_days": 7}) == 1
    # 超出允許範圍的天數回 422
    assert client.get(
        "/api/v1/orders", params={"created_within_days": 0}, headers=headers
    ).status_code == 422


def test_order_detail_not_visible_to_other_member(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    ).json()["data"]["id"]

    _, other_token = register_and_login(client)
    response = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(other_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"


def test_create_cancellation_request_success(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests",
        json={"reason": "臨時無法付款"},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["reason"] == "臨時無法付款"


def test_create_cancellation_request_duplicate_pending(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    ).json()["data"]["id"]

    client.post(f"/api/v1/orders/{order_id}/cancellation-requests", json={}, headers=headers)
    second = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests", json={}, headers=headers
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CANCELLATION_REQUEST_PENDING"


def test_create_cancellation_request_blank_reason_normalized_to_null(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client)
    headers = auth_headers(token)
    _add_follow_list_item(client, headers, group_buy_product.id, 1)
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests",
        json={"reason": "   "},
        headers=headers,
    )
    assert response.json()["data"]["reason"] is None
