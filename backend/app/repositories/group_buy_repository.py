import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.enums import ActivityStatus, GroupBuyStatus, PaymentMethod
from app.models.follow_list import FollowListItem
from app.models.group_buy import GroupBuy, GroupBuyProduct, GroupBuyProductCharacter
from app.models.group_leader import GroupLeaderProfile
from app.models.order import GroupOrder
from app.models.product import Character, Product


def get_by_id(db: Session, group_buy_id: uuid.UUID) -> GroupBuy | None:
    return db.get(GroupBuy, group_buy_id)


def get_group_buy_product_by_id(db: Session, group_buy_product_id: uuid.UUID) -> GroupBuyProduct | None:
    return db.get(GroupBuyProduct, group_buy_product_id)


def get_group_buy_products_for_update(
    db: Session, group_buy_product_ids: list[uuid.UUID]
) -> list[GroupBuyProduct]:
    """依 API Design §33.2：多筆 group_buy_product 依 UUID 排序鎖定，降低 Deadlock 風險。"""
    stmt = (
        select(GroupBuyProduct)
        .where(GroupBuyProduct.id.in_(group_buy_product_ids))
        .order_by(GroupBuyProduct.id.asc())
        .with_for_update()
    )
    return db.execute(stmt).scalars().all()


def get_products_for_group_buy(
    db: Session, group_buy_id: uuid.UUID
) -> list[tuple[GroupBuyProduct, Product]]:
    stmt = (
        select(GroupBuyProduct, Product)
        .join(Product, Product.id == GroupBuyProduct.product_id)
        .where(GroupBuyProduct.group_buy_id == group_buy_id)
        .order_by(GroupBuyProduct.created_at.asc())
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def list_group_buy_products_for_product(
    db: Session,
    product_id: uuid.UUID,
    *,
    cash_on_delivery_only: bool,
    requires_second_payment: bool | None,
    includes_full_gift: bool | None,
) -> list[tuple[GroupBuyProduct, GroupBuy, Activity, GroupLeaderProfile]]:
    """依 Business Rules §17.3：取得可套用 SQL 篩選的候選集合，可用性篩選於 Service 層計算。"""
    stmt = (
        select(GroupBuyProduct, GroupBuy, Activity, GroupLeaderProfile)
        .join(GroupBuy, GroupBuy.id == GroupBuyProduct.group_buy_id)
        .join(Activity, Activity.id == GroupBuy.activity_id)
        .join(GroupLeaderProfile, GroupLeaderProfile.id == GroupBuy.group_leader_profile_id)
        .where(GroupBuyProduct.product_id == product_id)
    )
    if cash_on_delivery_only:
        stmt = stmt.where(GroupBuy.payment_method == PaymentMethod.CASH_ON_DELIVERY)
    if requires_second_payment is not None:
        stmt = stmt.where(GroupBuy.requires_second_payment.is_(requires_second_payment))
    if includes_full_gift is not None:
        stmt = stmt.where(GroupBuy.includes_full_gift.is_(includes_full_gift))

    return [(row[0], row[1], row[2], row[3]) for row in db.execute(stmt).all()]


def list_by_group_leader(
    db: Session, group_leader_profile_id: uuid.UUID, status: GroupBuyStatus | None
) -> list[GroupBuy]:
    stmt = select(GroupBuy).where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    if status is not None:
        stmt = stmt.where(GroupBuy.status == status)
    stmt = stmt.order_by(GroupBuy.created_at.desc())
    return db.execute(stmt).scalars().all()


def count_group_buys_by_group_leader(db: Session, group_leader_profile_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(GroupBuy).where(
        GroupBuy.group_leader_profile_id == group_leader_profile_id
    )
    return db.execute(stmt).scalar_one()


def list_by_group_leader_paginated(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    status: GroupBuyStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[GroupBuy], int]:
    stmt = select(GroupBuy).where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    if status is not None:
        stmt = stmt.where(GroupBuy.status == status)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(GroupBuy.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total


def count_by_group_leader_and_status(
    db: Session, group_leader_profile_id: uuid.UUID, status: GroupBuyStatus
) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupBuy)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupBuy.status == status,
        )
    )
    return db.execute(stmt).scalar_one()


def count_formal_orders(db: Session, group_buy_id: uuid.UUID) -> int:
    """依 Business Rules §16.1：只要存在任何 group_order 紀錄就視為已有正式訂單。"""
    stmt = select(func.count()).select_from(GroupOrder).where(GroupOrder.group_buy_id == group_buy_id)
    return db.execute(stmt).scalar_one()


def create_group_buy(db: Session, **fields) -> GroupBuy:
    group_buy = GroupBuy(**fields)
    db.add(group_buy)
    db.flush()
    return group_buy


def create_group_buy_product(db: Session, **fields) -> GroupBuyProduct:
    group_buy_product = GroupBuyProduct(**fields)
    db.add(group_buy_product)
    db.flush()
    return group_buy_product


def set_product_character_stock(
    db: Session, group_buy_product_id: uuid.UUID, quantities: list[tuple[uuid.UUID, int]]
) -> None:
    """覆寫某開團商品的每角色庫存（先清空再寫入）。傳入空清單等同清空（無角色商品）。"""
    db.execute(
        delete(GroupBuyProductCharacter).where(
            GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id
        )
    )
    for character_id, max_quantity in quantities:
        db.add(
            GroupBuyProductCharacter(
                group_buy_product_id=group_buy_product_id,
                character_id=character_id,
                max_quantity=max_quantity,
            )
        )
    db.flush()


def get_product_character_stock(
    db: Session, group_buy_product_id: uuid.UUID
) -> list[tuple[Character, int]]:
    """回傳（角色, 每角色接單上限）清單，依角色名稱排序。無角色商品回傳空清單。"""
    stmt = (
        select(Character, GroupBuyProductCharacter.max_quantity)
        .join(
            GroupBuyProductCharacter,
            GroupBuyProductCharacter.character_id == Character.id,
        )
        .where(GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id)
        .order_by(Character.name.asc())
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_character_max_quantity(
    db: Session, group_buy_product_id: uuid.UUID, character_id: uuid.UUID
) -> int | None:
    stmt = select(GroupBuyProductCharacter.max_quantity).where(
        GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id,
        GroupBuyProductCharacter.character_id == character_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def count_products_in_group_buy(db: Session, group_buy_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupBuyProduct)
        .where(GroupBuyProduct.group_buy_id == group_buy_id)
    )
    return db.execute(stmt).scalar_one()


def product_exists_in_group_buy(db: Session, group_buy_id: uuid.UUID, product_id: uuid.UUID) -> bool:
    stmt = select(GroupBuyProduct.id).where(
        GroupBuyProduct.group_buy_id == group_buy_id, GroupBuyProduct.product_id == product_id
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def delete_group_buy_product(db: Session, group_buy_product: GroupBuyProduct) -> None:
    db.delete(group_buy_product)
    db.flush()


def has_follow_list_items_for_product(db: Session, group_buy_product_id: uuid.UUID) -> bool:
    stmt = select(FollowListItem.id).where(
        FollowListItem.group_buy_product_id == group_buy_product_id
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def _current_group_buys_base_stmt():
    return (
        select(GroupBuy, Activity, GroupLeaderProfile)
        .join(Activity, Activity.id == GroupBuy.activity_id)
        .join(GroupLeaderProfile, GroupLeaderProfile.id == GroupBuy.group_leader_profile_id)
        .where(
            GroupBuy.status == GroupBuyStatus.OPEN,
            GroupBuy.deadline_at > datetime.now(timezone.utc),
            Activity.status == ActivityStatus.OPEN,
        )
    )


def count_current_group_buys(db: Session) -> int:
    """依 API Design §26.2：目前開團需同時符合 open／deadline 未到／活動 open。"""
    stmt = _current_group_buys_base_stmt()
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()


def list_current_group_buys(
    db: Session, page: int, page_size: int
) -> tuple[list[tuple[GroupBuy, Activity, GroupLeaderProfile]], int]:
    stmt = _current_group_buys_base_stmt()
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(GroupBuy.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows], total


def count_orders_for_group_buy(db: Session, group_buy_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(GroupOrder).where(GroupOrder.group_buy_id == group_buy_id)
    return db.execute(stmt).scalar_one()
