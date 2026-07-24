import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import CancellationStatus, OrderStatus
from app.models.group_buy import GroupBuy
from app.models.order import CancellationRequest, GroupOrder, OrderItem
from app.models.user import AppUser

_NON_OCCUPYING_STATUSES = ("cancelled", "rejected")


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
            GroupOrder.status.notin_(_NON_OCCUPYING_STATUSES),
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
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(5):
        candidate = f"WG-{date_part}-{uuid.uuid4().hex[:6].upper()}"
        if not order_number_exists(db, candidate):
            return candidate
    raise RuntimeError("無法產生唯一訂單編號，請重試。")


def create_order(db: Session, **fields) -> GroupOrder:
    order = GroupOrder(**fields)
    db.add(order)
    db.flush()
    return order


def create_order_item(db: Session, **fields) -> OrderItem:
    item = OrderItem(**fields)
    db.add(item)
    db.flush()
    return item


def list_by_user(
    db: Session, user_id: uuid.UUID, status: OrderStatus | None, page: int, page_size: int
) -> tuple[list[GroupOrder], int]:
    stmt = select(GroupOrder).where(GroupOrder.user_id == user_id)
    if status is not None:
        stmt = stmt.where(GroupOrder.status == status)

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


def count_for_leader_by_status(
    db: Session, group_leader_profile_id: uuid.UUID, status: OrderStatus
) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupOrder.status == status,
        )
    )
    return db.execute(stmt).scalar_one()


def get_group_buy_for_update(db: Session, group_buy_id: uuid.UUID) -> GroupBuy | None:
    stmt = select(GroupBuy).where(GroupBuy.id == group_buy_id).with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def list_for_leader(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    *,
    group_buy_id: uuid.UUID | None,
    activity_id: uuid.UUID | None,
    status: OrderStatus | None,
    has_pending_cancellation: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[GroupOrder], int]:
    """依 API Design §24.1：團主訂單列表，預設 created_at ASC, id ASC（先喊先得）。"""
    stmt = (
        select(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    )
    if group_buy_id is not None:
        stmt = stmt.where(GroupOrder.group_buy_id == group_buy_id)
    if activity_id is not None:
        stmt = stmt.where(GroupBuy.activity_id == activity_id)
    if status is not None:
        stmt = stmt.where(GroupOrder.status == status)
    if keyword:
        stmt = stmt.join(AppUser, AppUser.id == GroupOrder.user_id).where(
            or_(
                GroupOrder.order_number.ilike(f"%{keyword}%"),
                AppUser.nickname.ilike(f"%{keyword}%"),
            )
        )
    if has_pending_cancellation is not None:
        pending_order_ids = select(CancellationRequest.order_id).where(
            CancellationRequest.status == CancellationStatus.PENDING
        )
        if has_pending_cancellation:
            stmt = stmt.where(GroupOrder.id.in_(pending_order_ids))
        else:
            stmt = stmt.where(GroupOrder.id.notin_(pending_order_ids))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(GroupOrder.created_at.asc(), GroupOrder.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total
