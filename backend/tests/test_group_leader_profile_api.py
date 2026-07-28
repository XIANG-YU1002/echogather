import uuid

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
from tests.utils import auth_headers, login, register_and_login


def _leader_headers(client, leader_user):
    token = login(client, leader_user.email, "Passw0rd1")
    return auth_headers(token)


def _unique_display_name() -> str:
    """測試跑在與示範資料共用的資料庫上，寫死名稱會撞 uq_group_leader_display_name_lower。"""
    return f"測試團-{uuid.uuid4().hex[:8]}"


def test_get_profile_requires_group_leader_profile(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get("/api/v1/group-leader/profile", headers=auth_headers(token))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_LEADER_PROFILE_NOT_FOUND"


def test_get_incomplete_profile_allowed(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    headers = _leader_headers(client, leader_user)

    response = client.get("/api/v1/group-leader/profile", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["display_name"] is None
    assert data["is_profile_complete"] is False


def test_update_profile_sets_display_name_and_contact(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    headers = _leader_headers(client, leader_user)

    display_name = _unique_display_name()
    response = client.patch(
        "/api/v1/group-leader/profile",
        json={"display_name": display_name, "discord_contact": "moon_group"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["display_name"] == display_name
    assert data["is_profile_complete"] is True


def test_update_profile_display_name_immutable_after_set(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=True)
    headers = _leader_headers(client, leader_user)

    response = client.patch(
        "/api/v1/group-leader/profile",
        json={"display_name": "新名稱"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GROUP_LEADER_DISPLAY_NAME_IMMUTABLE"


def test_update_profile_display_name_duplicate(client, db_session):
    taken_name = _unique_display_name()
    create_group_leader_profile(db_session, complete=False, display_name=taken_name)
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    headers = _leader_headers(client, leader_user)

    response = client.patch(
        "/api/v1/group-leader/profile",
        json={"display_name": taken_name, "discord_contact": "abc"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GROUP_LEADER_DISPLAY_NAME_UNAVAILABLE"


def test_update_profile_requires_at_least_one_contact(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=True)
    headers = _leader_headers(client, leader_user)

    response = client.patch(
        "/api/v1/group-leader/profile",
        json={"discord_contact": None},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTACT_REQUIRED"


def test_update_default_rules(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=True)
    headers = _leader_headers(client, leader_user)

    response = client.patch(
        "/api/v1/group-leader/profile/default-rules",
        json={"default_rules": "預設團規內容"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["default_rules"] == "預設團規內容"


def test_dashboard_requires_completed_profile(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    headers = _leader_headers(client, leader_user)

    response = client.get("/api/v1/group-leader/dashboard", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GROUP_LEADER_PROFILE_INCOMPLETE"


def test_dashboard_counts(client, db_session):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=10)
    buyer = create_user(db_session)
    create_order_with_item(
        db_session,
        buyer,
        group_buy,
        group_buy_product,
        quantity=1,
        status=OrderStatus.PENDING_CONFIRMATION,
    )

    headers = _leader_headers(client, leader_user)
    response = client.get("/api/v1/group-leader/dashboard", headers=headers)

    assert response.status_code == 200
    cards = {card["key"]: card["count"] for card in response.json()["data"]["cards"]}
    assert cards["open_group_buys"] == 1
    assert cards["pending_confirmation_orders"] == 1
    assert cards["pending_payment_orders"] == 0
    assert cards["pending_cancellation_requests"] == 0
