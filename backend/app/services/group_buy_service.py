import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import ActivityStatus, GroupBuyStatus
from app.repositories import (
    activity_repository,
    announcement_repository,
    group_buy_repository,
    group_leader_repository,
    product_repository,
)
from app.schemas.announcement import PublicAnnouncementItem
from app.schemas.group_buy import (
    GroupBuyActivitySummary,
    GroupBuyDetailResponse,
    GroupBuyProductAvailabilityResponse,
    GroupBuyProductCharacterOption,
    GroupBuyProductItem,
    GroupBuyProductRef,
    GroupBuyRulesResponse,
)
from app.schemas.group_leader import GroupLeaderSummary
from app.services import availability_service


def _load_group_buy_or_404(db: Session, group_buy_id: uuid.UUID):
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None:
        raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")
    return group_buy


def _compute_group_buy_level_status(
    group_buy, activity, product_availabilities: list[dict]
) -> tuple[str, bool]:
    if group_buy.status == GroupBuyStatus.CLOSED:
        return "closed", False
    if activity.status == ActivityStatus.ENDED:
        return "activity_ended", False
    if group_buy.deadline_at <= datetime.now(timezone.utc):
        return "expired", False
    if product_availabilities and all(not a["is_available"] for a in product_availabilities):
        return "full", False
    return "open", True


def get_group_buy_detail(db: Session, group_buy_id: uuid.UUID) -> GroupBuyDetailResponse:
    group_buy = _load_group_buy_or_404(db, group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    leader_profile = group_leader_repository.get_profile_by_id(db, group_buy.group_leader_profile_id)
    product_rows = group_buy_repository.get_products_for_group_buy(db, group_buy_id)

    product_items = []
    availabilities = []
    for group_buy_product, product in product_rows:
        availability = availability_service.get_group_buy_product_availability(
            db, group_buy, activity, group_buy_product, product.is_active
        )
        availabilities.append(availability)

        character_options = []
        for character in product_repository.get_characters(db, product.id):
            char_availability = availability_service.get_character_availability(
                db, group_buy, activity, group_buy_product, character.id, product.is_active
            )
            character_options.append(
                GroupBuyProductCharacterOption(
                    character_id=character.id,
                    name=character.name,
                    available_quantity=char_availability["available_quantity"],
                    is_available=char_availability["is_available"],
                )
            )

        product_items.append(
            GroupBuyProductItem(
                group_buy_product_id=group_buy_product.id,
                product=GroupBuyProductRef.model_validate(product, from_attributes=True),
                unit_price=group_buy_product.unit_price,
                available_quantity=availability["available_quantity"],
                is_available=availability["is_available"],
                characters=character_options,
            )
        )

    effective_status, is_available = _compute_group_buy_level_status(
        group_buy, activity, availabilities
    )

    return GroupBuyDetailResponse(
        id=group_buy.id,
        activity=GroupBuyActivitySummary.model_validate(activity, from_attributes=True),
        group_leader=GroupLeaderSummary.model_validate(leader_profile, from_attributes=True),
        payment_method=group_buy.payment_method,
        payment_method_note=group_buy.payment_method_note,
        requires_second_payment=group_buy.requires_second_payment,
        includes_full_gift=group_buy.includes_full_gift,
        deadline_at=group_buy.deadline_at,
        rules=group_buy.rules,
        contact_platform=group_buy.contact_platform,
        contact_value=group_buy.contact_value,
        status=group_buy.status,
        effective_status=effective_status,
        is_available=is_available,
        products=product_items,
        created_at=group_buy.created_at,
    )


def get_group_buy_rules(db: Session, group_buy_id: uuid.UUID) -> GroupBuyRulesResponse:
    group_buy = _load_group_buy_or_404(db, group_buy_id)
    return GroupBuyRulesResponse(rules=group_buy.rules, updated_at=group_buy.updated_at)


def get_group_buy_public_announcements(
    db: Session, group_buy_id: uuid.UUID
) -> list[PublicAnnouncementItem]:
    _load_group_buy_or_404(db, group_buy_id)
    announcements = announcement_repository.list_public_group_buy_announcements(db, group_buy_id)
    return [PublicAnnouncementItem.model_validate(a, from_attributes=True) for a in announcements]


def get_group_buy_product_availability(
    db: Session, group_buy_product_id: uuid.UUID
) -> GroupBuyProductAvailabilityResponse:
    group_buy_product = group_buy_repository.get_group_buy_product_by_id(db, group_buy_product_id)
    if group_buy_product is None:
        raise AppError(404, "GROUP_BUY_PRODUCT_NOT_FOUND", "找不到指定的開團商品。")

    group_buy = group_buy_repository.get_by_id(db, group_buy_product.group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    product = product_repository.get_by_id(db, group_buy_product.product_id)

    availability = availability_service.get_group_buy_product_availability(
        db, group_buy, activity, group_buy_product, product.is_active
    )
    return GroupBuyProductAvailabilityResponse(
        group_buy_product_id=group_buy_product.id,
        is_available=availability["is_available"],
        available_quantity=availability["available_quantity"],
        effective_status=availability["effective_status"],
    )
