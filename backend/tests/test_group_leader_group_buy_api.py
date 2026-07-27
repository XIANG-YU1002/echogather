from datetime import datetime, timedelta, timezone

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
from tests.utils import auth_headers, login


def _leader(client, db_session, **overrides):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=True, **overrides)
    token = login(client, leader_user.email, "Passw0rd1")
    return auth_headers(token)


def _future_deadline(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_payload(product_id, **overrides):
    payload = {
        "activity_id": None,
        "products": [{"product_id": str(product_id), "unit_price": "100.00", "max_quantity": 5}],
        "payment_method": "cash_on_delivery",
        "requires_second_payment": False,
        "includes_full_gift": False,
        "deadline_at": _future_deadline(),
        "rules": "團規內容",
        "contact_platform": "discord",
        "contact_value": "leader_discord",
    }
    payload.update(overrides)
    return payload


def test_create_group_buy_success(client, db_session):
    activity = create_activity(db_session, has_full_gift=True)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id), includes_full_gift=True)
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "open"
    assert len(data["products"]) == 1
    assert data["products"][0]["available_quantity"] == 5
    assert data["has_orders"] is False
    assert set(data["editable_fields"]) == {
        "payment_method",
        "payment_method_note",
        "requires_second_payment",
        "includes_full_gift",
        "deadline_at",
        "rules",
        "contact_platform",
        "contact_value",
        "unit_price",
        "max_quantity",
    }


def test_create_group_buy_requires_completed_profile(client, db_session):
    leader_user = create_user(db_session)
    create_group_leader_profile(db_session, user=leader_user, complete=False)
    token = login(client, leader_user.email, "Passw0rd1")
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    response = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=auth_headers(token)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GROUP_LEADER_PROFILE_INCOMPLETE"


def test_create_group_buy_activity_not_open(client, db_session):
    from app.models.enums import ActivityStatus

    activity = create_activity(db_session, status=ActivityStatus.ENDED)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACTIVITY_NOT_OPEN"


def test_create_group_buy_product_inactive(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity, is_active=False)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_INACTIVE"


def test_create_group_buy_product_activity_mismatch(client, db_session):
    activity = create_activity(db_session)
    other_activity = create_activity(db_session)
    product = create_product(db_session, activity=other_activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_ACTIVITY_MISMATCH"


def test_create_group_buy_full_gift_not_supported(client, db_session):
    activity = create_activity(db_session, has_full_gift=False)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id), includes_full_gift=True)
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FULL_GIFT_NOT_SUPPORTED"


def test_create_group_buy_deadline_in_past(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = _base_payload(product.id, activity_id=str(activity.id), deadline_at=past)
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_group_buy_rejects_removed_other_payment_method(client, db_session):
    """付款方式已移除 'other'，只接受 bank_transfer 與 cash_on_delivery。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id), payment_method="other")
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422


def test_create_group_buy_payment_method_note_is_optional(client, db_session):
    """付款方式備註為選填，任何付款方式皆可填寫；空白會被正規化成 None。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    # 匯款 + 有備註
    payload = _base_payload(
        product.id,
        activity_id=str(activity.id),
        payment_method="bank_transfer",
        payment_method_note="團費確認後再私訊告知匯款帳號",
    )
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["payment_method_note"] == "團費確認後再私訊告知匯款帳號"

    # 另一個活動：取貨付款 + 只有空白的備註 -> 存成 None
    other_activity = create_activity(db_session)
    other_product = create_product(db_session, activity=other_activity)
    payload = _base_payload(
        other_product.id,
        activity_id=str(other_activity.id),
        payment_method="cash_on_delivery",
        payment_method_note="   ",
    )
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["payment_method_note"] is None


def test_create_group_buy_rejects_second_open_group_buy_for_same_activity(client, db_session):
    """同一團主對同一活動同時只能有一個進行中的開團。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    assert client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers).status_code == 201

    second = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "GROUP_BUY_ALREADY_OPEN_FOR_ACTIVITY"


def test_create_group_buy_allows_other_leader_same_activity(client, db_session):
    """限制只針對同一團主；不同團主對同一活動仍可各自開團。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    first_headers = _leader(client, db_session)
    assert client.post("/api/v1/group-leader/group-buys", json=payload, headers=first_headers).status_code == 201

    second_headers = _leader(client, db_session)
    assert client.post("/api/v1/group-leader/group-buys", json=payload, headers=second_headers).status_code == 201


def test_create_group_buy_duplicate_products_rejected(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(product.id, activity_id=str(activity.id))
    payload["products"].append(
        {"product_id": str(product.id), "unit_price": "50.00", "max_quantity": 2}
    )
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422


def test_get_my_group_buys_list_with_status_filter(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id))
    client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    open_response = client.get(
        "/api/v1/group-leader/group-buys", params={"status": "open"}, headers=headers
    )
    assert len(open_response.json()["data"]) == 1

    closed_response = client.get(
        "/api/v1/group-leader/group-buys", params={"status": "closed"}, headers=headers
    )
    assert len(closed_response.json()["data"]) == 0


def test_group_buy_not_owned_by_other_leader(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id))
    group_buy_id = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]["id"]

    other_headers = _leader(client, db_session)
    response = client.get(f"/api/v1/group-leader/group-buys/{group_buy_id}", headers=other_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_BUY_NOT_OWNED"


def test_update_group_buy_settings_full_update_without_orders(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id))
    group_buy_id = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]["id"]

    response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy_id}",
        json={"rules": "新的團規", "payment_method": "bank_transfer"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["rules"] == "新的團規"
    assert data["payment_method"] == "bank_transfer"


def test_update_group_buy_settings_frozen_after_orders(client, db_session):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=5)
    buyer = create_user(db_session)
    create_order_with_item(db_session, buyer, group_buy, group_buy_product, quantity=1)

    headers = auth_headers(login(client, leader_user.email, "Passw0rd1"))

    frozen_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}",
        json={"rules": "改團規"},
        headers=headers,
    )
    assert frozen_response.status_code == 409
    assert frozen_response.json()["error"]["code"] == "GROUP_BUY_FIELDS_FROZEN"

    allowed_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}",
        json={"contact_value": "new_contact"},
        headers=headers,
    )
    assert allowed_response.status_code == 200
    assert allowed_response.json()["data"]["contact_value"] == "new_contact"
    assert allowed_response.json()["data"]["has_orders"] is True
    assert set(allowed_response.json()["data"]["editable_fields"]) == {
        "deadline_at",
        "contact_platform",
        "contact_value",
        "max_quantity",
    }


def test_add_and_remove_group_buy_product(client, db_session):
    activity = create_activity(db_session)
    product1 = create_product(db_session, activity=activity)
    product2 = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product1.id, activity_id=str(activity.id))
    detail = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]
    group_buy_id = detail["id"]
    first_gbp_id = detail["products"][0]["id"]

    add_response = client.post(
        f"/api/v1/group-leader/group-buys/{group_buy_id}/products",
        json={"product_id": str(product2.id), "unit_price": "80.00", "max_quantity": 3},
        headers=headers,
    )
    assert add_response.status_code == 201
    assert len(add_response.json()["data"]["products"]) == 2

    remove_response = client.delete(
        f"/api/v1/group-leader/group-buys/{group_buy_id}/products/{first_gbp_id}",
        headers=headers,
    )
    assert remove_response.status_code == 200
    assert len(remove_response.json()["data"]["products"]) == 1


def test_remove_last_product_blocked(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id))
    detail = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]

    response = client.delete(
        f"/api/v1/group-leader/group-buys/{detail['id']}/products/{detail['products'][0]['id']}",
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GROUP_BUY_MUST_KEEP_ONE_PRODUCT"


def test_add_product_blocked_when_has_orders(client, db_session):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    other_product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=5)
    buyer = create_user(db_session)
    create_order_with_item(db_session, buyer, group_buy, group_buy_product, quantity=1)
    headers = auth_headers(login(client, leader_user.email, "Passw0rd1"))

    response = client.post(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/products",
        json={"product_id": str(other_product.id), "unit_price": "10.00", "max_quantity": 1},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GROUP_BUY_HAS_ORDERS"


def test_update_group_buy_product_max_quantity_below_occupied(client, db_session):
    leader_user = create_user(db_session)
    leader_profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=5)
    buyer = create_user(db_session)
    create_order_with_item(
        db_session, buyer, group_buy, group_buy_product, quantity=3, status=OrderStatus.PAID
    )
    headers = auth_headers(login(client, leader_user.email, "Passw0rd1"))

    below_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/products/{group_buy_product.id}",
        json={"max_quantity": 2},
        headers=headers,
    )
    assert below_response.status_code == 409
    assert below_response.json()["error"]["code"] == "MAX_QUANTITY_BELOW_OCCUPIED"

    price_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/products/{group_buy_product.id}",
        json={"unit_price": "999.00"},
        headers=headers,
    )
    assert price_response.status_code == 409
    assert price_response.json()["error"]["code"] == "GROUP_BUY_FIELDS_FROZEN"

    ok_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/products/{group_buy_product.id}",
        json={"max_quantity": 10},
        headers=headers,
    )
    assert ok_response.status_code == 200


def test_close_group_buy_then_cannot_close_again(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id))
    group_buy_id = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]["id"]

    close_response = client.post(
        f"/api/v1/group-leader/group-buys/{group_buy_id}/close", headers=headers
    )
    assert close_response.status_code == 200
    assert close_response.json()["data"]["status"] == "closed"

    second_response = client.post(
        f"/api/v1/group-leader/group-buys/{group_buy_id}/close", headers=headers
    )
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "GROUP_BUY_ALREADY_CLOSED"
