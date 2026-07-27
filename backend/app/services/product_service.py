import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import PaymentMethod
from app.models.user import AppUser
from app.repositories import activity_repository, group_buy_repository, product_repository
from app.schemas.group_leader import GroupLeaderSummary
from app.schemas.product import (
    CharacterSummary,
    ProductActivitySummary,
    ProductDetailResponse,
    ProductGroupBuyListItem,
    ProductImageItem,
)
from app.services import availability_service

_SORT_KEYS = {
    "newest": lambda row: row[1].created_at,
    "price_asc": lambda row: row[0].unit_price,
    "price_desc": lambda row: row[0].unit_price,
    "deadline_asc": lambda row: row[1].deadline_at,
    "deadline_desc": lambda row: row[1].deadline_at,
}
_SORT_REVERSE = {"newest": True, "price_desc": True, "deadline_desc": True}


def get_product_detail(
    db: Session, product_id: uuid.UUID, current_user: AppUser | None
) -> ProductDetailResponse:
    product = product_repository.get_by_id(db, product_id)
    if product is None:
        raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")

    activity = activity_repository.get_by_id(db, product.activity_id)
    images = product_repository.get_images(db, product_id)
    characters = product_repository.get_characters(db, product_id)
    is_favorited = (
        product_repository.is_favorited(db, current_user.id, product_id)
        if current_user is not None
        else False
    )

    return ProductDetailResponse(
        id=product.id,
        name=product.name,
        official_price=product.official_price,
        official_currency=product.official_currency,
        primary_image_url=product.primary_image_url,
        is_active=product.is_active,
        activity=ProductActivitySummary.model_validate(activity, from_attributes=True),
        images=[ProductImageItem.model_validate(i, from_attributes=True) for i in images],
        characters=[CharacterSummary.model_validate(c, from_attributes=True) for c in characters],
        is_favorited=is_favorited,
    )


def get_product_group_buys(
    db: Session,
    product_id: uuid.UUID,
    *,
    sort: str,
    available_only: bool,
    payment_method: PaymentMethod | None,
    requires_second_payment: bool | None,
    includes_full_gift: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[ProductGroupBuyListItem], int]:
    product = product_repository.get_by_id(db, product_id)
    if product is None:
        raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")

    rows = group_buy_repository.list_group_buy_products_for_product(
        db,
        product_id,
        payment_method=payment_method,
        requires_second_payment=requires_second_payment,
        includes_full_gift=includes_full_gift,
    )

    enriched = []
    for group_buy_product, group_buy, activity, leader_profile in rows:
        availability = availability_service.get_group_buy_product_availability(
            db, group_buy, activity, group_buy_product, product.is_active
        )
        if available_only and not availability["is_available"]:
            continue
        enriched.append((group_buy_product, group_buy, leader_profile, availability))

    key_fn = _SORT_KEYS.get(sort, _SORT_KEYS["newest"])
    enriched.sort(key=key_fn, reverse=_SORT_REVERSE.get(sort, False))

    total = len(enriched)
    offset = (page - 1) * page_size
    page_rows = enriched[offset : offset + page_size]

    items = [
        ProductGroupBuyListItem(
            id=group_buy.id,
            group_buy_product_id=group_buy_product.id,
            group_leader=GroupLeaderSummary.model_validate(leader_profile, from_attributes=True),
            unit_price=group_buy_product.unit_price,
            payment_method=group_buy.payment_method,
            payment_method_note=group_buy.payment_method_note,
            requires_second_payment=group_buy.requires_second_payment,
            includes_full_gift=group_buy.includes_full_gift,
            deadline_at=group_buy.deadline_at,
            contact_platform=group_buy.contact_platform,
            effective_status=availability["effective_status"],
            is_available=availability["is_available"],
            available_quantity=availability["available_quantity"],
            created_at=group_buy.created_at,
        )
        for group_buy_product, group_buy, leader_profile, availability in page_rows
    ]
    return items, total
