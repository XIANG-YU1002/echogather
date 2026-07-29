import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import ActivityStatus, GroupBuyListSort, GroupBuyStatus, PaymentMethod
from app.models.group_buy import GroupBuy
from app.models.group_leader import GroupLeaderProfile
from app.models.enums import ContactPlatform
from app.repositories import activity_repository, group_buy_repository, order_repository, product_repository
from app.schemas.common import FACEBOOK_URL_ERROR, is_facebook_url
from app.schemas.group_leader_group_buy import (
    AddGroupBuyProductRequest,
    CreateGroupBuyRequest,
    GroupBuyOwnerActivityCard,
    GroupBuyOwnerActivityRef,
    GroupBuyOwnerCharacterStock,
    GroupBuyOwnerDetailResponse,
    GroupBuyOwnerListItem,
    GroupBuyOwnerListSummary,
    GroupBuyOwnerProductItem,
    GroupBuyOwnerProductRef,
    GroupBuyProductOrdersResponse,
    ProductOrderGroup,
    ProductOrderMemberItem,
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


_CONTACT_PLATFORM_LABELS = {
    ContactPlatform.FACEBOOK: "Facebook",
    ContactPlatform.DISCORD: "Discord",
    ContactPlatform.LINE: "LINE",
}


def _leader_contact_value(profile: GroupLeaderProfile, platform: ContactPlatform) -> str | None:
    """團主資料中該平台的公開聯絡方式，未設定回傳 None。"""
    return {
        ContactPlatform.FACEBOOK: profile.facebook_url,
        ContactPlatform.DISCORD: profile.discord_contact,
        ContactPlatform.LINE: profile.line_contact,
    }[platform]


def _validate_contact(
    profile: GroupLeaderProfile, platform: ContactPlatform, value: str
) -> None:
    """開團的主要聯絡方式必須取自團主資料已設定的公開聯絡方式。

    依使用者 2026-07-29 裁決：開團不另外輸入聯絡方式，一律沿用團主資料，
    避免同一位團主在不同開團留下不一致（甚至過期）的聯絡資訊。
    在 Service 層檢查而非 schema，因為 PATCH 可能只送其中一欄、另一欄沿用既有值，
    schema 當下看不到最終組合。
    """
    profile_value = _leader_contact_value(profile, platform)
    label = _CONTACT_PLATFORM_LABELS[platform]

    if not profile_value:
        raise AppError(
            422,
            "CONTACT_NOT_SET_IN_PROFILE",
            f"請先在團主資料填寫 {label}，才能將它設為開團的主要聯絡方式。",
            {"fields": {"contact_platform": [f"團主資料尚未設定 {label}。"]}},
        )

    if value != profile_value:
        raise AppError(
            422,
            "CONTACT_VALUE_MISMATCH",
            f"主要聯絡方式需與團主資料的 {label} 一致，請改到團主資料修改。",
            {"fields": {"contact_value": [f"應為團主資料設定的 {label}。"]}},
        )

    # 團主資料的 FB 已驗證為連結，這裡再擋一次以防既有資料是舊格式
    if platform == ContactPlatform.FACEBOOK and not is_facebook_url(value):
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "輸入資料格式不正確。",
            {"fields": {"contact_value": [FACEBOOK_URL_ERROR]}},
        )


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

    # 同一團主對同一活動同時只能有一個進行中的開團（DB 亦有 partial unique index 把關）。
    if group_buy_repository.get_open_group_buy_for_activity(db, profile.id, activity.id):
        raise AppError(
            409,
            "GROUP_BUY_ALREADY_OPEN_FOR_ACTIVITY",
            "你對這個活動已經有一個進行中的開團，請先結單後再建立新的開團。",
        )

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

    _validate_contact(profile, payload.contact_platform, payload.contact_value)

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


def _is_upcoming_deadline(group_buy: GroupBuy) -> bool:
    """是否落在圖 20／21 的「即將截止」標記範圍（進行中且 3 天內到期）。"""
    if group_buy.status != GroupBuyStatus.OPEN:
        return False
    deadline = _ensure_utc(group_buy.deadline_at)
    now = datetime.now(timezone.utc)
    return now < deadline <= now + timedelta(days=group_buy_repository.UPCOMING_DEADLINE_DAYS)


def _to_list_item(row: tuple) -> GroupBuyOwnerListItem:
    """把 repository 的聚合查詢結果組成列表項目。"""
    (
        group_buy,
        activity,
        round_number,
        order_count,
        ordered_quantity,
        pending_order_count,
        total_order_count,
    ) = row
    return GroupBuyOwnerListItem(
        id=group_buy.id,
        activity=GroupBuyOwnerActivityCard.model_validate(activity, from_attributes=True),
        round_number=round_number,
        status=group_buy.status,
        payment_method=group_buy.payment_method,
        deadline_at=group_buy.deadline_at,
        is_upcoming_deadline=_is_upcoming_deadline(group_buy),
        order_count=order_count,
        ordered_quantity=ordered_quantity,
        pending_order_count=pending_order_count,
        has_orders=total_order_count > 0,
        created_at=group_buy.created_at,
    )


def get_my_group_buys(
    db: Session,
    profile: GroupLeaderProfile,
    status: GroupBuyStatus | None,
    page: int,
    page_size: int,
    *,
    keyword: str | None = None,
    sort: GroupBuyListSort = GroupBuyListSort.CREATED_DESC,
) -> tuple[list[GroupBuyOwnerListItem], int, GroupBuyOwnerListSummary]:
    """圖 21 我的開團。統計與輪次由單一查詢帶回，不再逐列打 DB。

    summary 三張卡固定統計該團主的全部開團，不受 status／keyword 篩選影響——
    卡片本身就是切換篩選的入口，跟著篩選變動會讓數字看起來自相矛盾。
    """
    rows, total = group_buy_repository.list_by_group_leader_with_stats(
        db, profile.id, status, page, page_size, keyword=keyword, sort=sort
    )
    summary_counts = group_buy_repository.count_status_summary(db, profile.id)
    summary = GroupBuyOwnerListSummary(
        total=summary_counts["total"],
        open=summary_counts["open"],
        closed=summary_counts["closed"],
    )
    return [_to_list_item(row) for row in rows], total, summary


def get_my_open_group_buys(
    db: Session, profile: GroupLeaderProfile
) -> list[GroupBuyOwnerListItem]:
    """圖 20 儀表板「目前開團」：只列進行中、不分頁，依截止時間由近到遠。"""
    rows = group_buy_repository.list_open_group_buys_with_stats(db, profile.id)
    return [_to_list_item(row) for row in rows]


def get_product_orders(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID
) -> GroupBuyProductOrdersResponse:
    """圖 22 商品訂購總覽：以「某一開團、某一商品」為主的訂購明細。

    與訂單管理（以所有訂單為主）的差別見 docs/03 §26.1a。
    """
    group_buy = _load_owned_group_buy(db, profile, group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)

    # 先建立所有開團商品的空群組，未被訂購的商品才不會從畫面上消失。
    groups: dict[uuid.UUID, ProductOrderGroup] = {}
    for group_buy_product, product in group_buy_repository.get_products_for_group_buy(
        db, group_buy.id
    ):
        groups[group_buy_product.id] = ProductOrderGroup(
            group_buy_product_id=group_buy_product.id,
            product=GroupBuyOwnerProductRef.model_validate(product, from_attributes=True),
            unit_price=group_buy_product.unit_price,
            max_quantity=group_buy_product.max_quantity,
            total_quantity=0,
            member_count=0,
            items=[],
        )

    members_by_product: dict[uuid.UUID, set[uuid.UUID]] = {key: set() for key in groups}
    order_ids: set[uuid.UUID] = set()
    total_ordered_quantity = 0

    for group_buy_product, _product, order_item, order, user in (
        group_buy_repository.list_product_orders(db, group_buy.id)
    ):
        group = groups.get(group_buy_product.id)
        if group is None:
            continue
        group.items.append(
            ProductOrderMemberItem(
                order_id=order.id,
                order_number=order.order_number,
                user_id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
                chosen_character_name=order_item.chosen_character_name_snapshot,
                quantity=order_item.quantity,
                order_status=order.status,
                submitted_at=order.created_at,
            )
        )
        group.total_quantity += order_item.quantity
        members_by_product[group_buy_product.id].add(user.id)
        order_ids.add(order.id)
        total_ordered_quantity += order_item.quantity

    for product_id, members in members_by_product.items():
        groups[product_id].member_count = len(members)

    return GroupBuyProductOrdersResponse(
        group_buy_id=group_buy.id,
        activity=GroupBuyOwnerActivityCard.model_validate(activity, from_attributes=True),
        round_number=group_buy_repository.get_round_number(db, group_buy),
        status=group_buy.status,
        deadline_at=group_buy.deadline_at,
        # 訂單數以不重複訂單計算：一張訂單含多個商品時只算一筆。
        total_order_count=len(order_ids),
        total_ordered_quantity=total_ordered_quantity,
        products=list(groups.values()),
    )


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
        round_number=group_buy_repository.get_round_number(db, group_buy),
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

    if "contact_platform" in provided or "contact_value" in provided:
        new_platform = (
            payload.contact_platform if "contact_platform" in provided else group_buy.contact_platform
        )
        if "contact_value" in provided:
            new_value = payload.contact_value
        elif "contact_platform" in provided:
            # 只切換平台時自動採用團主資料該平台的值，呼叫端不必重送
            new_value = _leader_contact_value(profile, new_platform) or group_buy.contact_value
        else:
            new_value = group_buy.contact_value
        _validate_contact(profile, new_platform, new_value)
        group_buy.contact_platform = new_platform
        group_buy.contact_value = new_value

    if not has_orders:
        if "payment_method" in provided or "payment_method_note" in provided:
            new_method = payload.payment_method if "payment_method" in provided else group_buy.payment_method
            new_note = (
                payload.payment_method_note if "payment_method_note" in provided else group_buy.payment_method_note
            )
            # 付款方式備註為選填，空白字串一律存成 NULL。
            if new_note is not None:
                new_note = new_note.strip() or None
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
