"""取消合併（拆單）流程，使用者 2026-07-30 需求。

規則：
- 合併後被併掉的訂單標記 merged，前後台都看不到，資料保留。
- 會員在「訂單已合併」通知底下提出取消合併申請（不是立刻拆）。
- 團主可核准（拆回合併前各自的狀態與金額）或拒絕（原因必填），兩者都會通知會員。
- 已出貨之後不可拆；同時只能有一筆待處理申請；二次合併只能從最新批次往回拆。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.enums import CancellationStatus, OrderStatus
from app.models.order import GroupOrder, OrderItem, OrderMerge
from app.repositories import order_repository
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
    return {
        "leader_headers": auth_headers(login(client, leader_user.email, "Passw0rd1")),
        "member_headers": auth_headers(login(client, member.email, "Passw0rd1")),
        "group_buy": group_buy,
        "group_buy_product": group_buy_product,
        "member": member,
        "profile": profile,
        "leader_user": leader_user,
    }


def _merge_two(db_session, client, ctx, *, older_status, newer_status, keep="oldest"):
    """建立兩張訂單並合併，回傳 (保留的那張, 被併掉的那張)。"""
    older = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        2,
        status=older_status,
        created_at=_in_days(-3),
    )
    newer = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        3,
        status=newer_status,
        created_at=_in_days(-1),
    )
    response = client.post(
        f"/api/v1/group-leader/orders/{older.id}/merge",
        json={"merge_with_order_ids": [str(newer.id)], "keep": keep},
        headers=ctx["leader_headers"],
    )
    assert response.status_code == 200, response.text
    target, source = (older, newer) if keep == "oldest" else (newer, older)
    return target, source


def _request_unmerge(client, ctx, order_id, reason="想分開付款"):
    return client.post(
        f"/api/v1/orders/{order_id}/unmerge-requests",
        json={"reason": reason},
        headers=ctx["member_headers"],
    )


def test_merge_notification_carries_batch_and_button_flag(client, db_session):
    """合併通知要帶批次並允許申請拆單，且訊息含被併掉訂單的商品明細。"""
    ctx = _setup(db_session, client)
    _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )

    notifications = client.get(
        "/api/v1/notifications", params={"page": 1, "page_size": 20}, headers=ctx["member_headers"]
    ).json()["data"]
    merged_note = next(n for n in notifications if n["title"] == "訂單已合併")
    assert merged_note["unmerge_batch_id"]
    assert merged_note["can_request_unmerge"] is True
    # 被併掉的訂單有什麼商品要寫在通知裡（使用者 2026-07-30 需求）
    assert "被合併的訂單內容：" in merged_note["message"]
    assert "×3" in merged_note["message"]
    assert "聯絡團主" in merged_note["message"]


def test_member_requests_unmerge_then_leader_approves_restores_orders(client, db_session):
    """核准拆單後：來源訂單恢復原狀態並重新顯示，目標訂單金額與狀態回到合併前。"""
    ctx = _setup(db_session, client)
    target, source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )

    created = _request_unmerge(client, ctx, target.id)
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "pending"
    # 申請時要讓團主看得到會拆出哪幾張
    assert [s["order_number"] for s in created.json()["data"]["source_orders"]] == [
        source.order_number
    ]

    detail = client.get(
        f"/api/v1/group-leader/orders/{target.id}", headers=ctx["leader_headers"]
    ).json()["data"]
    assert detail["pending_unmerge_request"]["id"] == request_id

    approved = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": None},
        headers=ctx["leader_headers"],
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"

    db_session.expire_all()
    # 目標訂單回到合併前：只剩自己的 2 件、200 元、待確認
    target_row = db_session.get(GroupOrder, target.id)
    assert target_row.status == OrderStatus.PENDING_CONFIRMATION
    assert Decimal(target_row.product_total_amount) == Decimal("200.00")
    target_items = db_session.query(OrderItem).filter(OrderItem.order_id == target.id).all()
    assert len(target_items) == 1
    assert target_items[0].quantity == 2

    # 來源訂單恢復成合併前的狀態，並重新出現在兩端的列表
    source_row = db_session.get(GroupOrder, source.id)
    assert source_row.status == OrderStatus.PENDING_CONFIRMATION
    listed = client.get(
        "/api/v1/group-leader/orders",
        params={"page": 1, "page_size": 50},
        headers=ctx["leader_headers"],
    ).json()["data"]
    assert {row["id"] for row in listed} >= {str(target.id), str(source.id)}
    assert (
        client.get(
            f"/api/v1/orders/{source.id}", headers=ctx["member_headers"]
        ).status_code
        == 200
    )


def test_approve_restores_original_statuses_and_paid_amount(client, db_session):
    """已付款那張併進待付款後拆回，各自要回到原本的狀態與已收金額。"""
    ctx = _setup(db_session, client)
    target, source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_PAYMENT,
        newer_status=OrderStatus.PAID,
    )

    db_session.expire_all()
    merged_target = db_session.get(GroupOrder, target.id)
    # 合併後：總額 500，其中已付款那張的 300 記為已收
    assert Decimal(merged_target.product_total_amount) == Decimal("500.00")
    assert Decimal(merged_target.paid_amount) == Decimal("300.00")

    request_id = _request_unmerge(client, ctx, target.id).json()["data"]["id"]
    approved = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": "幫你拆回來了"},
        headers=ctx["leader_headers"],
    )
    assert approved.status_code == 200, approved.text

    db_session.expire_all()
    target_row = db_session.get(GroupOrder, target.id)
    source_row = db_session.get(GroupOrder, source.id)
    assert target_row.status == OrderStatus.PENDING_PAYMENT
    assert Decimal(target_row.paid_amount) == Decimal("0.00")
    assert Decimal(target_row.product_total_amount) == Decimal("200.00")
    # 已付款那張回到已付款，不會變成又要收錢
    assert source_row.status == OrderStatus.PAID
    assert Decimal(source_row.product_total_amount) == Decimal("300.00")


def test_approve_does_not_double_count_stock(client, db_session):
    """合併與拆單都不能讓同一筆訂購量被算兩次。"""
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    db_session.expire_all()
    # 合併後總量仍是 2+3=5（來源是 merged，不佔用）
    assert order_repository.get_occupied_quantity(db_session, ctx["group_buy_product"].id) == 5

    request_id = _request_unmerge(client, ctx, target.id).json()["data"]["id"]
    client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": None},
        headers=ctx["leader_headers"],
    )
    db_session.expire_all()
    assert order_repository.get_occupied_quantity(db_session, ctx["group_buy_product"].id) == 5


def test_reject_keeps_merged_state_and_requires_reason(client, db_session):
    """拒絕必須填原因；拒絕後訂單維持合併後的狀態，會員可再次申請。"""
    ctx = _setup(db_session, client)
    target, source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    request_id = _request_unmerge(client, ctx, target.id).json()["data"]["id"]

    blank = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/reject",
        json={"response_note": "   "},
        headers=ctx["leader_headers"],
    )
    assert blank.status_code == 422

    rejected = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/reject",
        json={"response_note": "已經一起收款了"},
        headers=ctx["leader_headers"],
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["status"] == "rejected"

    db_session.expire_all()
    # 訂單維持合併後的樣子
    assert db_session.get(GroupOrder, target.id).status == OrderStatus.PENDING_PAYMENT
    assert db_session.get(GroupOrder, source.id).status == OrderStatus.MERGED
    assert Decimal(db_session.get(GroupOrder, target.id).product_total_amount) == Decimal(
        "500.00"
    )
    # 被拒絕後可以再提一次
    assert _request_unmerge(client, ctx, target.id).status_code == 201


def test_only_one_pending_request_at_a_time(client, db_session):
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    assert _request_unmerge(client, ctx, target.id).status_code == 201
    duplicated = _request_unmerge(client, ctx, target.id)
    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "UNMERGE_REQUEST_ALREADY_PENDING"


def test_request_rejected_for_order_without_merge(client, db_session):
    ctx = _setup(db_session, client)
    plain = create_order_with_item(
        db_session,
        ctx["member"],
        ctx["group_buy"],
        ctx["group_buy_product"],
        1,
        status=OrderStatus.PENDING_PAYMENT,
        created_at=_in_days(-1),
    )
    response = _request_unmerge(client, ctx, plain.id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_MERGED"


@pytest.mark.parametrize("blocked_status", [OrderStatus.SHIPPED, OrderStatus.COMPLETED])
def test_request_rejected_after_shipped(client, db_session, blocked_status):
    """已出貨之後不能再拆（與可合併狀態的規則一致）。"""
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    db_session.get(GroupOrder, target.id).status = blocked_status
    db_session.commit()

    response = _request_unmerge(client, ctx, target.id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "UNMERGE_NOT_ALLOWED"


def test_other_member_cannot_request_unmerge(client, db_session):
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    outsider = create_user(db_session)
    response = client.post(
        f"/api/v1/orders/{target.id}/unmerge-requests",
        json={"reason": None},
        headers=auth_headers(login(client, outsider.email, "Passw0rd1")),
    )
    assert response.status_code == 404


def test_cannot_approve_same_batch_twice(client, db_session):
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    request_id = _request_unmerge(client, ctx, target.id).json()["data"]["id"]
    first = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": None},
        headers=ctx["leader_headers"],
    )
    assert first.status_code == 200
    again = client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": None},
        headers=ctx["leader_headers"],
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "UNMERGE_REQUEST_ALREADY_PROCESSED"


def test_merge_record_marked_unmerged_after_approval(client, db_session):
    """拆單後合併紀錄要留著並標記時間，之後才判斷得出「已經拆過」。"""
    ctx = _setup(db_session, client)
    target, source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    request_id = _request_unmerge(client, ctx, target.id).json()["data"]["id"]
    client.post(
        f"/api/v1/group-leader/unmerge-requests/{request_id}/approve",
        json={"response_note": None},
        headers=ctx["leader_headers"],
    )

    db_session.expire_all()
    record = (
        db_session.query(OrderMerge).filter(OrderMerge.source_order_id == source.id).one()
    )
    assert record.unmerged_at is not None
    assert record.source_status_before == OrderStatus.PENDING_CONFIRMATION

    # 已拆開的訂單不再提供拆單申請
    response = _request_unmerge(client, ctx, target.id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_MERGED"


def test_notification_button_hidden_while_request_pending(client, db_session):
    """已有待處理申請時，通知底下不再顯示按鈕（避免重複送出）。"""
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    _request_unmerge(client, ctx, target.id)

    notifications = client.get(
        "/api/v1/notifications", params={"page": 1, "page_size": 20}, headers=ctx["member_headers"]
    ).json()["data"]
    merged_note = next(n for n in notifications if n["title"] == "訂單已合併")
    assert merged_note["can_request_unmerge"] is False


def test_leader_gets_notified_of_unmerge_request(client, db_session):
    """團主要收到申請通知，且導向團主端訂單頁。"""
    ctx = _setup(db_session, client)
    target, _source = _merge_two(
        db_session,
        client,
        ctx,
        older_status=OrderStatus.PENDING_CONFIRMATION,
        newer_status=OrderStatus.PENDING_CONFIRMATION,
    )
    _request_unmerge(client, ctx, target.id, reason="想改數量")

    leader_notes = client.get(
        "/api/v1/notifications", params={"page": 1, "page_size": 20}, headers=ctx["leader_headers"]
    ).json()["data"]
    note = next(n for n in leader_notes if n["title"] == "會員申請取消合併訂單")
    assert note["target_url"] == f"/group-leader/orders/{target.id}"
    assert "想改數量" in note["message"]
    # 團主自己不該看到拆單按鈕（他不是下單會員）
    assert note["can_request_unmerge"] is False
