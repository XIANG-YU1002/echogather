import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import UNMERGE_ALLOWED_STATUSES, CancellationStatus, OrderStatus
from app.models.user import AppUser
from app.repositories import (
    activity_repository,
    cancellation_repository,
    character_repository,
    follow_list_repository,
    group_buy_repository,
    group_leader_repository,
    order_merge_repository,
    order_repository,
    product_repository,
)
from app.schemas.common import normalize_optional_text
from app.schemas.order import (
    CancellationRequestSummary,
    CreateOrderResponse,
    MergedSourceOrderSummary,
    OrderDetailResponse,
    OrderItemDetail,
    OrderListItem,
    OrderStatusHistoryItem,
    UnmergeRequestSummary,
)
from app.services import availability_service, notification_service


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

    # 團主不可對自己開團的商品下單。
    own_profile = group_leader_repository.get_profile_by_user_id(db, user.id)
    if own_profile is not None and own_profile.id == group_buy.group_leader_profile_id:
        raise AppError(403, "CANNOT_ORDER_OWN_GROUP_BUY", "這是你自己的開團，無法對自己下單。")

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
    order_repository.create_status_history(db, order.id, OrderStatus.PENDING_CONFIRMATION)

    # 通知團主有新訂單待確認
    notification_service.notify_order_event(
        db,
        user_id=leader_profile.user_id,
        order_id=order.id,
        title="收到新訂單",
        message=f"會員 {user.nickname} 送出訂單 {order.order_number}，請盡快確認。",
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


def build_item_summary(items) -> str:
    """商品摘要文字。會員端訂單列表與團主端訂單列表共用同一種寫法。"""
    if not items:
        return ""
    first_name = items[0].product_name_snapshot
    if len(items) == 1:
        return first_name
    return f"{first_name}等 {len(items)} 項"


def describe_items(items) -> str:
    """逐項列出「商品名（角色）×數量」。

    合併通知要告知會員「被併掉的那筆訂單有什麼商品」（使用者 2026-07-30 需求），
    因此不能用 build_item_summary 的「首項等 N 項」寫法。
    """
    if not items:
        return "（無商品）"
    parts = []
    for item in items:
        name = item.product_name_snapshot
        if item.chosen_character_name_snapshot:
            name = f"{name}（{item.chosen_character_name_snapshot}）"
        parts.append(f"{name} ×{item.quantity}")
    return "、".join(parts)


def get_unmergeable_batch_id(db: Session, order) -> uuid.UUID | None:
    """這張訂單目前可以拆回的合併批次，沒有則回 None。

    只允許拆最新一批：二次合併（A+B→C，之後 C+D→C）時先拆舊批次會把新批次
    併進來的數量一起算掉。已有待處理的拆單申請時也回 None，避免重複申請。
    """
    if order.status not in UNMERGE_ALLOWED_STATUSES:
        return None
    batch_id = order_merge_repository.get_latest_active_batch_id(db, order.id)
    if batch_id is None:
        return None
    if order_merge_repository.get_pending_unmerge_request(db, order.id) is not None:
        return None
    return batch_id


def build_unmerge_summary(db: Session, request) -> UnmergeRequestSummary:
    """組拆單申請摘要，附上這批會拆回哪幾張訂單、各有什麼商品。"""
    records = order_merge_repository.get_batch(db, request.batch_id, only_active=False)
    sources = []
    for record in records:
        source = order_repository.get_by_id(db, record.source_order_id)
        if source is None:
            continue
        sources.append(
            MergedSourceOrderSummary(
                order_number=source.order_number,
                status_before=record.source_status_before,
                item_summary=describe_items(order_repository.get_items(db, source.id)),
                product_total_amount=source.product_total_amount,
                created_at=source.created_at,
            )
        )
    return UnmergeRequestSummary(
        id=request.id,
        order_id=request.order_id,
        batch_id=request.batch_id,
        reason=request.reason,
        status=request.status,
        response_note=request.response_note,
        processed_at=request.processed_at,
        created_at=request.created_at,
        source_orders=sources,
    )


def request_unmerge(
    db: Session, user: AppUser, order_id: uuid.UUID, reason: str | None
) -> UnmergeRequestSummary:
    """會員提出拆單（取消合併）申請，由團主核准後才真正拆開。

    對應圖 10 通知中心「訂單已合併」通知底下的「取消合併訂單」按鈕
    （使用者 2026-07-30 需求）。這裡只建立申請並通知團主，不改動任何訂單。
    """
    order = order_repository.get_by_id(db, order_id)
    if order is None or order.user_id != user.id or order.status == OrderStatus.MERGED:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")

    if order.status not in UNMERGE_ALLOWED_STATUSES:
        raise AppError(
            409,
            "UNMERGE_NOT_ALLOWED",
            "訂單目前狀態已無法取消合併，請直接聯絡團主。",
            {"status": order.status.value},
        )
    if order_merge_repository.get_pending_unmerge_request(db, order.id) is not None:
        raise AppError(
            409,
            "UNMERGE_REQUEST_ALREADY_PENDING",
            "已經有一筆待團主處理的取消合併申請。",
        )
    batch_id = order_merge_repository.get_latest_active_batch_id(db, order.id)
    if batch_id is None:
        raise AppError(409, "ORDER_NOT_MERGED", "這張訂單沒有可取消的合併紀錄。")

    request = order_merge_repository.create_unmerge_request(
        db, order_id=order.id, batch_id=batch_id, reason=normalize_optional_text(reason)
    )

    # 通知團主：同一筆訂單的通知寄給非下單者時，target_url 會導向團主端訂單詳情
    # （notification_service._source_and_target_url 既有邏輯）。
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    profile = group_leader_repository.get_profile_by_id(db, group_buy.group_leader_profile_id)
    if profile is not None:
        records = order_merge_repository.get_batch(db, batch_id)
        source_numbers = []
        for record in records:
            source = order_repository.get_by_id(db, record.source_order_id)
            if source is not None:
                source_numbers.append(source.order_number)
        notification_service.notify_order_event(
            db,
            user_id=profile.user_id,
            order_id=order.id,
            title="會員申請取消合併訂單",
            message=(
                f"會員 {user.nickname} 申請將訂單 {order.order_number} 拆回合併前的"
                f"{len(source_numbers) + 1} 張訂單（原訂單編號："
                f"{'、'.join(source_numbers) or '無'}）。"
                + (f"\n會員填寫的原因：{request.reason}" if request.reason else "")
                + "\n請在訂單詳情頁確認後執行拆單，或拒絕並說明原因。"
            ),
        )
        db.commit()

    return build_unmerge_summary(db, request)


def get_my_orders(
    db: Session,
    user_id: uuid.UUID,
    status: OrderStatus | None,
    page: int,
    page_size: int,
    *,
    activity_name: str | None = None,
    group_leader_name: str | None = None,
    created_within_days: int | None = None,
) -> tuple[list[OrderListItem], int]:
    orders, total = order_repository.list_by_user(
        db,
        user_id,
        status,
        page,
        page_size,
        activity_name=activity_name,
        group_leader_name=group_leader_name,
        created_within_days=created_within_days,
    )
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
                item_summary=build_item_summary(items),
                item_count=len(items),
                product_total_amount=order.product_total_amount,
                status=order.status,
                rejection_reason=order.rejection_reason,
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
    # 被合併掉的訂單在會員端視為已刪除（使用者 2026-07-30 裁決），連詳情頁都不給開，
    # 否則從舊通知或書籤點進來會看到一張已經不該存在的訂單。
    if order is None or order.user_id != user.id or order.status == OrderStatus.MERGED:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")

    items = order_repository.get_items(db, order.id)
    cancellation_requests = cancellation_repository.list_by_order_id(db, order.id)
    pending = next(
        (r for r in cancellation_requests if r.status == CancellationStatus.PENDING), None
    )
    status_history = order_repository.list_status_history(db, order.id)
    pending_unmerge = order_merge_repository.get_pending_unmerge_request(db, order.id)
    # 收單期限與團主公開頁連結取自開團本體（訂單未快照收單期限，依使用者決議取即時值）
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        rejection_reason=order.rejection_reason,
        product_total_amount=order.product_total_amount,
        group_leader_id=group_buy.group_leader_profile_id,
        deadline_at=group_buy.deadline_at,
        member_facebook_contact=order.member_facebook_contact_snapshot,
        member_discord_contact=order.member_discord_contact_snapshot,
        member_line_contact=order.member_line_contact_snapshot,
        status_history=[
            OrderStatusHistoryItem(status=h.status, note=h.note, created_at=h.created_at)
            for h in status_history
        ],
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
        can_request_unmerge=get_unmergeable_batch_id(db, order) is not None,
        pending_unmerge_request=(
            build_unmerge_summary(db, pending_unmerge) if pending_unmerge is not None else None
        ),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
