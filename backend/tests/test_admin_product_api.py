import uuid

from app.models.enums import UserRole
from tests.factories import create_activity, create_character, create_product, create_user
from tests.utils import auth_headers, login

# 測試跑在與示範資料共用的 Supabase 上，角色名有不分大小寫的唯一鍵
# （uq_character_name_lower），因此一律使用隨機名稱避免與既有資料撞名。


def _unique_name(prefix: str = "測試角色") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_create_product_with_existing_and_new_character(client, db_session):
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)
    existing_name = _unique_name()
    new_name = _unique_name()
    existing_character = create_character(db_session, name=existing_name)

    response = client.post(
        "/api/v1/admin/products",
        json={
            "activity_id": str(activity.id),
            "name": "壓克力立牌",
            "official_price": "390.00",
            "primary_image_url": "/uploads/product/p.webp",
            "characters": [{"id": str(existing_character.id)}, {"new_name": new_name}],
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["official_price"] == "390.00"
    names = {c["name"] for c in data["characters"]}
    assert names == {existing_name, new_name}


def test_create_product_duplicate_name_in_activity(client, db_session):
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)
    create_product(db_session, activity=activity, name="壓克力立牌")

    response = client.post(
        "/api/v1/admin/products",
        json={
            "activity_id": str(activity.id),
            "name": "壓克力立牌",
            "primary_image_url": "/uploads/product/p.webp",
        },
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def _create_product_via_api(client, headers, activity, name, price, currency):
    return client.post(
        "/api/v1/admin/products",
        json={
            "activity_id": str(activity.id),
            "name": name,
            "official_price": price,
            "official_currency": currency,
            "primary_image_url": "/uploads/product/p.webp",
        },
        headers=headers,
    )


def test_create_product_rejects_currency_different_from_activity(client, db_session):
    """同一活動的商品幣別必須一致（使用者 2026-07-30 規則）。"""
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)

    first = _create_product_via_api(client, headers, activity, "立牌", "390.00", "TWD")
    assert first.status_code == 201

    second = _create_product_via_api(client, headers, activity, "吊飾", "1500.00", "JPY")
    assert second.status_code == 409
    body = second.json()["error"]
    assert body["code"] == "ACTIVITY_CURRENCY_MISMATCH"
    # 訊息要告訴管理員該活動目前用的是哪一種幣別，否則不知道要改成什麼
    assert body["details"]["activity_currency"] == "TWD"


def test_create_product_allows_same_currency_and_unpriced(client, db_session):
    """同幣別可以繼續新增；沒有標價的商品不受幣別限制。"""
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)

    assert _create_product_via_api(client, headers, activity, "立牌", "390.00", "TWD").status_code == 201
    assert _create_product_via_api(client, headers, activity, "色紙", "250.00", "TWD").status_code == 201

    # 未填官方價 → official_currency 為 NULL，不構成幣別衝突
    unpriced = client.post(
        "/api/v1/admin/products",
        json={
            "activity_id": str(activity.id),
            "name": "無標價商品",
            "primary_image_url": "/uploads/product/p.webp",
        },
        headers=headers,
    )
    assert unpriced.status_code == 201
    assert unpriced.json()["data"]["official_currency"] is None


def test_create_product_currency_isolated_per_activity(client, db_session):
    """限制只在同一活動內；不同活動可以各用不同幣別。"""
    headers = _admin_headers(client, db_session)
    activity_a = create_activity(db_session)
    activity_b = create_activity(db_session)

    assert _create_product_via_api(client, headers, activity_a, "立牌", "390.00", "TWD").status_code == 201
    assert _create_product_via_api(client, headers, activity_b, "立牌", "1500.00", "JPY").status_code == 201


def test_update_product_currency_validated_excluding_itself(client, db_session):
    """改幣別同樣受限；但排除自己，否則唯一的標價商品會被自己的舊值鎖死。"""
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)

    created = _create_product_via_api(client, headers, activity, "立牌", "390.00", "TWD")
    product_id = created.json()["data"]["id"]

    # 全活動只有這一項標價商品 → 改成別的幣別應該可以
    changed = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={"official_price": "1500.00", "official_currency": "JPY"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["official_currency"] == "JPY"

    # 再加一項 JPY 之後，就不能把其中一項改成 TWD
    assert _create_product_via_api(client, headers, activity, "吊飾", "800.00", "JPY").status_code == 201
    rejected = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={"official_price": "390.00", "official_currency": "TWD"},
        headers=headers,
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "ACTIVITY_CURRENCY_MISMATCH"


def test_activity_detail_exposes_product_currency(client, db_session):
    """前端靠這個欄位鎖定幣別下拉，避免送出才被擋。"""
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)

    before = client.get(f"/api/v1/admin/activities/{activity.id}", headers=headers)
    assert before.json()["data"]["product_currency"] is None

    _create_product_via_api(client, headers, activity, "立牌", "390.00", "JPY")

    after = client.get(f"/api/v1/admin/activities/{activity.id}", headers=headers)
    assert after.json()["data"]["product_currency"] == "JPY"


def test_create_product_new_character_reuses_existing_case_insensitive(client, db_session):
    """以 new_name 送出已存在的角色（大小寫不同）時應重用既有角色，不建立第二筆。"""
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)
    suffix = uuid.uuid4().hex[:8]
    existing_name = f"Jinhsi{suffix}"
    create_character(db_session, name=existing_name)

    response = client.post(
        "/api/v1/admin/products",
        json={
            "activity_id": str(activity.id),
            "name": "商品A",
            "primary_image_url": "/uploads/product/p.webp",
            "characters": [{"new_name": f"JINHSI{suffix.upper()}"}],
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert len(response.json()["data"]["characters"]) == 1

    # 以隨機片段查詢，確認沒有因大小寫差異多建立一筆角色
    suggestions = client.get(
        "/api/v1/admin/characters/suggestions", params={"q": suffix}, headers=headers
    ).json()["data"]
    assert len(suggestions) == 1
    assert suggestions[0]["name"] == existing_name
    assert suggestions[0]["related_product_count"] == 1


def test_deactivate_and_reactivate_product(client, db_session):
    headers = _admin_headers(client, db_session)
    product = create_product(db_session)

    deactivate_response = client.post(
        f"/api/v1/admin/products/{product.id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["is_active"] is False

    repeat_response = client.post(
        f"/api/v1/admin/products/{product.id}/deactivate", headers=headers
    )
    assert repeat_response.status_code == 409
    assert repeat_response.json()["error"]["code"] == "PRODUCT_ALREADY_INACTIVE"

    reactivate_response = client.post(
        f"/api/v1/admin/products/{product.id}/reactivate", headers=headers
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["data"]["is_active"] is True


def test_update_product_replaces_characters(client, db_session):
    headers = _admin_headers(client, db_session)
    product = create_product(db_session)
    old_character = create_character(db_session, name="舊角色")
    from tests.factories import link_product_character

    link_product_character(db_session, product, old_character)

    response = client.patch(
        f"/api/v1/admin/products/{product.id}",
        json={"characters": [{"new_name": "新角色"}]},
        headers=headers,
    )
    assert response.status_code == 200
    names = {c["name"] for c in response.json()["data"]["characters"]}
    assert names == {"新角色"}


def test_update_product_omitting_characters_keeps_existing(client, db_session):
    headers = _admin_headers(client, db_session)
    product = create_product(db_session)
    character = create_character(db_session, name="保留角色")
    from tests.factories import link_product_character

    link_product_character(db_session, product, character)

    response = client.patch(
        f"/api/v1/admin/products/{product.id}", json={"name": "改名商品"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "改名商品"
    assert [c["name"] for c in response.json()["data"]["characters"]] == ["保留角色"]


def test_add_update_delete_and_reorder_images(client, db_session):
    headers = _admin_headers(client, db_session)
    product = create_product(db_session)

    add1 = client.post(
        f"/api/v1/admin/products/{product.id}/images",
        json={"image_url": "/uploads/product/1.webp"},
        headers=headers,
    )
    add2 = client.post(
        f"/api/v1/admin/products/{product.id}/images",
        json={"image_url": "/uploads/product/2.webp"},
        headers=headers,
    )
    assert add1.status_code == 201
    assert add2.status_code == 201
    images = add2.json()["data"]["images"]
    assert [img["sort_order"] for img in images] == [0, 1]
    image1_id, image2_id = images[0]["id"], images[1]["id"]

    update_response = client.patch(
        f"/api/v1/admin/products/{product.id}/images/{image1_id}",
        json={"image_url": "/uploads/product/1-updated.webp"},
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_image = next(
        i for i in update_response.json()["data"]["images"] if i["id"] == image1_id
    )
    assert updated_image["image_url"] == "/uploads/product/1-updated.webp"

    reorder_response = client.patch(
        f"/api/v1/admin/products/{product.id}/images/reorder",
        json={"ordered_image_ids": [image2_id, image1_id]},
        headers=headers,
    )
    assert reorder_response.status_code == 200
    reordered = reorder_response.json()["data"]["images"]
    assert reordered[0]["id"] == image2_id
    assert reordered[0]["sort_order"] == 0
    assert reordered[1]["id"] == image1_id
    assert reordered[1]["sort_order"] == 1

    delete_response = client.delete(
        f"/api/v1/admin/products/{product.id}/images/{image1_id}", headers=headers
    )
    assert delete_response.status_code == 200
    assert len(delete_response.json()["data"]["images"]) == 1


def test_reorder_images_incomplete_list_rejected(client, db_session):
    headers = _admin_headers(client, db_session)
    product = create_product(db_session)
    add_response = client.post(
        f"/api/v1/admin/products/{product.id}/images",
        json={"image_url": "/uploads/product/1.webp"},
        headers=headers,
    )
    client.post(
        f"/api/v1/admin/products/{product.id}/images",
        json={"image_url": "/uploads/product/2.webp"},
        headers=headers,
    )
    image1_id = add_response.json()["data"]["images"][0]["id"]

    response = client.patch(
        f"/api/v1/admin/products/{product.id}/images/reorder",
        json={"ordered_image_ids": [image1_id]},
        headers=headers,
    )
    assert response.status_code == 422
