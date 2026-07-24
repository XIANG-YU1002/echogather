import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import CancellationStatus, OrderStatus
from app.models.user import AppUser
from app.repositories import (
    activity_repository,
    cancellation_repository,
    character_repository,
    follow_list_repository,
    group_buy_repository,
    group_leader_repository,
    order_repository,
    product_repository,
)
from app.schemas.order import (
    CancellationRequestSummary,
    CreateOrderResponse,
    OrderDetailResponse,
    OrderItemDetail,
    OrderListItem,
)
from app.services import availability_service


def create_order(db: Session, user: AppUser, rules_accepted: bool) -> CreateOrderResponse:
    """依 Business Rules §19 及 API Design §18.1/§33.2：鎖定跟團清單、開團與開團商品，重新驗證後原子建立訂單。"""
    if not rules_accepted:
        raise AppError(422, "RULES_NOT_ACCEPTED", "請先閱讀並同意本次團規。")

    follow_list = follow_list_repository.get_by_user_id(db, user.id, for_update=True)
    if follow_list is None:
        raise AppError(409, "FOLLOW_LIST_EMPTY", "跟團清單是空的。")

    items = follow_list_repository.get_items(db, follow_list.id)
    if not items:
        raise AppError(409, "FOLLOW_LIST_EMPTY", "跟團清單是空的。")

    group_buy = order_repository.get_group_buy_for_update(db, follow_list.group_buy_id)
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    if availability_service.compute_group_buy_level_status(group_buy, activity) != "open":
        raise AppError(409, "GROUP_BUY_NOT_AVAILABLE", "此開團目前無法接受訂單。")

    product_ids = sorted({item.group_buy_product_id for item in items})
    locked_products = {
        p.id: p for p in group_buy_repository.get_group_buy_products_for_update(db, product_ids)
    }

    insufficient_items = []
    resolved = []
    for item in items:
        group_buy_product = locked_products.get(item.group_buy_product_id)
        if group_buy_product is None:
            raise AppError(404, "GROUP_BUY_PRODUCT_NOT_FOUND", "找不到指定的開團商品。")
        product = product_repository.get_by_id(db, group_buy_product.product_id)
        if item.chosen_character_id is not None:
            char_max = (
                group_buy_repository.get_character_max_quantity(
                    db, group_buy_product.id, item.chosen_character_id
                )
                or 0
            )
            occupied = order_repository.get_occupied_quantity(
                db, group_buy_product.id, item.chosen_character_id
            )
            available = max(char_max - occupied, 0)
        else:
            occupied = order_repository.get_occupied_quantity(db, group_buy_product.id)
            available = max(group_buy_product.max_quantity - occupied, 0)

        if not product.is_active or item.quantity > available:
            insufficient_items.append(
                {
                    "group_buy_product_id": str(group_buy_product.id),
                    "requested_quantity": item.quantity,
                    "available_quantity": available if product.is_active else 0,
                }
            )
        else:
            resolved.append((item, group_buy_product, product))

    if insufficient_items:
        raise AppError(
            409,
            "INSUFFICIENT_AVAILABLE_QUANTITY",
            "部分商品的可接受數量不足。",
            {"items": insufficient_items},
        )

    leader_profile = group_leader_repository.get_profile_by_id(db, group_buy.group_leader_profile_id)
    product_total_amount = sum(
        (group_buy_product.unit_price * item.quantity for item, group_buy_product, _ in resolved)
    )
    order_number = order_repository.generate_unique_order_number(db)

    order = order_repository.create_order(
        db,
        order_number=order_number,
        user_id=user.id,
        group_buy_id=group_buy.id,
        status=OrderStatus.PENDING_CONFIRMATION,
        product_total_amount=product_total_amount,
        group_leader_name_snapshot=leader_profile.display_name,
        activity_name_snapshot=activity.name,
        payment_method_snapshot=group_buy.payment_method,
        payment_method_note_snapshot=group_buy.payment_method_note,
        requires_second_payment_snapshot=group_buy.requires_second_payment,
        includes_full_gift_snapshot=group_buy.includes_full_gift,
        rules_snapshot=group_buy.rules,
        leader_contact_platform_snapshot=group_buy.contact_platform,
        leader_contact_value_snapshot=group_buy.contact_value,
        member_facebook_contact_snapshot=user.facebook_contact,
        member_discord_contact_snapshot=user.discord_contact,
        member_line_contact_snapshot=user.line_contact,
    )

    for item, group_buy_product, product in resolved:
        subtotal = group_buy_product.unit_price * item.quantity
        chosen_character_name = None
        if item.chosen_character_id is not None:
            chosen_character = character_repository.get_by_id(db, item.chosen_character_id)
            chosen_character_name = chosen_character.name if chosen_character else None
        order_repository.create_order_item(
            db,
            order_id=order.id,
            group_buy_product_id=group_buy_product.id,
            chosen_character_id=item.chosen_character_id,
            chosen_character_name_snapshot=chosen_character_name,
            product_name_snapshot=product.name,
            image_url_snapshot=product.primary_image_url,
            unit_price=group_buy_product.unit_price,
            quantity=item.quantity,
            subtotal=subtotal,
        )

    follow_list_repository.delete_follow_list(db, follow_list)

    db.commit()
    db.refresh(order)

    return CreateOrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        product_total_amount=order.product_total_amount,
        created_at=order.created_at,
    )


def _build_item_summary(items) -> str:
    first_name = items[0].product_name_snapshot
    if len(items) == 1:
        return first_name
    return f"{first_name}等 {len(items)} 項"


def get_my_orders(
    db: Session, user_id: uuid.UUID, status: OrderStatus | None, page: int, page_size: int
) -> tuple[list[OrderListItem], int]:
    orders, total = order_repository.list_by_user(db, user_id, status, page, page_size)
    results = []
    for order in orders:
        items = order_repository.get_items(db, order.id)
        results.append(
            OrderListItem(
                id=order.id,
                order_number=order.order_number,
                group_leader_name=order.group_leader_name_snapshot,
                activity_name=order.activity_name_snapshot,
                representative_image_url=items[0].image_url_snapshot if items else "",
                item_summary=_build_item_summary(items) if items else "",
                product_total_amount=order.product_total_amount,
                status=order.status,
                created_at=order.created_at,
            )
        )
    return results, total


def _cancellation_to_summary(request) -> CancellationRequestSummary:
    return CancellationRequestSummary(
        id=request.id,
        order_id=request.order_id,
        reason=request.reason,
        status=request.status,
        response_note=request.response_note,
        processed_at=request.processed_at,
        created_at=request.created_at,
    )


def get_my_order_detail(db: Session, user: AppUser, order_id: uuid.UUID) -> OrderDetailResponse:
    order = order_repository.get_by_id(db, order_id)
    if order is None or order.user_id != user.id:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")

    items = order_repository.get_items(db, order.id)
    cancellation_requests = cancellation_repository.list_by_order_id(db, order.id)
    pending = next(
        (r for r in cancellation_requests if r.status == CancellationStatus.PENDING), None
    )

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        rejection_reason=order.rejection_reason,
        product_total_amount=order.product_total_amount,
        group_leader_name=order.group_leader_name_snapshot,
        activity_name=order.activity_name_snapshot,
        payment_method=order.payment_method_snapshot,
        payment_method_note=order.payment_method_note_snapshot,
        requires_second_payment=order.requires_second_payment_snapshot,
        includes_full_gift=order.includes_full_gift_snapshot,
        rules=order.rules_snapshot,
        contact_platform=order.leader_contact_platform_snapshot,
        contact_value=order.leader_contact_value_snapshot,
        items=[
            OrderItemDetail(
                id=item.id,
                product_name_snapshot=item.product_name_snapshot,
                image_url_snapshot=item.image_url_snapshot,
                chosen_character_name=item.chosen_character_name_snapshot,
                unit_price=item.unit_price,
                quantity=item.quantity,
                subtotal=item.subtotal,
            )
            for item in items
        ],
        pending_cancellation_request=(
            _cancellation_to_summary(pending) if pending is not None else None
        ),
        cancellation_requests=[_cancellation_to_summary(r) for r in cancellation_requests],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
