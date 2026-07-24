import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.follow_list import FollowList, FollowListItem


def get_by_user_id(db: Session, user_id: uuid.UUID, *, for_update: bool = False) -> FollowList | None:
    stmt = select(FollowList).where(FollowList.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def get_items(db: Session, follow_list_id: uuid.UUID) -> list[FollowListItem]:
    stmt = (
        select(FollowListItem)
        .where(FollowListItem.follow_list_id == follow_list_id)
        .order_by(FollowListItem.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def get_item_by_id(db: Session, item_id: uuid.UUID) -> FollowListItem | None:
    return db.get(FollowListItem, item_id)


def get_item_by_list_and_product(
    db: Session, follow_list_id: uuid.UUID, group_buy_product_id: uuid.UUID
) -> FollowListItem | None:
    stmt = select(FollowListItem).where(
        FollowListItem.follow_list_id == follow_list_id,
        FollowListItem.group_buy_product_id == group_buy_product_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_item_by_list_product_character(
    db: Session,
    follow_list_id: uuid.UUID,
    group_buy_product_id: uuid.UUID,
    chosen_character_id: uuid.UUID | None,
) -> FollowListItem | None:
    stmt = select(FollowListItem).where(
        FollowListItem.follow_list_id == follow_list_id,
        FollowListItem.group_buy_product_id == group_buy_product_id,
        FollowListItem.chosen_character_id.is_(None)
        if chosen_character_id is None
        else FollowListItem.chosen_character_id == chosen_character_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def count_items(db: Session, follow_list_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(FollowListItem)
        .where(FollowListItem.follow_list_id == follow_list_id)
    )
    return db.execute(stmt).scalar_one()


def create_follow_list(db: Session, user_id: uuid.UUID, group_buy_id: uuid.UUID) -> FollowList:
    follow_list = FollowList(user_id=user_id, group_buy_id=group_buy_id)
    db.add(follow_list)
    db.flush()
    return follow_list


def add_item(
    db: Session,
    follow_list_id: uuid.UUID,
    group_buy_product_id: uuid.UUID,
    quantity: int,
    chosen_character_id: uuid.UUID | None = None,
) -> FollowListItem:
    item = FollowListItem(
        follow_list_id=follow_list_id,
        group_buy_product_id=group_buy_product_id,
        chosen_character_id=chosen_character_id,
        quantity=quantity,
    )
    db.add(item)
    db.flush()
    return item


def delete_follow_list(db: Session, follow_list: FollowList) -> None:
    db.delete(follow_list)
    db.flush()


def delete_item(db: Session, item: FollowListItem) -> None:
    db.delete(item)
    db.flush()
