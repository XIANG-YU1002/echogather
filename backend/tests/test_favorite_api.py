from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.favorite import ProductFavorite
from tests.factories import create_activity, create_product
from tests.utils import auth_headers, register_and_login


def test_add_and_list_favorite(client, db_session):
    activity = create_activity(db_session)
    product = create_product(
        db_session,
        activity=activity,
        official_price=Decimal("680"),
        official_currency="TWD",
    )
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    add_response = client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    assert add_response.status_code == 201
    assert add_response.json()["data"] == {"product_id": str(product.id), "is_favorited": True}

    list_response = client.get("/api/v1/favorites/products", headers=headers)
    assert list_response.status_code == 200
    data = list_response.json()["data"]
    assert len(data) == 1
    assert data[0]["product"]["id"] == str(product.id)
    # 依圖 11：卡片要顯示官方原價
    assert data[0]["product"]["official_price"] == "680.00"
    assert data[0]["product"]["official_currency"] == "TWD"


def test_list_favorite_without_official_price(client, db_session):
    """未定價商品的價格欄位為 null，前端顯示「未提供官方原價」。"""
    product = create_product(db_session)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    data = client.get("/api/v1/favorites/products", headers=headers).json()["data"]
    assert data[0]["product"]["official_price"] is None
    assert data[0]["product"]["official_currency"] is None


def test_add_favorite_idempotent(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    second = client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    assert second.status_code == 201

    list_response = client.get("/api/v1/favorites/products", headers=headers)
    assert len(list_response.json()["data"]) == 1


def test_favorite_inactive_product_still_listed(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity, is_active=False)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    list_response = client.get("/api/v1/favorites/products", headers=headers)
    assert list_response.json()["data"][0]["product"]["is_active"] is False


def test_remove_favorite(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    remove_response = client.delete(f"/api/v1/favorites/products/{product.id}", headers=headers)
    assert remove_response.status_code == 204

    list_response = client.get("/api/v1/favorites/products", headers=headers)
    assert list_response.json()["data"] == []


def test_remove_favorite_idempotent_when_not_favorited(client, db_session):
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    _, token = register_and_login(client, db_session)

    response = client.delete(
        f"/api/v1/favorites/products/{product.id}", headers=auth_headers(token)
    )
    assert response.status_code == 204


def test_favorite_requires_authentication(client, db_session):
    product = create_product(db_session)
    response = client.post(f"/api/v1/favorites/products/{product.id}")
    assert response.status_code == 401


def _favorited_names(client, headers, sort: str) -> list[str]:
    response = client.get(f"/api/v1/favorites/products?sort={sort}", headers=headers)
    assert response.status_code == 200
    return [item["product"]["name"] for item in response.json()["data"]]


def _stamp_favorite_times(db_session, products) -> None:
    """依傳入順序給收藏遞增的 created_at。

    整個測試跑在單一交易內，而 created_at 的 server_default 是 PostgreSQL 的
    now()——它回傳「交易開始時間」，所以同一測試建立的收藏時間戳會完全相同，
    排序會退回次要鍵（隨機 UUID）。正式環境每次收藏都是獨立交易故無此問題，
    這裡明確指定時間，才測得到「依收藏時間」排序本身。
    """
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    for index, product in enumerate(products):
        favorite = db_session.execute(
            select(ProductFavorite).where(ProductFavorite.product_id == product.id)
        ).scalar_one()
        favorite.created_at = base + timedelta(days=index)
    db_session.flush()


def test_list_favorites_sort_options(client, db_session):
    """依圖 11 的排序下拉：收藏時間新／舊、商品名稱、價格高／低。"""
    activity = create_activity(db_session)
    cheap = create_product(
        db_session,
        activity=activity,
        name="AAA 便宜",
        official_price=Decimal("100"),
        official_currency="TWD",
    )
    pricey = create_product(
        db_session,
        activity=activity,
        name="BBB 昂貴",
        official_price=Decimal("900"),
        official_currency="TWD",
    )
    # 未定價商品在價格排序時一律排最後（NULLS LAST）
    unpriced = create_product(db_session, activity=activity, name="CCC 未定價")

    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)
    ordered = (cheap, pricey, unpriced)
    for product in ordered:
        client.post(f"/api/v1/favorites/products/{product.id}", headers=headers)
    _stamp_favorite_times(db_session, ordered)

    newest_first = ["CCC 未定價", "BBB 昂貴", "AAA 便宜"]
    oldest_first = ["AAA 便宜", "BBB 昂貴", "CCC 未定價"]

    assert _favorited_names(client, headers, "created_desc") == newest_first
    assert _favorited_names(client, headers, "created_asc") == oldest_first
    assert _favorited_names(client, headers, "name_asc") == oldest_first
    assert _favorited_names(client, headers, "price_asc") == oldest_first
    assert _favorited_names(client, headers, "price_desc") == [
        "BBB 昂貴",
        "AAA 便宜",
        "CCC 未定價",
    ]


def test_list_favorites_default_sort_is_created_desc(client, db_session):
    activity = create_activity(db_session)
    first = create_product(db_session, activity=activity)
    second = create_product(db_session, activity=activity)

    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)
    client.post(f"/api/v1/favorites/products/{first.id}", headers=headers)
    client.post(f"/api/v1/favorites/products/{second.id}", headers=headers)
    _stamp_favorite_times(db_session, (first, second))

    data = client.get("/api/v1/favorites/products", headers=headers).json()["data"]
    assert [item["product"]["id"] for item in data] == [str(second.id), str(first.id)]


def test_list_favorites_invalid_sort_rejected(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get(
        "/api/v1/favorites/products?sort=not_a_sort", headers=auth_headers(token)
    )
    assert response.status_code == 422
