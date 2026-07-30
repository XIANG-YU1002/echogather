import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.models.enums import CancellationStatus, OrderStatus
from app.models.group_buy import GroupBuy
from app.models.order import CancellationRequest, GroupOrder, OrderItem, OrderStatusHistory
from app.models.user import AppUser

# 不佔用庫存、也不計入團主端統計的訂單狀態。開團統計（訂單數／訂購數量）沿用同一基準，
# 依使用者 2026-07-29 裁決：已取消與已拒絕的訂單不算進統計。
# merged（被併進另一張訂單的來源訂單）也必須在此：合併時明細是複製到目標訂單，
# 來源訂單保留自己的明細作為歷史，若它仍佔用庫存，同一筆訂購量就會被算兩次。
NON_OCCUPYING_STATUSES = ("cancelled", "rejected", "merged")

# 會員端與團主端一律看不到的訂單狀態（使用者 2026-07-30 裁決：合併後來源訂單
# 從畫面上消失，等同刪除，但資料庫完整保留以供拆單還原）。
HIDDEN_ORDER_STATUSES = ("merged",)


def get_occupied_quantity(
    db: Session, group_buy_product_id: uuid.UUID, character_id: uuid.UUID | None = None
) -> int:
    """依 Business Rules §20.1：除 cancelled／rejected 外的訂單明細數量總和。

    傳入 character_id 時只計算該角色的佔用量（分角色庫存用）；不傳則計整體。
    """
    stmt = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(GroupOrder, GroupOrder.id == OrderItem.order_id)
        .where(
            OrderItem.group_buy_product_id == group_buy_product_id,
            GroupOrder.status.notin_(NON_OCCUPYING_STATUSES),
        )
    )
    if character_id is not None:
        stmt = stmt.where(OrderItem.chosen_character_id == character_id)
    return int(db.execute(stmt).scalar_one())


def get_by_id(db: Session, order_id: uuid.UUID, *, for_update: bool = False) -> GroupOrder | None:
    stmt = select(GroupOrder).where(GroupOrder.id == order_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def get_items(db: Session, order_id: uuid.UUID) -> list[OrderItem]:
    stmt = (
        select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def order_number_exists(db: Session, order_number: str) -> bool:
    stmt = select(GroupOrder.id).where(GroupOrder.order_number == order_number)
    return db.execute(stmt).scalar_one_or_none() is not None


def generate_unique_order_number(db: Session) -> str:
    """產生每日流水的訂單編號，格式為 WG{YYMMDD}-{6 位流水}，例如 WG260727-000001。

    以單一原子語句對 order_number_counter 取號（INSERT ... ON CONFLICT DO UPDATE
    ... RETURNING），同一天內遞增、隔天自動從 1 重新開始；併發下單不會拿到相同號碼。
    """
    date_key = datetime.now(timezone.utc).strftime("%y%m%d")
    serial = db.execute(
        text(
            """
            INSERT INTO order_number_counter (date_key, last_value)
            VALUES (:date_key, 1)
            ON CONFLICT (date_key)
            DO UPDATE SET last_value = order_number_counter.last_value + 1
            RETURNING last_value
            """
        ),
        {"date_key": date_key},
    ).scalar_one()
    return f"WG{date_key}-{serial:06d}"


def create_order(db: Session, **fields) -> GroupOrder:
    order = GroupOrder(**fields)
    db.add(order)
    db.flush()
    return order


def create_status_history(
    db: Session, order_id: uuid.UUID, status: OrderStatus, note: str | None = None
) -> OrderStatusHistory:
    """記錄一次訂單狀態異動（圖 08 右側「狀態紀錄」用）。

    刻意不 flush：呼叫端（例如 reject_order）會在轉換後才補上 rejection_reason，
    提前 flush 會讓 group_order 的 UPDATE 先送出而違反 rejection_reason 成對約束。
    """
    entry = OrderStatusHistory(order_id=order_id, status=status, note=note)
    db.add(entry)
    return entry


def list_status_history(db: Session, order_id: uuid.UUID) -> list[OrderStatusHistory]:
    stmt = (
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def create_order_item(db: Session, **fields) -> OrderItem:
    item = OrderItem(**fields)
    db.add(item)
    db.flush()
    return item


def list_by_user(
    db: Session,
    user_id: uuid.UUID,
    status: OrderStatus | None,
    page: int,
    page_size: int,
    *,
    activity_name: str | None = None,
    group_leader_name: str | None = None,
    created_within_days: int | None = None,
) -> tuple[list[GroupOrder], int]:
    """依圖 07 篩選卡：狀態、時間範圍、活動名稱、團主名稱（後兩者為不分大小寫的部分比對）。"""
    stmt = select(GroupOrder).where(
        GroupOrder.user_id == user_id,
        # 被合併掉的訂單在畫面上等同已刪除，任何狀態篩選都不該出現
        GroupOrder.status.notin_(HIDDEN_ORDER_STATUSES),
    )
    if status is not None:
        stmt = stmt.where(GroupOrder.status == status)
    if activity_name:
        stmt = stmt.where(GroupOrder.activity_name_snapshot.ilike(f"%{activity_name}%"))
    if group_leader_name:
        stmt = stmt.where(GroupOrder.group_leader_name_snapshot.ilike(f"%{group_leader_name}%"))
    if created_within_days:
        since = datetime.now(timezone.utc) - timedelta(days=created_within_days)
        stmt = stmt.where(GroupOrder.created_at >= since)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(GroupOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total


def list_by_group_buy_and_status(
    db: Session, group_buy_id: uuid.UUID, status: OrderStatus, *, for_update: bool = False
) -> list[GroupOrder]:
    """取得單一開團中指定狀態的所有訂單（批次出貨用）。"""
    stmt = (
        select(GroupOrder)
        .where(GroupOrder.group_buy_id == group_buy_id, GroupOrder.status == status)
        .order_by(GroupOrder.created_at.asc())
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalars().all()


def count_by_group_buy_and_status(
    db: Session, group_buy_id: uuid.UUID, status: OrderStatus
) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupOrder)
        .where(GroupOrder.group_buy_id == group_buy_id, GroupOrder.status == status)
    )
    return int(db.execute(stmt).scalar_one())


def count_for_leader_by_statuses(
    db: Session, group_leader_profile_id: uuid.UUID, statuses: Sequence[OrderStatus]
) -> int:
    """統計該團主底下指定狀態的訂單數。傳入多個狀態時為合計（例如「待處理」）。"""
    stmt = (
        select(func.count())
        .select_from(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupOrder.status.in_(tuple(statuses)),
        )
    )
    return int(db.execute(stmt).scalar_one())


def get_group_buy_for_update(db: Session, group_buy_id: uuid.UUID) -> GroupBuy | None:
    stmt = select(GroupBuy).where(GroupBuy.id == group_buy_id).with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def list_same_member_orders_in_group_buy(
    db: Session,
    group_buy_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    statuses: Sequence[OrderStatus],
    exclude_order_id: uuid.UUID | None = None,
    for_update: bool = False,
) -> list[GroupOrder]:
    """同一會員在同一開團的訂單（訂單合併用）。

    依建立時間遞增排序，讓「保留最舊」與「保留最新」都能直接取頭尾。
    for_update 供合併時鎖定，避免併發合併同一批訂單。
    """
    stmt = (
        select(GroupOrder)
        .where(
            GroupOrder.group_buy_id == group_buy_id,
            GroupOrder.user_id == user_id,
            GroupOrder.status.in_(tuple(statuses)),
        )
        .order_by(GroupOrder.created_at.asc(), GroupOrder.id.asc())
    )
    if exclude_order_id is not None:
        stmt = stmt.where(GroupOrder.id != exclude_order_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalars().all()


def _leader_orders_stmt(
    group_leader_profile_id: uuid.UUID,
    *,
    group_buy_id: uuid.UUID | None,
    activity_id: uuid.UUID | None,
    keyword: str | None,
):
    """團主訂單的共用篩選（不含狀態），列表與統計卡共用同一組條件。

    被合併掉的來源訂單（merged）在這裡就排除，列表、六張統計卡與待處理取消申請
    計數因此一致看不到它們——若分頭排除，總有一處會漏掉而讓它露出來。
    """
    stmt = (
        select(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupOrder.status.notin_(HIDDEN_ORDER_STATUSES),
        )
    )
    if group_buy_id is not None:
        stmt = stmt.where(GroupOrder.group_buy_id == group_buy_id)
    if activity_id is not None:
        stmt = stmt.where(GroupBuy.activity_id == activity_id)
    if keyword:
        stmt = stmt.join(AppUser, AppUser.id == GroupOrder.user_id).where(
            or_(
                GroupOrder.order_number.ilike(f"%{keyword}%"),
                AppUser.nickname.ilike(f"%{keyword}%"),
            )
        )
    return stmt


def count_for_leader_grouped_by_status(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    *,
    group_buy_id: uuid.UUID | None = None,
    activity_id: uuid.UUID | None = None,
    keyword: str | None = None,
) -> dict[OrderStatus, int]:
    """圖 25 統計卡：各狀態的訂單數，一次 GROUP BY 取回。

    刻意不吃 status 條件——統計卡是切換狀態篩選的入口，跟著篩選變動會自相矛盾。
    """
    base = _leader_orders_stmt(
        group_leader_profile_id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        keyword=keyword,
    ).subquery()
    stmt = select(base.c.status, func.count()).group_by(base.c.status)
    return {status: int(count) for status, count in db.execute(stmt).all()}


def count_pending_cancellation_for_leader(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    *,
    group_buy_id: uuid.UUID | None = None,
    activity_id: uuid.UUID | None = None,
    keyword: str | None = None,
) -> int:
    """圖 25「待處理取消申請」卡：有待處理取消申請的訂單數。"""
    base = _leader_orders_stmt(
        group_leader_profile_id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        keyword=keyword,
    ).subquery()
    pending_order_ids = select(CancellationRequest.order_id).where(
        CancellationRequest.status == CancellationStatus.PENDING
    )
    stmt = (
        select(func.count())
        .select_from(base)
        .where(base.c.id.in_(pending_order_ids))
    )
    return int(db.execute(stmt).scalar_one())


def list_for_leader(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    *,
    group_buy_id: uuid.UUID | None,
    activity_id: uuid.UUID | None,
    statuses: Sequence[OrderStatus] | None,
    has_pending_cancellation: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
    newest_first: bool = False,
) -> tuple[list[GroupOrder], int]:
    """依 API Design §24.1：團主訂單列表，預設 created_at ASC, id ASC（先喊先得）。

    statuses 接受多個狀態以支援「待處理」這種複合篩選（待確認＋待付款）。
    newest_first 只改變排序方向，預設仍是先喊先得（Business Rules §24.1）。
    """
    stmt = _leader_orders_stmt(
        group_leader_profile_id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        keyword=keyword,
    )
    if statuses:
        stmt = stmt.where(GroupOrder.status.in_(tuple(statuses)))
    if has_pending_cancellation is not None:
        pending_order_ids = select(CancellationRequest.order_id).where(
            CancellationRequest.status == CancellationStatus.PENDING
        )
        if has_pending_cancellation:
            stmt = stmt.where(GroupOrder.id.in_(pending_order_ids))
        else:
            stmt = stmt.where(GroupOrder.id.notin_(pending_order_ids))

    order_by = (
        (GroupOrder.created_at.desc(), GroupOrder.id.desc())
        if newest_first
        else (GroupOrder.created_at.asc(), GroupOrder.id.asc())
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(*order_by).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total
