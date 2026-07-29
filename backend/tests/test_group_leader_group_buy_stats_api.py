"""第 6 批後端：開團統計聚合、輪次編號、儀表板目前開團與商品訂購總覽（圖 20–22）。

統計基準依使用者 2026-07-29 裁決：訂單數與訂購件數一律排除已取消／已拒絕，
與庫存佔用量同一套基準；has_orders 則沿用 Business Rules §16.1 的「任何紀錄」。
"""

from datetime import datetime, timedelta, timezone

from app.models.enums import GroupBuyStatus, OrderStatus
from app.models.order import OrderItem
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


def _leader(client, db_session):
    leader_user = create_user(db_session)
    profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    token = login(client, leader_user.email, "Passw0rd1")
    return profile, auth_headers(token)


def _in_days(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _two_rounds(db_session, profile, activity):
    """同一活動的兩輪開團。同時只能有一個 open，因此第一團先結單。

    created_at 必須明確指定：它平常由 server_default now() 產生，而 PostgreSQL 的
    now() 在同一交易內是固定值，測試整包跑在一個交易裡會讓兩團的建立時間一模一樣，
    輪次順序就落到 UUID tie-break 上而變成隨機。
    """
    first = create_group_buy(
        db_session,
        profile,
        activity,
        created_at=_in_days(-2),
        status=GroupBuyStatus.CLOSED,
        closed_at=_in_days(-1),
    )
    second = create_group_buy(db_session, profile, activity, created_at=_in_days(-1))
    return first, second


def test_my_group_buys_returns_round_number_and_stats(client, db_session):
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    first, second = _two_rounds(db_session, profile, activity)
    product = create_product(db_session, activity=activity)
    group_buy_product = create_group_buy_product(db_session, second, product)
    member = create_user(db_session)
    create_order_with_item(db_session, member, second, group_buy_product, 2)
    create_order_with_item(
        db_session, member, second, group_buy_product, 1, status=OrderStatus.PENDING_CONFIRMATION
    )
    create_order_with_item(
        db_session, member, second, group_buy_product, 4, status=OrderStatus.PENDING_PAYMENT
    )
    create_order_with_item(
        db_session, member, second, group_buy_product, 5, status=OrderStatus.CANCELLED
    )

    response = client.get("/api/v1/group-leader/group-buys", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {"total": 2, "open": 1, "closed": 1}

    items = {item["id"]: item for item in body["data"]}
    assert items[str(first.id)]["round_number"] == 1

    latest = items[str(second.id)]
    assert latest["round_number"] == 2
    # 已取消的那張（5 件）不計入訂單數與訂購件數
    assert latest["order_count"] == 3
    assert latest["ordered_quantity"] == 7
    # 待處理＝待確認＋待付款，已付款那張不算
    assert latest["pending_order_count"] == 2
    # has_orders 是欄位凍結判斷，含已取消紀錄，與上面兩項基準刻意不同
    assert latest["has_orders"] is True
    assert latest["activity"]["image_url"] == activity.image_url


def test_round_number_survives_status_filter(client, db_session):
    """篩選 open 時第二團仍須是「第 2 團」。

    視窗函式在 WHERE 之後計算，若排名與篩選寫在同一層，已結單的第一團會被排除在
    排名之外，第二團就會變成 1，畫面上出現兩個「第一團」。
    """
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    _first, second = _two_rounds(db_session, profile, activity)

    response = client.get("/api/v1/group-leader/group-buys?status=open", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [item["id"] for item in data] == [str(second.id)]
    assert data[0]["round_number"] == 2


def test_round_number_is_scoped_per_leader(client, db_session):
    """別的團主在同一活動開過團，不影響自己的輪次編號。"""
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    create_group_buy(
        db_session, create_group_leader_profile(db_session), activity, created_at=_in_days(-2)
    )
    create_group_buy(db_session, profile, activity, created_at=_in_days(-1))

    response = client.get("/api/v1/group-leader/group-buys", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["round_number"] == 1


def test_my_group_buys_sort_by_created_at(client, db_session):
    """圖 21 排序下拉：依開團建立時間新→舊（預設）或舊→新。

    參考圖寫「活動時間」，但 activity 沒有起訖日期欄位，改以建立時間排序。
    """
    profile, headers = _leader(client, db_session)
    older = create_group_buy(
        db_session, profile, create_activity(db_session), created_at=_in_days(-5)
    )
    newer = create_group_buy(
        db_session, profile, create_activity(db_session), created_at=_in_days(-1)
    )

    default_order = client.get("/api/v1/group-leader/group-buys", headers=headers)
    assert [item["id"] for item in default_order.json()["data"]] == [str(newer.id), str(older.id)]

    ascending = client.get(
        "/api/v1/group-leader/group-buys?sort=created_asc", headers=headers
    )
    assert [item["id"] for item in ascending.json()["data"]] == [str(older.id), str(newer.id)]


def test_my_group_buys_keyword_matches_activity_name(client, db_session):
    """搜尋框比對活動名稱——開團沒有名稱欄位，可搜的只有活動名稱。"""
    profile, headers = _leader(client, db_session)
    wanted = create_activity(db_session, name="潮聲信籤紀念組")
    create_group_buy(db_session, profile, wanted)
    create_group_buy(db_session, profile, create_activity(db_session, name="月夜茶會週邊"))

    response = client.get("/api/v1/group-leader/group-buys?keyword=潮聲", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["activity"]["name"] for item in body["data"]] == ["潮聲信籤紀念組"]
    # 統計卡是切換篩選的入口，不隨 keyword 變動
    assert body["summary"]["total"] == 2


def test_dashboard_upcoming_deadline_card_and_activity_grouping(client, db_session):
    profile, headers = _leader(client, db_session)
    activity_soon = create_activity(db_session)
    activity_later = create_activity(db_session)
    create_group_buy(db_session, profile, activity_soon, deadline_at=_in_days(1))
    create_group_buy(db_session, profile, activity_later, deadline_at=_in_days(10))

    response = client.get("/api/v1/group-leader/dashboard", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    cards = {card["key"]: card for card in body["cards"]}
    assert cards["upcoming_deadline_group_buys"]["count"] == 1
    assert cards["upcoming_deadline_group_buys"]["label"] == "即將截止（3 天內）"
    assert cards["open_group_buys"]["count"] == 2

    groups = body["current_group_buys"]
    assert len(groups) == 2
    # 最早截止的活動排前面
    assert groups[0]["activity_id"] == str(activity_soon.id)
    assert groups[0]["group_buys"][0]["is_upcoming_deadline"] is True
    assert groups[1]["group_buys"][0]["is_upcoming_deadline"] is False


def test_dashboard_excludes_closed_group_buys_from_current(client, db_session):
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    create_group_buy(
        db_session,
        profile,
        activity,
        status=GroupBuyStatus.CLOSED,
        closed_at=datetime.now(timezone.utc),
    )

    response = client.get("/api/v1/group-leader/dashboard", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["current_group_buys"] == []
    cards = {card["key"]: card for card in body["cards"]}
    assert cards["open_group_buys"]["count"] == 0
    assert cards["upcoming_deadline_group_buys"]["count"] == 0


def test_open_group_buys_endpoint_lists_only_open(client, db_session):
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    _first, second = _two_rounds(db_session, profile, activity)

    response = client.get("/api/v1/group-leader/group-buys/open", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [item["id"] for item in data] == [str(second.id)]
    assert data[0]["round_number"] == 2


def test_product_orders_overview(client, db_session):
    profile, headers = _leader(client, db_session)
    activity = create_activity(db_session)
    group_buy = create_group_buy(db_session, profile, activity)
    ordered_a = create_group_buy_product(
        db_session, group_buy, create_product(db_session, activity=activity)
    )
    ordered_b = create_group_buy_product(
        db_session, group_buy, create_product(db_session, activity=activity)
    )
    untouched = create_group_buy_product(
        db_session, group_buy, create_product(db_session, activity=activity)
    )

    member_one = create_user(db_session)
    member_two = create_user(db_session)
    # 明細依訂單建立時間排序（先喊先得），時間必須明確指定才不會變成 UUID 抽籤
    order = create_order_with_item(
        db_session, member_one, group_buy, ordered_a, 2, created_at=_in_days(-3)
    )
    # 同一張訂單再訂第二項商品：總訂單數不可因此變成兩筆
    db_session.add(
        OrderItem(
            order_id=order.id,
            group_buy_product_id=ordered_b.id,
            product_name_snapshot="商品快照",
            image_url_snapshot="/uploads/product/sample.webp",
            unit_price=ordered_b.unit_price,
            quantity=1,
            subtotal=ordered_b.unit_price * 1,
        )
    )
    db_session.commit()
    create_order_with_item(
        db_session, member_two, group_buy, ordered_a, 3, created_at=_in_days(-2)
    )
    create_order_with_item(
        db_session,
        member_one,
        group_buy,
        ordered_a,
        5,
        status=OrderStatus.CANCELLED,
        created_at=_in_days(-1),
    )

    response = client.get(
        f"/api/v1/group-leader/group-buys/{group_buy.id}/product-orders", headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["round_number"] == 1
    assert body["activity"]["name"] == activity.name
    # 兩張有效訂單（跨兩商品的那張只算一次），已取消的不算
    assert body["total_order_count"] == 2
    assert body["total_ordered_quantity"] == 6

    groups = {group["group_buy_product_id"]: group for group in body["products"]}
    assert groups[str(ordered_a.id)]["total_quantity"] == 5
    assert groups[str(ordered_a.id)]["member_count"] == 2
    assert len(groups[str(ordered_a.id)]["items"]) == 2
    assert groups[str(ordered_b.id)]["total_quantity"] == 1
    assert groups[str(ordered_b.id)]["member_count"] == 1
    # 沒人訂的商品仍要出現，否則團主會以為資料漏了
    assert groups[str(untouched.id)]["total_quantity"] == 0
    assert groups[str(untouched.id)]["member_count"] == 0
    assert groups[str(untouched.id)]["items"] == []

    # 明細依先喊先得排序
    assert [item["nickname"] for item in groups[str(ordered_a.id)]["items"]] == [
        member_one.nickname,
        member_two.nickname,
    ]
    first_item = groups[str(ordered_a.id)]["items"][0]
    assert first_item["order_number"] == order.order_number
    assert first_item["order_status"] == "paid"
    assert first_item["quantity"] == 2


def test_product_orders_rejects_other_leaders_group_buy(client, db_session):
    _profile, headers = _leader(client, db_session)
    other_group_buy = create_group_buy(db_session, create_group_leader_profile(db_session))

    response = client.get(
        f"/api/v1/group-leader/group-buys/{other_group_buy.id}/product-orders", headers=headers
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_BUY_NOT_OWNED"
