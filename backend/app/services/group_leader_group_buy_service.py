import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import ActivityStatus, GroupBuyStatus, PaymentMethod
from app.models.group_buy import GroupBuy
from app.models.group_leader import GroupLeaderProfile
from app.repositories import activity_repository, group_buy_repository, order_repository, product_repository
from app.schemas.group_leader_group_buy import (
    AddGroupBuyProductRequest,
    CreateGroupBuyRequest,
    GroupBuyOwnerActivityRef,
    GroupBuyOwnerCharacterStock,
    GroupBuyOwnerDetailResponse,
    GroupBuyOwnerListItem,
    GroupBuyOwnerProductItem,
    GroupBuyOwnerProductRef,
    UpdateGroupBuyProductRequest,
    UpdateGroupBuySettingsRequest,
)


def _apply_character_stock(db, group_buy_product, product, character_quantities) -> None:
    """設定開團商品的每角色庫存。

    無角色商品：清空每角色庫存、沿用 max_quantity。
    有角色商品：未指定的角色以 max_quantity 作為 fallback；並把 max_quantity
    同步為各角色數量總和（作為整體庫存的去正規化值）。
    """
    characters = product_repository.get_characters(db, product.id)
    if not characters:
        group_buy_repository.set_product_character_stock(db, group_buy_product.id, [])
        return

    provided = {cq.character_id: cq.max_quantity for cq in (character_quantities or [])}
    quantities: list[tuple] = []
    total = 0
    for character in characters:
        qty = provided.get(character.id, group_buy_product.max_quantity)
        quantities.append((character.id, qty))
        total += qty
    group_buy_repository.set_product_character_stock(db, group_buy_product.id, quantities)
    group_buy_product.max_quantity = total

_FIELDS_EDITABLE_WITHOUT_ORDERS = {
    "payment_method",
    "payment_method_note",
    "requires_second_payment",
    "includes_full_gift",
    "deadline_at",
    "rules",
    "contact_platform",
    "contact_value",
}
_FIELDS_EDITABLE_WITH_ORDERS = {"deadline_at", "contact_platform", "contact_value"}

_EDITABLE_FIELDS_RESPONSE_NO_ORDERS = [
    "payment_method",
    "payment_method_note",
    "requires_second_payment",
    "includes_full_gift",
    "deadline_at",
    "rules",
    "contact_platform",
    "contact_value",
    "unit_price",
    "max_quantity",
]
_EDITABLE_FIELDS_RESPONSE_WITH_ORDERS = ["deadline_at", "contact_platform", "contact_value", "max_quantity"]


def _ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _load_owned_group_buy(db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID) -> GroupBuy:
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None:
        raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "GROUP_BUY_NOT_OWNED", "此開團不屬於你。")
    return group_buy


def create_group_buy(
    db: Session, profile: GroupLeaderProfile, payload: CreateGroupBuyRequest
) -> GroupBuyOwnerDetailResponse:
    """依 Business Rules §15 / API Design §23.2：建立前完整驗證，任一步失敗不得建立部分資料。"""
    activity = activity_repository.get_by_id(db, payload.activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "找不到指定的活動。")
    if activity.status != ActivityStatus.OPEN:
        raise AppError(409, "ACTIVITY_NOT_OPEN", "活動目前不是進行中，無法建立開團。")

    deadline_at = _ensure_utc(payload.deadline_at)
    if deadline_at <= datetime.now(timezone.utc):
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "輸入資料格式不正確。",
            {"fields": {"deadline_at": ["收單期限必須晚於目前時間。"]}},
        )

    if payload.includes_full_gift and not activity.has_full_gift:
        raise AppError(409, "FULL_GIFT_NOT_SUPPORTED", "此活動不支援滿贈。")

    resolved_products = []
    for item in payload.products:
        product = product_repository.get_by_id(db, item.product_id)
        if product is None:
            raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")
        if product.activity_id != activity.id:
            raise AppError(409, "PRODUCT_ACTIVITY_MISMATCH", "商品必須屬於所選活動。")
        if not product.is_active:
            raise AppError(409, "PRODUCT_INACTIVE", "商品已下架，無法加入開團。")
        resolved_products.append((item, product))

    group_buy = group_buy_repository.create_group_buy(
        db,
        group_leader_profile_id=profile.id,
        activity_id=activity.id,
        payment_method=payload.payment_method,
        payment_method_note=payload.payment_method_note,
        requires_second_payment=payload.requires_second_payment,
        includes_full_gift=payload.includes_full_gift,
        deadline_at=deadline_at,
        rules=payload.rules,
        contact_platform=payload.contact_platform,
        contact_value=payload.contact_value,
        status=GroupBuyStatus.OPEN,
    )

    for item, product in resolved_products:
        group_buy_product = group_buy_repository.create_group_buy_product(
            db,
            group_buy_id=group_buy.id,
            product_id=product.id,
            unit_price=item.unit_price,
            max_quantity=item.max_quantity,
        )
        _apply_character_stock(db, group_buy_product, product, item.character_quantities)

    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)


def get_my_group_buys(
    db: Session, profile: GroupLeaderProfile, status: GroupBuyStatus | None, page: int, page_size: int
) -> tuple[list[GroupBuyOwnerListItem], int]:
    group_buys, total = group_buy_repository.list_by_group_leader_paginated(
        db, profile.id, status, page, page_size
    )
    items = []
    for group_buy in group_buys:
        activity = activity_repository.get_by_id(db, group_buy.activity_id)
        has_orders = group_buy_repository.count_formal_orders(db, group_buy.id) > 0
        items.append(
            GroupBuyOwnerListItem(
                id=group_buy.id,
                activity=GroupBuyOwnerActivityRef.model_validate(activity, from_attributes=True),
                status=group_buy.status,
                deadline_at=group_buy.deadline_at,
                has_orders=has_orders,
                created_at=group_buy.created_at,
            )
        )
    return items, total


def get_my_group_buy_detail(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID
) -> GroupBuyOwnerDetailResponse:
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    has_orders = group_buy_repository.count_formal_orders(db, group_buy.id) > 0

    product_items = []
    for group_buy_product, product in group_buy_repository.get_products_for_group_buy(db, group_buy.id):
        occupied = order_repository.get_occupied_quantity(db, group_buy_product.id)
        available = max(group_buy_product.max_quantity - occupied, 0)

        character_stock = []
        for character, char_max in group_buy_repository.get_product_character_stock(
            db, group_buy_product.id
        ):
            char_occupied = order_repository.get_occupied_quantity(
                db, group_buy_product.id, character.id
            )
            character_stock.append(
                GroupBuyOwnerCharacterStock(
                    character_id=character.id,
                    name=character.name,
                    max_quantity=char_max,
                    occupied_quantity=char_occupied,
                    available_quantity=max(char_max - char_occupied, 0),
                )
            )

        product_items.append(
            GroupBuyOwnerProductItem(
                id=group_buy_product.id,
                product=GroupBuyOwnerProductRef.model_validate(product, from_attributes=True),
                unit_price=group_buy_product.unit_price,
                max_quantity=group_buy_product.max_quantity,
                occupied_quantity=occupied,
                available_quantity=available,
                character_stock=character_stock,
            )
        )

    editable_fields = (
        _EDITABLE_FIELDS_RESPONSE_WITH_ORDERS if has_orders else _EDITABLE_FIELDS_RESPONSE_NO_ORDERS
    )

    return GroupBuyOwnerDetailResponse(
        id=group_buy.id,
        activity=GroupBuyOwnerActivityRef.model_validate(activity, from_attributes=True),
        payment_method=group_buy.payment_method,
        payment_method_note=group_buy.payment_method_note,
        requires_second_payment=group_buy.requires_second_payment,
        includes_full_gift=group_buy.includes_full_gift,
        deadline_at=group_buy.deadline_at,
        rules=group_buy.rules,
        contact_platform=group_buy.contact_platform,
        contact_value=group_buy.contact_value,
        status=group_buy.status,
        closed_at=group_buy.closed_at,
        products=product_items,
        has_orders=has_orders,
        editable_fields=editable_fields,
        created_at=group_buy.created_at,
        updated_at=group_buy.updated_at,
    )


def update_group_buy_settings(
    db: Session,
    profile: GroupLeaderProfile,
    group_buy_id: uuid.UUID,
    payload: UpdateGroupBuySettingsRequest,
) -> GroupBuyOwnerDetailResponse:
    """依 Business Rules §16.2/§16.3：已有正式訂單後僅可修改截止時間與聯絡方式。"""
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    has_orders = group_buy_repository.count_formal_orders(db, group_buy.id) > 0
    allowed = _FIELDS_EDITABLE_WITH_ORDERS if has_orders else _FIELDS_EDITABLE_WITHOUT_ORDERS

    provided = payload.model_fields_set
    disallowed = provided - allowed
    if disallowed:
        raise AppError(
            409,
            "GROUP_BUY_FIELDS_FROZEN",
            "開團已有正式訂單，此欄位不可修改。",
            {"fields": sorted(disallowed)},
        )

    if "deadline_at" in provided:
        deadline = _ensure_utc(payload.deadline_at)
        if deadline <= datetime.now(timezone.utc):
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "輸入資料格式不正確。",
                {"fields": {"deadline_at": ["收單期限不得早於目前時間。"]}},
            )
        group_buy.deadline_at = deadline

    if "contact_platform" in provided:
        group_buy.contact_platform = payload.contact_platform
    if "contact_value" in provided:
        group_buy.contact_value = payload.contact_value

    if not has_orders:
        if "payment_method" in provided or "payment_method_note" in provided:
            new_method = payload.payment_method if "payment_method" in provided else group_buy.payment_method
            new_note = (
                payload.payment_method_note if "payment_method_note" in provided else group_buy.payment_method_note
            )
            if new_method == PaymentMethod.OTHER and not new_note:
                raise AppError(422, "PAYMENT_METHOD_NOTE_REQUIRED", "選擇其他付款方式時必須填寫說明。")
            if new_method != PaymentMethod.OTHER and new_note is not None:
                raise AppError(422, "PAYMENT_METHOD_NOTE_NOT_ALLOWED", "非其他付款方式不可填寫付款方式說明。")
            group_buy.payment_method = new_method
            group_buy.payment_method_note = new_note

        if "requires_second_payment" in provided:
            group_buy.requires_second_payment = payload.requires_second_payment

        if "includes_full_gift" in provided:
            if payload.includes_full_gift:
                activity = activity_repository.get_by_id(db, group_buy.activity_id)
                if not activity.has_full_gift:
                    raise AppError(409, "FULL_GIFT_NOT_SUPPORTED", "此活動不支援滿贈。")
            group_buy.includes_full_gift = payload.includes_full_gift

        if "rules" in provided:
            group_buy.rules = payload.rules

    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)


def add_group_buy_product(
    db: Session,
    profile: GroupLeaderProfile,
    group_buy_id: uuid.UUID,
    payload: AddGroupBuyProductRequest,
) -> GroupBuyOwnerDetailResponse:
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    if group_buy_repository.count_formal_orders(db, group_buy.id) > 0:
        raise AppError(409, "GROUP_BUY_HAS_ORDERS", "開團已有正式訂單，無法新增商品。")
    if group_buy_repository.product_exists_in_group_buy(db, group_buy.id, payload.product_id):
        raise AppError(409, "GROUP_BUY_PRODUCT_DUPLICATED", "此商品已存在於開團中。")

    product = product_repository.get_by_id(db, payload.product_id)
    if product is None:
        raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")
    if product.activity_id != group_buy.activity_id:
        raise AppError(409, "PRODUCT_ACTIVITY_MISMATCH", "商品必須屬於此開團的活動。")
    if not product.is_active:
        raise AppError(409, "PRODUCT_INACTIVE", "商品已下架，無法加入開團。")

    group_buy_product = group_buy_repository.create_group_buy_product(
        db,
        group_buy_id=group_buy.id,
        product_id=product.id,
        unit_price=payload.unit_price,
        max_quantity=payload.max_quantity,
    )
    _apply_character_stock(db, group_buy_product, product, payload.character_quantities)
    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)


def update_group_buy_product(
    db: Session,
    profile: GroupLeaderProfile,
    group_buy_id: uuid.UUID,
    group_buy_product_id: uuid.UUID,
    payload: UpdateGroupBuyProductRequest,
) -> GroupBuyOwnerDetailResponse:
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    group_buy_product = group_buy_repository.get_group_buy_product_by_id(db, group_buy_product_id)
    if group_buy_product is None or group_buy_product.group_buy_id != group_buy.id:
        raise AppError(404, "GROUP_BUY_PRODUCT_NOT_FOUND", "找不到指定的開團商品。")

    has_orders = group_buy_repository.count_formal_orders(db, group_buy.id) > 0
    provided = payload.model_fields_set

    if has_orders and "unit_price" in provided:
        raise AppError(409, "GROUP_BUY_FIELDS_FROZEN", "開團已有正式訂單，售價不可修改。")

    if "unit_price" in provided:
        group_buy_product.unit_price = payload.unit_price

    if "max_quantity" in provided:
        if has_orders:
            occupied = order_repository.get_occupied_quantity(db, group_buy_product.id)
            if payload.max_quantity < occupied:
                raise AppError(
                    409,
                    "MAX_QUANTITY_BELOW_OCCUPIED",
                    "接單上限不可低於目前已占用數量。",
                    {"occupied_quantity": occupied},
                )
        group_buy_product.max_quantity = payload.max_quantity

    if "character_quantities" in provided and payload.character_quantities is not None:
        product = product_repository.get_by_id(db, group_buy_product.product_id)
        _apply_character_stock(db, group_buy_product, product, payload.character_quantities)

    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)


def remove_group_buy_product(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID, group_buy_product_id: uuid.UUID
) -> GroupBuyOwnerDetailResponse:
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    group_buy_product = group_buy_repository.get_group_buy_product_by_id(db, group_buy_product_id)
    if group_buy_product is None or group_buy_product.group_buy_id != group_buy.id:
        raise AppError(404, "GROUP_BUY_PRODUCT_NOT_FOUND", "找不到指定的開團商品。")

    if group_buy_repository.count_formal_orders(db, group_buy.id) > 0:
        raise AppError(409, "GROUP_BUY_HAS_ORDERS", "開團已有正式訂單，無法移除商品。")

    if group_buy_repository.count_products_in_group_buy(db, group_buy.id) <= 1:
        raise AppError(409, "GROUP_BUY_MUST_KEEP_ONE_PRODUCT", "開團至少須保留一項商品。")

    if group_buy_repository.has_follow_list_items_for_product(db, group_buy_product.id):
        raise AppError(409, "CONFLICT", "已有會員將此商品加入跟團清單，無法移除。")

    group_buy_repository.delete_group_buy_product(db, group_buy_product)
    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)


def close_group_buy(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID
) -> GroupBuyOwnerDetailResponse:
    """依 Business Rules §16.6：第一版不可重新開啟。"""
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    if group_buy.status != GroupBuyStatus.OPEN:
        raise AppError(409, "GROUP_BUY_ALREADY_CLOSED", "開團已經結單。")

    group_buy.status = GroupBuyStatus.CLOSED
    group_buy.closed_at = datetime.now(timezone.utc)
    db.commit()
    return get_my_group_buy_detail(db, profile, group_buy.id)
