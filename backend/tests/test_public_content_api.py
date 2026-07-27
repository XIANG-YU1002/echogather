import uuid
from datetime import datetime, timedelta, timezone

from app.models.enums import ActivityStatus, GroupBuyStatus, OrderStatus
from tests.factories import (
    create_activity,
    create_character,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_order_with_item,
    create_product,
    link_product_character,
)


def test_list_activities_default_open(client, db_session):
    open_activity = create_activity(db_session, status=ActivityStatus.OPEN)
    ended_activity = create_activity(db_session, status=ActivityStatus.ENDED)

    response = client.get("/api/v1/activities", params={"status": "open"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert str(open_activity.id) in ids
    assert str(ended_activity.id) not in ids


def test_get_activity_detail_not_found(client):
    response = client.get(f"/api/v1/activities/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_get_activity_products_only_active(client, db_session):
    activity = create_activity(db_session)
    active_product = create_product(db_session, activity=activity, is_active=True)
    inactive_product = create_product(db_session, activity=activity, is_active=False)

    response = client.get(f"/api/v1/activities/{activity.id}/products")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert str(active_product.id) in ids
    assert str(inactive_product.id) not in ids


def test_get_product_detail_includes_characters_and_activity(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    character = create_character(db_session)
    link_product_character(db_session, product, character)

    response = client.get(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["activity"]["id"] == str(activity.id)
    assert [c["id"] for c in data["characters"]] == [str(character.id)]
    assert data["is_favorited"] is False


def test_get_product_detail_not_found(client):
    response = client.get(f"/api/v1/products/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_product_group_buys_available_quantity_and_filter(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(
        db_session, group_buy, product, max_quantity=5, unit_price="200.00"
    )

    response = client.get(f"/api/v1/products/{product.id}/group-buys")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    item = data[0]
    assert item["group_buy_product_id"] == str(group_buy_product.id)
    assert item["available_quantity"] == 5
    assert item["effective_status"] == "open"
    assert item["is_available"] is True
    assert item["unit_price"] == "200.00"


def test_product_group_buys_occupied_quantity_reduces_availability(client, db_session):
    from tests.factories import create_user

    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    buyer = create_user(db_session)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    group_buy_product = create_group_buy_product(
        db_session, group_buy, product, max_quantity=3, unit_price="150.00"
    )
    create_order_with_item(
        db_session, buyer, group_buy, group_buy_product, quantity=3, status=OrderStatus.PAID
    )

    response = client.get(f"/api/v1/products/{product.id}/group-buys")
    data = response.json()["data"][0]
    assert data["available_quantity"] == 0
    assert data["effective_status"] == "full"
    assert data["is_available"] is False

    filtered = client.get(
        f"/api/v1/products/{product.id}/group-buys", params={"available_only": True}
    )
    assert filtered.json()["data"] == []


def test_product_group_buys_payment_method_filter(client, db_session):
    from app.models.enums import PaymentMethod

    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(
        db_session,
        group_leader_profile=leader_profile,
        activity=activity,
        payment_method=PaymentMethod.BANK_TRANSFER,
    )
    create_group_buy_product(db_session, group_buy, product)

    url = f"/api/v1/products/{product.id}/group-buys"

    # 未指定付款方式時不篩選
    assert len(client.get(url).json()["data"]) == 1
    # 指定為該開團的付款方式時保留
    assert len(client.get(url, params={"payment_method": "bank_transfer"}).json()["data"]) == 1
    # 指定為其他付款方式時濾除
    assert client.get(url, params={"payment_method": "cash_on_delivery"}).json()["data"] == []
    # 不合法的付款方式回 422
    assert client.get(url, params={"payment_method": "bogus"}).status_code == 422


def test_get_group_buy_detail(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    create_group_buy_product(db_session, group_buy, product)

    response = client.get(f"/api/v1/group-buys/{group_buy.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(group_buy.id)
    assert data["group_leader"]["display_name"] == leader_profile.display_name
    assert len(data["products"]) == 1
    assert data["effective_status"] == "open"


def test_get_group_buy_rules(client, db_session):
    group_buy = create_group_buy(db_session, rules="特殊團規內容")
    response = client.get(f"/api/v1/group-buys/{group_buy.id}/rules")
    assert response.status_code == 200
    assert response.json()["data"]["rules"] == "特殊團規內容"


def test_get_group_buy_not_found(client):
    response = client.get(f"/api/v1/group-buys/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_BUY_NOT_FOUND"


def test_get_group_buy_product_availability(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, activity=activity)
    group_buy_product = create_group_buy_product(db_session, group_buy, product, max_quantity=7)

    response = client.get(f"/api/v1/group-buy-products/{group_buy_product.id}/availability")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available_quantity"] == 7
    assert data["effective_status"] == "open"


def test_expired_group_buy_effective_status(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(
        db_session,
        activity=activity,
        deadline_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    create_group_buy_product(db_session, group_buy, product)

    response = client.get(f"/api/v1/group-buys/{group_buy.id}")
    assert response.json()["data"]["effective_status"] == "expired"


def test_closed_group_buy_effective_status(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(
        db_session,
        activity=activity,
        status=GroupBuyStatus.CLOSED,
        closed_at=datetime.now(timezone.utc),
    )
    create_group_buy_product(db_session, group_buy, product)

    response = client.get(f"/api/v1/group-buys/{group_buy.id}")
    assert response.json()["data"]["effective_status"] == "closed"


def test_public_group_leader_profile_requires_completed_profile(client, db_session):
    incomplete_profile = create_group_leader_profile(db_session, complete=False)

    response = client.get(f"/api/v1/group-leaders/{incomplete_profile.id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_LEADER_PROFILE_NOT_FOUND"


def test_public_group_leader_profile_success(client, db_session):
    profile = create_group_leader_profile(db_session, complete=True)

    response = client.get(f"/api/v1/group-leaders/{profile.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["display_name"] == profile.display_name
    assert data["public_contacts"]["discord"] == "leader_discord"
    assert data["statistics"] == {"group_buy_count": 0, "completed_order_count": 0}


def test_public_group_leader_group_buys_and_announcements(client, db_session):
    profile = create_group_leader_profile(db_session, complete=True)
    create_group_buy(db_session, group_leader_profile=profile)

    group_buys_response = client.get(f"/api/v1/group-leaders/{profile.id}/group-buys")
    assert group_buys_response.status_code == 200
    assert len(group_buys_response.json()["data"]) == 1

    announcements_response = client.get(f"/api/v1/group-leaders/{profile.id}/announcements")
    assert announcements_response.status_code == 200
    assert announcements_response.json()["data"] == []


def test_global_search_preview(client, db_session):
    activity = create_activity(db_session, name="今汐周邊活動")
    create_product(db_session, activity=activity, name="今汐壓克力立牌")
    create_character(db_session, name="今汐")

    response = client.get("/api/v1/search", params={"q": "今汐"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["activities"]["total_count"] >= 1
    assert data["products"]["total_count"] >= 1
    assert data["characters"]["total_count"] >= 1


def test_global_search_requires_query(client):
    response = client.get("/api/v1/search", params={"q": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SEARCH_QUERY_REQUIRED"


def test_search_products_only_active(client, db_session):
    activity = create_activity(db_session)
    active = create_product(db_session, activity=activity, name="搜尋測試上架商品", is_active=True)
    inactive = create_product(
        db_session, activity=activity, name="搜尋測試下架商品", is_active=False
    )

    response = client.get("/api/v1/search/products", params={"q": "搜尋測試"})

    ids = [item["id"] for item in response.json()["data"]]
    assert str(active.id) in ids
    assert str(inactive.id) not in ids
