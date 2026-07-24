from datetime import datetime, timezone

from sqlalchemy.orm import Session

import uuid

from app.models.activity import Activity
from app.models.enums import ActivityStatus, GroupBuyStatus
from app.models.group_buy import GroupBuy, GroupBuyProduct
from app.repositories import group_buy_repository, order_repository


def compute_effective_status(
    *, group_buy_status: GroupBuyStatus, activity_status: ActivityStatus, deadline_at, available_quantity: int
) -> str:
    """依 Business Rules §16.7/§16.8：判斷順序需能清楚回傳主要不可用原因。"""
    if group_buy_status == GroupBuyStatus.CLOSED:
        return "closed"
    if activity_status == ActivityStatus.ENDED:
        return "activity_ended"
    if deadline_at <= datetime.now(timezone.utc):
        return "expired"
    if available_quantity <= 0:
        return "full"
    return "open"


def compute_group_buy_level_status(group_buy: GroupBuy, activity: Activity) -> str:
    """開團整體狀態（不含數量），供跟團清單／團主公開開團列表等不需商品可用性的情境使用。"""
    if group_buy.status == GroupBuyStatus.CLOSED:
        return "closed"
    if activity.status == ActivityStatus.ENDED:
        return "activity_ended"
    if group_buy.deadline_at <= datetime.now(timezone.utc):
        return "expired"
    return "open"


def get_group_buy_product_availability(
    db: Session,
    group_buy: GroupBuy,
    activity: Activity,
    group_buy_product: GroupBuyProduct,
    product_is_active: bool,
) -> dict:
    occupied_quantity = order_repository.get_occupied_quantity(db, group_buy_product.id)
    available_quantity = max(group_buy_product.max_quantity - occupied_quantity, 0)
    effective_status = compute_effective_status(
        group_buy_status=group_buy.status,
        activity_status=activity.status,
        deadline_at=group_buy.deadline_at,
        available_quantity=available_quantity,
    )
    is_available = effective_status == "open" and product_is_active

    return {
        "available_quantity": available_quantity,
        "effective_status": effective_status,
        "is_available": is_available,
    }


def get_character_availability(
    db: Session,
    group_buy: GroupBuy,
    activity: Activity,
    group_buy_product: GroupBuyProduct,
    character_id: uuid.UUID,
    product_is_active: bool,
) -> dict:
    """分角色庫存的可用性：以該角色的接單上限與該角色的佔用量計算。"""
    char_max = (
        group_buy_repository.get_character_max_quantity(db, group_buy_product.id, character_id) or 0
    )
    occupied = order_repository.get_occupied_quantity(db, group_buy_product.id, character_id)
    available_quantity = max(char_max - occupied, 0)
    effective_status = compute_effective_status(
        group_buy_status=group_buy.status,
        activity_status=activity.status,
        deadline_at=group_buy.deadline_at,
        available_quantity=available_quantity,
    )
    is_available = effective_status == "open" and product_is_active
    return {
        "available_quantity": available_quantity,
        "effective_status": effective_status,
        "is_available": is_available,
    }
