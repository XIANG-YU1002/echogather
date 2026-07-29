"""訂單合併（使用者 2026-07-29 需求）。

規則：同會員同開團、狀態限待確認／待付款／已付款、保留哪張由團主選、
同商品同角色數量相加、合併後狀態取進度最慢者、已付款部分記入 paid_amount、
被併入的訂單標記為已取消。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import CancellationStatus, OrderStatus
from app.models.order import CancellationRequest, OrderItem
from tests.factories import (
    create_activity,
    create_character,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_order_with_item,
    create_product,
    create_user,
)
from tests.utils import auth_headers, login


def _in_days(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _setup(db_session, client):
    leader_user = create_user(db_session)
    profile = create_group_leader_profile(db_session, user=leader_user, complete=True)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    group_buy = create_group_buy(db_session, profile, activity)
    group_buy_product = create_group_buy_product(
        db_session, group_buy, product, max_quantity=100
    )
    member = create_user(db_session)
    headers = auth_headers(login(client, leader_user.email, "Passw0rd1"))
    return {
        "headers": headers,
        "group_buy": group_buy,
        "group_buy_product": group_buy_product,
        "member": member,
        "activity": activity,
        "profile": profile,
    }


def test_merge_two_pending_orders_sums_same_product(client, db_session):
    """同商品同角色的明細數量相加，而不是變成兩列。"""
    ctx = _setup(db_session, client)
    older = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    newer = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        3,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{newer.id}/merge",
        json={"merge_with_order_ids": [str(older.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    # keep=oldest → 保留較早那張的編號
    assert data["order_number"] == older.order_number
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5
    assert Decimal(data["product_total_amount"]) == Decimal("500.00")
    assert Decimal(data["paid_amount"]) == Decimal("0.00")
    # 合併代表團主已確認這些訂單，待確認直接進到待付款
    assert data["status"] == "pending_payment"

    # 被併入的訂單標記為已取消
    db_session.expire_all()
    detail = client.get(
        f"/api/v1/group-leader/orders/{newer.id}", headers=ctx["headers"]
    ).json()["data"]
    assert detail["status"] == "cancelled"


def test_merge_keep_newest_uses_newest_order_number(client, db_session):
    ctx = _setup(db_session, client)
    older = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    newer = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{older.id}/merge",
        json={"merge_with_order_ids": [str(newer.id)], "keep": "newest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["order_number"] == newer.order_number


def test_merge_paid_order_records_paid_amount_and_pending_payment(client, db_session):
    """已付款那筆的錢已收，記入 paid_amount；合併後狀態為待付款（部分已付款）。"""
    ctx = _setup(db_session, client)
    pending = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    paid = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PAID,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{pending.id}/merge",
        json={"merge_with_order_ids": [str(paid.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    # 不是全部已付款 → 待付款，未收的部分由 總額－已收 表達
    assert data["status"] == "pending_payment"
    assert Decimal(data["product_total_amount"]) == Decimal("300.00")
    # 已付款那筆的 100 元已收
    assert Decimal(data["paid_amount"]) == Decimal("100.00")


def test_merge_all_paid_orders_stays_paid_with_full_amount(client, db_session):
    """全部都是已付款時不該退回待付款，且已收金額等於總額。"""
    ctx = _setup(db_session, client)
    first = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PAID,
        created_at=_in_days(-3),
    )
    second = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PAID,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{first.id}/merge",
        json={"merge_with_order_ids": [str(second.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "paid"
    assert Decimal(data["product_total_amount"]) == Decimal("300.00")
    assert Decimal(data["paid_amount"]) == Decimal("300.00")


def test_mark_paid_after_merge_fills_paid_amount(client, db_session):
    """合併後標記已付款時，已收金額要補到全額，否則會出現已付款卻仍有待收的矛盾。"""
    ctx = _setup(db_session, client)
    pending = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    paid = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PAID,
        created_at=_in_days(-1),
    )

    merged = client.post(
        f"/api/v1/group-leader/orders/{pending.id}/merge",
        json={"merge_with_order_ids": [str(paid.id)], "keep": "oldest"},
        headers=ctx["headers"],
    ).json()["data"]
    assert merged["status"] == "pending_payment"
    assert Decimal(merged["paid_amount"]) == Decimal("100.00")

    response = client.post(
        f"/api/v1/group-leader/orders/{merged['id']}/mark-paid", headers=ctx["headers"]
    )
    assert response.status_code == 200, response.text

    detail = client.get(
        f"/api/v1/group-leader/orders/{merged['id']}", headers=ctx["headers"]
    ).json()["data"]
    assert detail["status"] == "paid"
    assert Decimal(detail["paid_amount"]) == Decimal(detail["product_total_amount"])


def test_merge_keeps_different_characters_as_separate_items(client, db_session):
    """同商品但角色不同時必須保持兩列，不可相加。

    order_item 的唯一約束是 (order, product, character)，相加的判斷也必須含角色，
    否則會把不同角色的訂購量併成一筆而出錯貨。
    """
    ctx = _setup(db_session, client)
    character_a = create_character(db_session)
    character_b = create_character(db_session)

    first = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    second = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )
    for order, character in ((first, character_a), (second, character_b)):
        item = db_session.query(OrderItem).filter(OrderItem.order_id == order.id).one()
        item.chosen_character_id = character.id
        item.chosen_character_name_snapshot = character.name
    db_session.flush()

    response = client.post(
        f"/api/v1/group-leader/orders/{first.id}/merge",
        json={"merge_with_order_ids": [str(second.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["items"]) == 2
    quantities = sorted(item["quantity"] for item in data["items"])
    assert quantities == [1, 2]
    assert sorted(item["chosen_character_name"] for item in data["items"]) == sorted(
        [character_a.name, character_b.name]
    )
    assert Decimal(data["product_total_amount"]) == Decimal("300.00")


def test_merge_rejects_order_with_pending_cancellation(client, db_session):
    ctx = _setup(db_session, client)
    base = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    other = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )
    db_session.add(
        CancellationRequest(order_id=other.id, reason="想改數量", status=CancellationStatus.PENDING)
    )
    db_session.flush()

    response = client.post(
        f"/api/v1/group-leader/orders/{base.id}/merge",
        json={"merge_with_order_ids": [str(other.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_MERGE_HAS_PENDING_CANCELLATION"


@pytest.mark.parametrize(
    "blocked_status",
    [OrderStatus.SHIPPED, OrderStatus.COMPLETED, OrderStatus.CANCELLED],
)
def test_merge_rejects_non_mergeable_statuses(client, db_session, blocked_status):
    """已出貨、已完成、已取消都不可合併（使用者 2026-07-29 確認）。

    已出貨之後貨都出了、已取消的訂單本身無效，都不該再併進其他訂單。
    """
    ctx = _setup(db_session, client)
    base = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    blocked = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=blocked_status,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{base.id}/merge",
        json={"merge_with_order_ids": [str(blocked.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_MERGE_STATUS_NOT_ALLOWED"

    # 也不該出現在可合併清單中
    mergeable = client.get(
        f"/api/v1/group-leader/orders/{base.id}/mergeable", headers=ctx["headers"]
    ).json()["data"]
    assert str(blocked.id) not in [item["id"] for item in mergeable]


def test_merged_source_order_keeps_its_own_items(client, db_session):
    """被併入的訂單要保留自己的明細作為歷史。

    若直接把明細搬到目標訂單，來源訂單會變成沒有商品的空殼，
    訂單列表就會顯示「共 0 件商品」。來源已是 cancelled，不會重複佔用庫存。
    """
    ctx = _setup(db_session, client)
    target = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    source = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        3,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )

    merged = client.post(
        f"/api/v1/group-leader/orders/{target.id}/merge",
        json={"merge_with_order_ids": [str(source.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["data"]["items"][0]["quantity"] == 5

    source_detail = client.get(
        f"/api/v1/group-leader/orders/{source.id}", headers=ctx["headers"]
    ).json()["data"]
    assert source_detail["status"] == "cancelled"
    # 來源訂單仍看得到自己原本訂的內容與金額
    assert len(source_detail["items"]) == 1
    assert source_detail["items"][0]["quantity"] == 3
    assert Decimal(source_detail["product_total_amount"]) == Decimal("300.00")

    # 列表的商品摘要不會變成「共 0 件」
    listed = client.get(
        "/api/v1/group-leader/orders",
        params={"page": 1, "page_size": 50},
        headers=ctx["headers"],
    ).json()["data"]
    source_row = next(row for row in listed if row["id"] == str(source.id))
    assert source_row["total_quantity"] == 3
    assert source_row["item_summary"]


@pytest.mark.parametrize(
    "blocked_status",
    [OrderStatus.SHIPPED, OrderStatus.COMPLETED, OrderStatus.CANCELLED],
)
def test_mergeable_list_empty_when_order_itself_cannot_merge(
    client, db_session, blocked_status
):
    """訂單本身不可合併時回空清單，前端才不會顯示合併區塊。"""
    ctx = _setup(db_session, client)
    blocked = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=blocked_status,
        created_at=_in_days(-3),
    )
    # 同會員同團另有一張可合併的訂單，但仍不該列出來
    create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )

    response = client.get(
        f"/api/v1/group-leader/orders/{blocked.id}/mergeable", headers=ctx["headers"]
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


def test_merge_rejects_different_member(client, db_session):
    ctx = _setup(db_session, client)
    base = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-3),
    )
    other_member_order = create_order_with_item(
        db_session,
        create_user(db_session),
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-1),
    )

    response = client.post(
        f"/api/v1/group-leader/orders/{base.id}/merge",
        json={"merge_with_order_ids": [str(other_member_order.id)], "keep": "oldest"},
        headers=ctx["headers"],
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_MERGE_DIFFERENT_MEMBER"


def test_mergeable_list_excludes_self_and_pending_cancellation(client, db_session):
    ctx = _setup(db_session, client)
    base = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-4),
    )
    ok = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_PAYMENT,
        created_at=_in_days(-3),
    )
    with_cancellation = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_CONFIRMATION,
        created_at=_in_days(-2),
    )
    db_session.add(
        CancellationRequest(
            order_id=with_cancellation.id, status=CancellationStatus.PENDING
        )
    )
    # 已出貨不可合併，不該出現在清單
    create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.SHIPPED,
        created_at=_in_days(-1),
    )
    db_session.flush()

    response = client.get(
        f"/api/v1/group-leader/orders/{base.id}/mergeable", headers=ctx["headers"]
    )

    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [str(ok.id)]
