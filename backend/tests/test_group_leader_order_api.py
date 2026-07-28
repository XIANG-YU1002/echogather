from tests.factories import (
    create_activity,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_product,
    create_user,
)
from tests.utils import auth_headers, login, register_and_login


def _setup_leader_and_group_buy(db_session, **gbp_overrides):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, **gbp_overrides)
    return leader_user, leader_profile, group_buy, group_buy_product


def _leader_headers(client, leader_user):
    token = login(client, leader_user.email, "Passw0rd1")
    return auth_headers(token)


def _create_order(client, db_session, group_buy_product_id, quantity=1):
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)
    add_response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product_id), "quantity": quantity},
        headers=headers,
    )
    assert add_response.status_code == 201, add_response.text
    create_response = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=headers
    )
    assert create_response.status_code == 201, create_response.text
    return create_response.json()["data"]["id"]


def test_get_orders_and_detail_for_leader(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    order_id = _create_order(client, db_session, group_buy_product.id)
    leader_headers = _leader_headers(client, leader_user)

    list_response = client.get("/api/v1/group-leader/orders", headers=leader_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    detail_response = client.get(
        f"/api/v1/group-leader/orders/{order_id}", headers=leader_headers
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["available_actions"] == ["accept", "reject"]
    assert detail["member_contacts"]["discord"] == "tester_discord"


def test_group_leader_orders_requires_completed_profile(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    token = login(client, leader_user.email, "Passw0rd1")

    response = client.get("/api/v1/group-leader/orders", headers=auth_headers(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GROUP_LEADER_PROFILE_INCOMPLETE"


def test_accept_then_conflict_on_repeat(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    order_id = _create_order(client, db_session, group_buy_product.id)
    leader_headers = _leader_headers(client, leader_user)

    accept_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/accept", headers=leader_headers
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["data"]["status"] == "pending_payment"

    repeat_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/accept", headers=leader_headers
    )
    assert repeat_response.status_code == 409
    assert repeat_response.json()["error"]["code"] == "ORDER_STATUS_CONFLICT"


def test_status_history_written_on_transitions(client, db_session):
    """依圖 08：每次狀態變更都要寫入 order_status_history，拒絕時連同原因存為 note。"""
    from app.models.order import OrderStatusHistory

    def history_for(order_id):
        return (
            db_session.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc())
            .all()
        )

    leader_user, _profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session, max_quantity=10
    )
    leader_headers = _leader_headers(client, leader_user)

    # 建立即寫入一筆
    accepted_id = _create_order(client, db_session, group_buy_product.id)
    entries = history_for(accepted_id)
    assert [e.status.value for e in entries] == ["pending_confirmation"]

    # 接受 -> 追加一筆 pending_payment
    assert client.post(
        f"/api/v1/group-leader/orders/{accepted_id}/accept", headers=leader_headers
    ).status_code == 200
    entries = history_for(accepted_id)
    assert [e.status.value for e in entries] == ["pending_confirmation", "pending_payment"]
    assert entries[1].note is None

    # 標記付款 -> 追加一筆 paid
    assert client.post(
        f"/api/v1/group-leader/orders/{accepted_id}/mark-paid", headers=leader_headers
    ).status_code == 200
    assert [e.status.value for e in history_for(accepted_id)] == [
        "pending_confirmation",
        "pending_payment",
        "paid",
    ]

    # 另一張訂單拒絕 -> note 存拒絕原因
    rejected_id = _create_order(client, db_session, group_buy_product.id)
    assert client.post(
        f"/api/v1/group-leader/orders/{rejected_id}/reject",
        json={"reason": "本次可接受數量不足。"},
        headers=leader_headers,
    ).status_code == 200
    entries = history_for(rejected_id)
    assert [e.status.value for e in entries] == ["pending_confirmation", "rejected"]
    assert entries[1].note == "本次可接受數量不足。"


def test_reject_order_requires_reason(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    order_id = _create_order(client, db_session, group_buy_product.id)
    leader_headers = _leader_headers(client, leader_user)

    blank_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/reject",
        json={"reason": "   "},
        headers=leader_headers,
    )
    assert blank_response.status_code == 422
    assert blank_response.json()["error"]["code"] == "ORDER_REJECTION_REASON_REQUIRED"

    response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/reject",
        json={"reason": "數量不足"},
        headers=leader_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"
    assert response.json()["data"]["rejection_reason"] == "數量不足"


def test_full_order_lifecycle(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    order_id = _create_order(client, db_session, group_buy_product.id)
    leader_headers = _leader_headers(client, leader_user)

    client.post(f"/api/v1/group-leader/orders/{order_id}/accept", headers=leader_headers)

    skip_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/mark-shipped", headers=leader_headers
    )
    assert skip_response.status_code == 409

    paid_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/mark-paid", headers=leader_headers
    )
    assert paid_response.json()["data"]["status"] == "paid"

    shipped_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/mark-shipped", headers=leader_headers
    )
    assert shipped_response.json()["data"]["status"] == "shipped"

    complete_response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/complete", headers=leader_headers
    )
    assert complete_response.json()["data"]["status"] == "completed"


def test_order_not_owned_by_other_leader(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    order_id = _create_order(client, db_session, group_buy_product.id)

    other_leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=other_leader_user, complete=True)
    other_headers = _leader_headers(client, other_leader_user)

    response = client.post(
        f"/api/v1/group-leader/orders/{order_id}/accept", headers=other_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_OWNED_BY_GROUP_LEADER"


def test_approve_cancellation_cancels_order(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    add_response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 1},
        headers=member_headers,
    )
    assert add_response.status_code == 201
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=member_headers
    ).json()["data"]["id"]

    cancellation_response = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests",
        json={"reason": "改變心意"},
        headers=member_headers,
    )
    request_id = cancellation_response.json()["data"]["id"]

    leader_headers = _leader_headers(client, leader_user)
    approve_response = client.post(
        f"/api/v1/group-leader/cancellation-requests/{request_id}/approve",
        json={"response_note": "已確認"},
        headers=leader_headers,
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["data"]["status"] == "approved"

    order_detail = client.get(f"/api/v1/orders/{order_id}", headers=member_headers)
    assert order_detail.json()["data"]["status"] == "cancelled"


def test_reject_cancellation_keeps_order_status(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 1},
        headers=member_headers,
    )
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=member_headers
    ).json()["data"]["id"]
    request_id = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests", json={}, headers=member_headers
    ).json()["data"]["id"]

    leader_headers = _leader_headers(client, leader_user)
    reject_response = client.post(
        f"/api/v1/group-leader/cancellation-requests/{request_id}/reject",
        json={},
        headers=leader_headers,
    )
    assert reject_response.json()["data"]["status"] == "rejected"

    order_detail = client.get(f"/api/v1/orders/{order_id}", headers=member_headers)
    assert order_detail.json()["data"]["status"] == "pending_confirmation"

    # Member can reapply after rejection.
    reapply_response = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests", json={}, headers=member_headers
    )
    assert reapply_response.status_code == 201


def test_approve_already_processed_cancellation_conflicts(client, db_session):
    leader_user, _leader_profile, _group_buy, group_buy_product = _setup_leader_and_group_buy(
        db_session
    )
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 1},
        headers=member_headers,
    )
    order_id = client.post(
        "/api/v1/orders", json={"rules_accepted": True}, headers=member_headers
    ).json()["data"]["id"]
    request_id = client.post(
        f"/api/v1/orders/{order_id}/cancellation-requests", json={}, headers=member_headers
    ).json()["data"]["id"]

    leader_headers = _leader_headers(client, leader_user)
    client.post(
        f"/api/v1/group-leader/cancellation-requests/{request_id}/approve",
        json={},
        headers=leader_headers,
    )
    second_response = client.post(
        f"/api/v1/group-leader/cancellation-requests/{request_id}/approve",
        json={},
        headers=leader_headers,
    )
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "CANCELLATION_REQUEST_ALREADY_PROCESSED"
