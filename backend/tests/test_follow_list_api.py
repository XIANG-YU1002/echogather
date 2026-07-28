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


def test_get_follow_list_when_none_exists(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get("/api/v1/follow-list", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_add_item_creates_follow_list(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=5, unit_price="100.00")
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 2},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["estimated_subtotal"] == "200.00"
    assert data["estimated_product_total"] == "200.00"
    assert data["is_submittable"] is True


def test_add_same_product_accumulates_quantity(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=10)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 2},
        headers=headers,
    )
    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 3},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5


def test_add_item_insufficient_quantity(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=2)
    _, token = register_and_login(client, db_session)

    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 5},
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_AVAILABLE_QUANTITY"


def test_add_item_invalid_quantity(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client, db_session)

    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 0},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUANTITY"


def test_add_item_from_different_group_buy_conflicts(client, db_session):
    _, gbp1 = _setup_group_buy_product(db_session)
    _, gbp2 = _setup_group_buy_product(db_session)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(gbp1.id), "quantity": 1},
        headers=headers,
    )
    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(gbp2.id), "quantity": 1},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FOLLOW_LIST_GROUP_BUY_CONFLICT"


def test_add_item_replace_existing(client, db_session):
    _, gbp1 = _setup_group_buy_product(db_session)
    _, gbp2 = _setup_group_buy_product(db_session)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(gbp1.id), "quantity": 1},
        headers=headers,
    )
    response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(gbp2.id), "quantity": 1, "replace_existing": True},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["group_buy_product_id"] == str(gbp2.id)


def test_update_item_quantity(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session, max_quantity=10, unit_price="50.00")
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    add_response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 2},
        headers=headers,
    )
    item_id = add_response.json()["data"]["items"][0]["id"]

    response = client.patch(
        f"/api/v1/follow-list/items/{item_id}", json={"quantity": 4}, headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["quantity"] == 4
    assert data["estimated_subtotal"] == "200.00"
    assert data["estimated_product_total"] == "200.00"


def test_remove_item_deletes_empty_follow_list(client, db_session):
    _, group_buy_product = _setup_group_buy_product(db_session)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    add_response = client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 1},
        headers=headers,
    )
    item_id = add_response.json()["data"]["items"][0]["id"]

    remove_response = client.delete(f"/api/v1/follow-list/items/{item_id}", headers=headers)
    assert remove_response.status_code == 204

    get_response = client.get("/api/v1/follow-list", headers=headers)
    assert get_response.json()["data"] is None


def test_clear_follow_list_idempotent(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.delete("/api/v1/follow-list", headers=auth_headers(token))
    assert response.status_code == 204


def test_follow_list_marks_not_submittable_when_quantity_occupied(client, db_session):
    group_buy, group_buy_product = _setup_group_buy_product(db_session, max_quantity=2)
    buyer = create_user(db_session)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(
        "/api/v1/follow-list/items",
        json={"group_buy_product_id": str(group_buy_product.id), "quantity": 2},
        headers=headers,
    )

    create_order_with_item(
        db_session, buyer, group_buy, group_buy_product, quantity=2, status=OrderStatus.PAID
    )

    response = client.get("/api/v1/follow-list", headers=headers)
    data = response.json()["data"]
    assert data["is_submittable"] is False
    assert "INSUFFICIENT_AVAILABLE_QUANTITY" in data["invalid_reasons"]
    assert data["items"][0]["is_available"] is False
