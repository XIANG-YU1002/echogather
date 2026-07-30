from datetime import datetime, timedelta, timezone

from app.models.enums import OrderStatus
from app.models.group_buy import GroupBuyProductCharacter
from tests.factories import (
    create_activity,
    create_character,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_order_with_item,
    create_product,
    create_user,
    link_product_character,
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


def test_update_group_buy_deadline_can_be_moved_earlier(client, db_session):
    """依 Business Rules §16.5：截止時間可延長也可縮短，只是不得改到過去。

    實務上因數量不足而提早收單的情況比延後更常見，所以特別留一個回歸測試。
    """
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)
    payload = _base_payload(product.id, activity_id=str(activity.id), deadline_at=_future_deadline(30))
    group_buy_id = client.post(
        "/api/v1/group-leader/group-buys", json=payload, headers=headers
    ).json()["data"]["id"]

    earlier = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy_id}",
        json={"deadline_at": _future_deadline(2)},
        headers=headers,
    )
    assert earlier.status_code == 200, earlier.text
    assert earlier.json()["data"]["deadline_at"].startswith(_future_deadline(2)[:10])

    # 改到過去仍要被拒絕
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rejected = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy_id}",
        json={"deadline_at": past},
        headers=headers,
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"


def test_group_buy_contact_must_come_from_leader_profile(client, db_session):
    """開團的主要聯絡方式必須取自團主資料已設定的公開聯絡方式。

    依使用者 2026-07-29 裁決：不在開團另外輸入，避免同一位團主在不同開團
    留下不一致或過期的聯絡資訊。
    """
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    # 團主資料只設定 Discord（factories 預設），沒有 Facebook
    headers = _leader(client, db_session)

    not_set = client.post(
        "/api/v1/group-leader/group-buys",
        json=_base_payload(
            product.id,
            activity_id=str(activity.id),
            contact_platform="facebook",
            contact_value="https://www.facebook.com/moon.group",
        ),
        headers=headers,
    )
    assert not_set.status_code == 422
    assert not_set.json()["error"]["code"] == "CONTACT_NOT_SET_IN_PROFILE"

    mismatch = client.post(
        "/api/v1/group-leader/group-buys",
        json=_base_payload(
            product.id,
            activity_id=str(activity.id),
            contact_platform="discord",
            contact_value="someone_else",
        ),
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "CONTACT_VALUE_MISMATCH"

    # 與團主資料一致才能建立（factories 的 discord_contact 為 leader_discord）
    created = client.post(
        "/api/v1/group-leader/group-buys",
        json=_base_payload(product.id, activity_id=str(activity.id)),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["contact_value"] == "leader_discord"


def test_group_buy_facebook_contact_must_be_url(client, db_session):
    """團主資料的 Facebook 必須是連結，開團沿用時自然也是連結。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(
        client, db_session, facebook_url="https://www.facebook.com/moon.group"
    )

    created = client.post(
        "/api/v1/group-leader/group-buys",
        json=_base_payload(
            product.id,
            activity_id=str(activity.id),
            contact_platform="facebook",
            contact_value="https://www.facebook.com/moon.group",
        ),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["contact_value"] == "https://www.facebook.com/moon.group"

    # 團主資料本身不接受只填帳號名稱
    rejected = client.patch(
        "/api/v1/group-leader/profile",
        json={"facebook_url": "my_fb_name"},
        headers=headers,
    )
    assert rejected.status_code == 422
    assert "facebook_url" in rejected.json()["error"]["details"]["fields"]


def test_update_group_buy_settings_frozen_after_orders(client, db_session):
    leader_user = create_user(db_session)
    # 團主同時設定 Discord 與 LINE，才能測「有訂單後仍可換主要聯絡方式」
    leader_profile = create_group_leader_profile(
        db_session, user=leader_user, complete=True, line_contact="leader_line"
    )
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

    # 只送平台時後端自動採用團主資料該平台的值
    allowed_response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}",
        json={"contact_platform": "line"},
        headers=headers,
    )
    assert allowed_response.status_code == 200, allowed_response.text
    assert allowed_response.json()["data"]["contact_platform"] == "line"
    assert allowed_response.json()["data"]["contact_value"] == "leader_line"
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


# ---------------------------------------------------------------------------
# 每角色接單上限（Business Rules §20.4）
# 單商品多角色時，團主可把不接的角色設 0；商品層級與單一角色仍須至少 1。
# ---------------------------------------------------------------------------


def _multi_character_product(db_session, activity, count=2):
    """建立一個掛了 count 個角色的商品，回傳 (product, characters)。"""
    product = create_product(db_session, activity=activity)
    characters = [create_character(db_session) for _ in range(count)]
    for character in characters:
        link_product_character(db_session, product, character)
    return product, characters


def _character_payload(product, activity, quantities):
    """quantities 依角色順序給定每角色上限。"""
    return _base_payload(
        product.id,
        activity_id=str(activity.id),
        products=[
            {
                "product_id": str(product.id),
                "unit_price": "100.00",
                # 商品層級送總和，與後端加總後的值一致
                "max_quantity": max(sum(qty for _, qty in quantities), 1),
                "character_quantities": [
                    {"character_id": str(character.id), "max_quantity": qty}
                    for character, qty in quantities
                ],
            }
        ],
    )


def test_create_group_buy_character_quantity_zero_means_not_accepting(client, db_session):
    """某個角色設 0：開團建立成功，該角色可用量 0，商品總上限只算其他角色。"""
    activity = create_activity(db_session)
    product, characters = _multi_character_product(db_session, activity)
    headers = _leader(client, db_session)

    payload = _character_payload(product, activity, [(characters[0], 3), (characters[1], 0)])
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 201
    item = response.json()["data"]["products"][0]
    assert item["max_quantity"] == 3
    stock = {entry["name"]: entry for entry in item["character_stock"]}
    assert stock[characters[0].name]["available_quantity"] == 3
    assert stock[characters[1].name]["max_quantity"] == 0
    assert stock[characters[1].name]["available_quantity"] == 0


def test_create_group_buy_single_character_quantity_zero_rejected(client, db_session):
    """只有一個角色的商品填 0 等於整個商品不接，應該取消勾選而不是填 0。"""
    activity = create_activity(db_session)
    product, characters = _multi_character_product(db_session, activity, count=1)
    headers = _leader(client, db_session)

    payload = _character_payload(product, activity, [(characters[0], 0)])
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SINGLE_CHARACTER_QUANTITY_ZERO"


def test_create_group_buy_all_character_quantities_zero_rejected(client, db_session):
    activity = create_activity(db_session)
    product, characters = _multi_character_product(db_session, activity)
    headers = _leader(client, db_session)

    payload = _character_payload(product, activity, [(characters[0], 0), (characters[1], 0)])
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ALL_CHARACTER_QUANTITIES_ZERO"


def test_create_group_buy_product_max_quantity_zero_rejected(client, db_session):
    """商品層級的上限不放寬：勾選商品就代表要接單。"""
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    headers = _leader(client, db_session)

    payload = _base_payload(
        product.id,
        activity_id=str(activity.id),
        products=[{"product_id": str(product.id), "unit_price": "100.00", "max_quantity": 0}],
    )
    response = client.post("/api/v1/group-leader/group-buys", json=payload, headers=headers)

    assert response.status_code == 422


def test_update_character_quantity_to_zero_stops_accepting(client, db_session):
    """開團後把某角色改成 0：該角色不再可跟，其他角色不受影響。"""
    activity = create_activity(db_session)
    product, characters = _multi_character_product(db_session, activity)
    headers = _leader(client, db_session)

    created = client.post(
        "/api/v1/group-leader/group-buys",
        json=_character_payload(product, activity, [(characters[0], 4), (characters[1], 4)]),
        headers=headers,
    ).json()["data"]
    group_buy_id = created["id"]
    group_buy_product_id = created["products"][0]["id"]

    response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy_id}/products/{group_buy_product_id}",
        json={
            "character_quantities": [
                {"character_id": str(characters[0].id), "max_quantity": 4},
                {"character_id": str(characters[1].id), "max_quantity": 0},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200
    item = response.json()["data"]["products"][0]
    assert item["max_quantity"] == 4
    stock = {entry["name"]: entry for entry in item["character_stock"]}
    assert stock[characters[1].name]["max_quantity"] == 0
    assert stock[characters[0].name]["available_quantity"] == 4


def test_update_character_quantity_below_occupied_rejected(client, db_session):
    """已被訂單占用的角色不能調到占用量以下（與商品層級同一條規則）。"""
    activity = create_activity(db_session)
    product, characters = _multi_character_product(db_session, activity)
    leader_user = create_user(db_session)
    profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    token = login(client, leader_user.email, "Passw0rd1")
    headers = auth_headers(token)

    group_buy = create_group_buy(db_session, group_leader_profile=profile, activity=activity)
    group_buy_product = create_group_buy_product(
        db_session, group_buy=group_buy, product=product, max_quantity=6
    )
    db_session.add_all(
        [
            GroupBuyProductCharacter(
                group_buy_product_id=group_buy_product.id,
                character_id=characters[0].id,
                max_quantity=3,
            ),
            GroupBuyProductCharacter(
                group_buy_product_id=group_buy_product.id,
                character_id=characters[1].id,
                max_quantity=3,
            ),
        ]
    )
    db_session.commit()

    member = create_user(db_session)
    create_order_with_item(
        db_session,
        user=member,
        group_buy=group_buy,
        group_buy_product=group_buy_product,
        quantity=2,
        chosen_character=characters[0],
    )

    response = client.patch(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/products/{group_buy_product.id}",
        json={
            "character_quantities": [
                {"character_id": str(characters[0].id), "max_quantity": 0},
                {"character_id": str(characters[1].id), "max_quantity": 3},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CHARACTER_MAX_QUANTITY_BELOW_OCCUPIED"
    assert response.json()["error"]["details"]["occupied_quantity"] == 2
