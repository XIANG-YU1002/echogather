from tests.factories import create_activity, create_group_buy, create_group_buy_product, create_group_leader_profile, create_product, create_user
from tests.utils import auth_headers, login, register_and_login


def _setup_leader_and_group_buy(db_session, **gbp_overrides):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, **gbp_overrides)
    return leader_user, leader_profile, group_buy, group_buy_product


def _create_order_and_accept(client, db_session):
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

    leader_token = login(client, leader_user.email, "Passw0rd1")
    client.post(
        f"/api/v1/group-leader/orders/{order_id}/accept",
        headers=auth_headers(leader_token),
    )
    return member_headers, order_id


def test_notification_created_on_order_accept(client, db_session):
    member_headers, order_id = _create_order_and_accept(client, db_session)

    response = client.get("/api/v1/notifications", headers=member_headers)
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["notification_type"] == "system"
    assert items[0]["is_read"] is False
    assert items[0]["source"] == {"type": "order", "id": order_id}
    assert items[0]["target_url"] == f"/orders/{order_id}"


def test_unread_count(client, db_session):
    member_headers, _order_id = _create_order_and_accept(client, db_session)

    response = client.get("/api/v1/notifications/unread-count", headers=member_headers)
    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 1


def test_mark_notification_read_is_idempotent(client, db_session):
    member_headers, _order_id = _create_order_and_accept(client, db_session)
    notification_id = client.get("/api/v1/notifications", headers=member_headers).json()["data"][
        0
    ]["id"]

    first = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=member_headers
    )
    assert first.status_code == 200

    unread_after_first = client.get(
        "/api/v1/notifications/unread-count", headers=member_headers
    ).json()["data"]["unread_count"]
    assert unread_after_first == 0

    detail_after_first = client.get("/api/v1/notifications", headers=member_headers).json()[
        "data"
    ][0]
    read_at_first = detail_after_first["read_at"]
    assert detail_after_first["is_read"] is True

    second = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=member_headers
    )
    assert second.status_code == 200

    detail_after_second = client.get("/api/v1/notifications", headers=member_headers).json()[
        "data"
    ][0]
    assert detail_after_second["read_at"] == read_at_first


def test_mark_all_notifications_read(client, db_session):
    member_headers, _order_id = _create_order_and_accept(client, db_session)

    response = client.patch("/api/v1/notifications/read-all", headers=member_headers)
    assert response.status_code == 200

    unread = client.get(
        "/api/v1/notifications/unread-count", headers=member_headers
    ).json()["data"]["unread_count"]
    assert unread == 0


def test_notification_requires_authentication(client):
    response = client.get("/api/v1/notifications")
    assert response.status_code == 401


def test_mark_other_users_notification_not_found(client, db_session):
    member_headers, _order_id = _create_order_and_accept(client, db_session)
    notification_id = client.get("/api/v1/notifications", headers=member_headers).json()["data"][
        0
    ]["id"]

    _, other_token = register_and_login(client, db_session)
    response = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=auth_headers(other_token)
    )
    assert response.status_code == 404
