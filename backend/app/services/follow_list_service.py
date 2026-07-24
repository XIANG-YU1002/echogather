import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.follow_list import FollowList
from app.repositories import (
    activity_repository,
    follow_list_repository,
    group_buy_repository,
    group_leader_repository,
    product_repository,
)
from app.schemas.follow_list import (
    AddFollowListItemRequest,
    FollowListActivityRef,
    FollowListGroupBuySummary,
    FollowListItemResponse,
    FollowListProductRef,
    FollowListResponse,
    UpdateFollowListItemResponse,
)
from app.schemas.group_leader import GroupLeaderSummary
from app.schemas.product import CharacterSummary
from app.services import availability_service


def _load_group_buy_product_or_404(db: Session, group_buy_product_id: uuid.UUID):
    group_buy_product = group_buy_repository.get_group_buy_product_by_id(db, group_buy_product_id)
    if group_buy_product is None:
        raise AppError(404, "GROUP_BUY_PRODUCT_NOT_FOUND", "找不到指定的開團商品。")
    return group_buy_product


def _resolve_chosen_character_id(db: Session, product, requested_character_id):
    """依商品角色數判定所選角色：無角色→None；單角色→自動帶入；多角色→必填且須屬於該商品。"""
    characters = product_repository.get_characters(db, product.id)
    if not characters:
        return None
    if len(characters) == 1:
        return characters[0].id
    character_ids = {c.id for c in characters}
    if requested_character_id is None:
        raise AppError(422, "CHARACTER_REQUIRED", "此商品有多個角色/款式，請先選擇一個。")
    if requested_character_id not in character_ids:
        raise AppError(422, "INVALID_CHARACTER", "所選角色/款式不屬於此商品。")
    return requested_character_id


def _availability_for(db: Session, group_buy_product):
    group_buy = group_buy_repository.get_by_id(db, group_buy_product.group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    product = product_repository.get_by_id(db, group_buy_product.product_id)
    availability = availability_service.get_group_buy_product_availability(
        db, group_buy, activity, group_buy_product, product.is_active
    )
    return group_buy, activity, product, availability


def _build_response(db: Session, follow_list: FollowList) -> FollowListResponse:
    group_buy = group_buy_repository.get_by_id(db, follow_list.group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    leader_profile = group_leader_repository.get_profile_by_id(db, group_buy.group_leader_profile_id)
    group_level_status = availability_service.compute_group_buy_level_status(group_buy, activity)

    items = follow_list_repository.get_items(db, follow_list.id)
    item_responses = []
    estimated_total = Decimal("0")
    invalid_reasons: list[str] = []
    if group_level_status != "open":
        invalid_reasons.append("GROUP_BUY_NOT_AVAILABLE")

    any_insufficient = False
    for item in items:
        group_buy_product = group_buy_repository.get_group_buy_product_by_id(
            db, item.group_buy_product_id
        )
        product = product_repository.get_by_id(db, group_buy_product.product_id)
        characters = product_repository.get_characters(db, product.id)

        if item.chosen_character_id is not None:
            availability = availability_service.get_character_availability(
                db, group_buy, activity, group_buy_product, item.chosen_character_id, product.is_active
            )
        else:
            availability = availability_service.get_group_buy_product_availability(
                db, group_buy, activity, group_buy_product, product.is_active
            )
        item_is_available = availability["is_available"] and item.quantity <= availability[
            "available_quantity"
        ]
        if not item_is_available:
            any_insufficient = True

        chosen_character = next(
            (
                CharacterSummary.model_validate(c, from_attributes=True)
                for c in characters
                if c.id == item.chosen_character_id
            ),
            None,
        )

        subtotal = group_buy_product.unit_price * item.quantity
        estimated_total += subtotal
        item_responses.append(
            FollowListItemResponse(
                id=item.id,
                group_buy_product_id=group_buy_product.id,
                product=FollowListProductRef(
                    id=product.id,
                    name=product.name,
                    primary_image_url=product.primary_image_url,
                    characters=[
                        CharacterSummary.model_validate(c, from_attributes=True) for c in characters
                    ],
                ),
                chosen_character=chosen_character,
                unit_price=group_buy_product.unit_price,
                quantity=item.quantity,
                estimated_subtotal=subtotal,
                is_available=item_is_available,
            )
        )

    if any_insufficient:
        invalid_reasons.append("INSUFFICIENT_AVAILABLE_QUANTITY")

    return FollowListResponse(
        id=follow_list.id,
        group_buy=FollowListGroupBuySummary(
            id=group_buy.id,
            group_leader=GroupLeaderSummary.model_validate(leader_profile, from_attributes=True),
            activity=FollowListActivityRef.model_validate(activity, from_attributes=True),
            payment_method=group_buy.payment_method,
            payment_method_note=group_buy.payment_method_note,
            requires_second_payment=group_buy.requires_second_payment,
            includes_full_gift=group_buy.includes_full_gift,
            deadline_at=group_buy.deadline_at,
            rules=group_buy.rules,
            contact_platform=group_buy.contact_platform,
            contact_value=group_buy.contact_value,
            effective_status=group_level_status,
            is_available=group_level_status == "open",
        ),
        items=item_responses,
        estimated_product_total=estimated_total,
        is_submittable=not invalid_reasons,
        invalid_reasons=invalid_reasons,
        created_at=follow_list.created_at,
        updated_at=follow_list.updated_at,
    )


def get_follow_list(db: Session, user_id: uuid.UUID) -> FollowListResponse | None:
    follow_list = follow_list_repository.get_by_user_id(db, user_id)
    if follow_list is None:
        return None
    return _build_response(db, follow_list)


def add_item(
    db: Session, user_id: uuid.UUID, payload: AddFollowListItemRequest
) -> FollowListResponse:
    """依 Business Rules §18.2-18.4：同開團加量、不同開團需確認替換，整段在同一 Transaction 完成。"""
    if payload.quantity <= 0:
        raise AppError(422, "INVALID_QUANTITY", "數量必須大於 0。")

    group_buy_product = _load_group_buy_product_or_404(db, payload.group_buy_product_id)
    group_buy, activity, product, aggregate_availability = _availability_for(db, group_buy_product)

    chosen_character_id = _resolve_chosen_character_id(db, product, payload.chosen_character_id)

    # 有選角色→以該角色的分角色庫存判定；無角色→用整體庫存。
    if chosen_character_id is not None:
        availability = availability_service.get_character_availability(
            db, group_buy, activity, group_buy_product, chosen_character_id, product.is_active
        )
    else:
        availability = aggregate_availability

    if not availability["is_available"]:
        raise AppError(409, "GROUP_BUY_NOT_AVAILABLE", "此開團目前無法跟團。")

    existing_list = follow_list_repository.get_by_user_id(db, user_id, for_update=True)

    replacing = False
    if existing_list is not None and existing_list.group_buy_id != group_buy.id:
        if not payload.replace_existing:
            raise AppError(
                409,
                "FOLLOW_LIST_GROUP_BUY_CONFLICT",
                "目前跟團清單屬於其他開團。",
                {
                    "current_group_buy_id": str(existing_list.group_buy_id),
                    "requested_group_buy_id": str(group_buy.id),
                },
            )
        replacing = True

    existing_item = None
    if existing_list is not None and not replacing:
        existing_item = follow_list_repository.get_item_by_list_product_character(
            db, existing_list.id, group_buy_product.id, chosen_character_id
        )

    prospective_quantity = (existing_item.quantity if existing_item else 0) + payload.quantity
    if prospective_quantity > availability["available_quantity"]:
        raise AppError(
            409,
            "INSUFFICIENT_AVAILABLE_QUANTITY",
            "部分商品的可接受數量不足。",
            {
                "items": [
                    {
                        "group_buy_product_id": str(group_buy_product.id),
                        "requested_quantity": prospective_quantity,
                        "available_quantity": availability["available_quantity"],
                    }
                ]
            },
        )

    if replacing:
        follow_list_repository.delete_follow_list(db, existing_list)
        existing_list = None
    if existing_list is None:
        existing_list = follow_list_repository.create_follow_list(db, user_id, group_buy.id)

    if existing_item is not None:
        existing_item.quantity = prospective_quantity
    else:
        follow_list_repository.add_item(
            db, existing_list.id, group_buy_product.id, prospective_quantity, chosen_character_id
        )

    db.commit()
    db.refresh(existing_list)
    return _build_response(db, existing_list)


def _get_owned_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID):
    item = follow_list_repository.get_item_by_id(db, item_id)
    if item is None:
        raise AppError(404, "FOLLOW_LIST_ITEM_NOT_FOUND", "找不到跟團清單項目。")
    follow_list = db.get(FollowList, item.follow_list_id)
    if follow_list is None or follow_list.user_id != user_id:
        raise AppError(404, "FOLLOW_LIST_ITEM_NOT_FOUND", "找不到跟團清單項目。")
    return item, follow_list


def update_item_quantity(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID, quantity: int
) -> UpdateFollowListItemResponse:
    if quantity <= 0:
        raise AppError(422, "INVALID_QUANTITY", "數量必須大於 0。")

    item, follow_list = _get_owned_item(db, user_id, item_id)
    group_buy_product = group_buy_repository.get_group_buy_product_by_id(
        db, item.group_buy_product_id
    )
    group_buy, activity, product, aggregate_availability = _availability_for(db, group_buy_product)

    if item.chosen_character_id is not None:
        availability = availability_service.get_character_availability(
            db, group_buy, activity, group_buy_product, item.chosen_character_id, product.is_active
        )
    else:
        availability = aggregate_availability

    if quantity > availability["available_quantity"]:
        raise AppError(
            409,
            "INSUFFICIENT_AVAILABLE_QUANTITY",
            "可接受數量不足。",
            {
                "items": [
                    {
                        "group_buy_product_id": str(group_buy_product.id),
                        "requested_quantity": quantity,
                        "available_quantity": availability["available_quantity"],
                    }
                ]
            },
        )

    item.quantity = quantity
    db.commit()

    items = follow_list_repository.get_items(db, follow_list.id)
    total = Decimal("0")
    for other_item in items:
        other_group_buy_product = group_buy_repository.get_group_buy_product_by_id(
            db, other_item.group_buy_product_id
        )
        total += other_group_buy_product.unit_price * other_item.quantity

    return UpdateFollowListItemResponse(
        id=item.id,
        quantity=item.quantity,
        unit_price=group_buy_product.unit_price,
        estimated_subtotal=group_buy_product.unit_price * item.quantity,
        estimated_product_total=total,
    )


def remove_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item, follow_list = _get_owned_item(db, user_id, item_id)
    follow_list_repository.delete_item(db, item)

    remaining = follow_list_repository.count_items(db, follow_list.id)
    if remaining == 0:
        follow_list_repository.delete_follow_list(db, follow_list)
    db.commit()


def clear_follow_list(db: Session, user_id: uuid.UUID) -> None:
    """依 API Design §17.5：沒有清單時仍可回傳成功（Idempotent）。"""
    follow_list = follow_list_repository.get_by_user_id(db, user_id)
    if follow_list is not None:
        follow_list_repository.delete_follow_list(db, follow_list)
        db.commit()
