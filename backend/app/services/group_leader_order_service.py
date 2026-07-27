import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import CancellationStatus, OrderStatus
from app.models.group_leader import GroupLeaderProfile
from app.models.order import CancellationRequest, GroupOrder
from app.repositories import cancellation_repository, group_buy_repository, order_repository, user_repository
from app.schemas.common import normalize_optional_text
from app.schemas.group_leader_order import (
    GroupLeaderOrderDetailResponse,
    GroupLeaderOrderListItem,
    MemberContactSnapshot,
)
from app.schemas.order import CancellationRequestSummary, OrderItemDetail
from app.services import notification_service

_CANCELLABLE_STATUSES = {
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
}

_AVAILABLE_ACTIONS_BY_STATUS = {
    OrderStatus.PENDING_CONFIRMATION: ["accept", "reject"],
    OrderStatus.PENDING_PAYMENT: ["mark-paid"],
    OrderStatus.PAID: ["mark-shipped"],
    OrderStatus.SHIPPED: ["complete"],
}


def _load_owned_order(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID, *, for_update: bool = False
) -> GroupOrder:
    order = order_repository.get_by_id(db, order_id, for_update=for_update)
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "找不到指定的訂單。")
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "ORDER_NOT_OWNED_BY_GROUP_LEADER", "此訂單不屬於你管理的開團。")
    return order


def _cancellation_to_summary(request: CancellationRequest) -> CancellationRequestSummary:
    return CancellationRequestSummary(
        id=request.id,
        order_id=request.order_id,
        reason=request.reason,
        status=request.status,
        response_note=request.response_note,
        processed_at=request.processed_at,
        created_at=request.created_at,
    )


def get_orders(
    db: Session,
    profile: GroupLeaderProfile,
    *,
    group_buy_id: uuid.UUID | None,
    activity_id: uuid.UUID | None,
    status: OrderStatus | None,
    has_pending_cancellation: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[GroupLeaderOrderListItem], int]:
    orders, total = order_repository.list_for_leader(
        db,
        profile.id,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        status=status,
        has_pending_cancellation=has_pending_cancellation,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = []
    for order in orders:
        member = user_repository.get_by_id(db, order.user_id)
        has_pending = cancellation_repository.get_pending_by_order_id(db, order.id) is not None
        items.append(
            GroupLeaderOrderListItem(
                id=order.id,
                order_number=order.order_number,
                member_nickname=member.nickname if member is not None else "",
                group_buy_id=order.group_buy_id,
                activity_name=order.activity_name_snapshot,
                status=order.status,
                product_total_amount=order.product_total_amount,
                has_pending_cancellation=has_pending,
                created_at=order.created_at,
            )
        )
    return items, total


def get_order_detail(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID
) -> GroupLeaderOrderDetailResponse:
    order = _load_owned_order(db, profile, order_id)
    member = user_repository.get_by_id(db, order.user_id)
    items = order_repository.get_items(db, order.id)
    cancellation_requests = cancellation_repository.list_by_order_id(db, order.id)
    pending = next(
        (r for r in cancellation_requests if r.status == CancellationStatus.PENDING), None
    )

    return GroupLeaderOrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        rejection_reason=order.rejection_reason,
        product_total_amount=order.product_total_amount,
        member_nickname=member.nickname if member is not None else "",
        member_contacts=MemberContactSnapshot(
            facebook=order.member_facebook_contact_snapshot,
            discord=order.member_discord_contact_snapshot,
            line=order.member_line_contact_snapshot,
        ),
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
        available_actions=_AVAILABLE_ACTIONS_BY_STATUS.get(order.status, []),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _transition(
    db: Session,
    profile: GroupLeaderProfile,
    order_id: uuid.UUID,
    *,
    from_status: OrderStatus,
    to_status: OrderStatus,
    note: str | None = None,
) -> GroupOrder:
    order = _load_owned_order(db, profile, order_id, for_update=True)
    if order.status != from_status:
        raise AppError(
            409,
            "ORDER_STATUS_CONFLICT",
            "訂單狀態已變更，請重新載入資料。",
            {"current_status": order.status.value},
        )
    order.status = to_status
    order_repository.create_status_history(db, order.id, to_status, note)
    return order


def accept_order(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    """依 Business Rules §21.3：pending_confirmation -> pending_payment，並建立會員通知。"""
    order = _transition(
        db,
        profile,
        order_id,
        from_status=OrderStatus.PENDING_CONFIRMATION,
        to_status=OrderStatus.PENDING_PAYMENT,
    )
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已受理",
        message=f"你的訂單 {order.order_number} 已受理，請留意付款通知。",
    )
    db.commit()
    db.refresh(order)
    return order


def reject_order(
    db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID, reason: str
) -> GroupOrder:
    """依 Business Rules §21.4：pending_confirmation -> rejected，拒絕原因必填且不可修改。"""
    normalized_reason = normalize_optional_text(reason)
    if not normalized_reason:
        raise AppError(422, "ORDER_REJECTION_REASON_REQUIRED", "請填寫拒絕原因。")

    order = _transition(
        db,
        profile,
        order_id,
        from_status=OrderStatus.PENDING_CONFIRMATION,
        to_status=OrderStatus.REJECTED,
        note=normalized_reason,
    )
    order.rejection_reason = normalized_reason
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已被拒絕",
        message=f"你的訂單 {order.order_number} 已被拒絕：{normalized_reason}",
    )
    db.commit()
    db.refresh(order)
    return order


def mark_paid(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.PENDING_PAYMENT, to_status=OrderStatus.PAID
    )
    db.commit()
    db.refresh(order)
    return order


def mark_shipped(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.PAID, to_status=OrderStatus.SHIPPED
    )
    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="訂單已出貨",
        message=f"你的訂單 {order.order_number} 已由團主出貨，收到商品後請與團主確認完成。",
    )
    db.commit()
    db.refresh(order)
    return order


def mark_all_shipped(
    db: Session, profile: GroupLeaderProfile, group_buy_id: uuid.UUID
) -> dict:
    """一鍵將指定開團中所有「已付款」訂單標記為已出貨。

    只處理 paid 狀態的訂單；其餘狀態（待確認、待付款、已出貨、已完成、已拒絕、已取消）
    一律略過，並在回應中回報略過筆數，讓團主知道還有多少張沒進到可出貨狀態。
    """
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None or group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")

    orders = order_repository.list_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PAID, for_update=True
    )
    pending_confirmation = order_repository.count_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PENDING_CONFIRMATION
    )
    pending_payment = order_repository.count_by_group_buy_and_status(
        db, group_buy_id, OrderStatus.PENDING_PAYMENT
    )

    for order in orders:
        order.status = OrderStatus.SHIPPED
        order_repository.create_status_history(db, order.id, OrderStatus.SHIPPED)
        notification_service.notify_order_event(
            db,
            user_id=order.user_id,
            order_id=order.id,
            title="訂單已出貨",
            message=f"你的訂單 {order.order_number} 已由團主出貨，收到商品後請與團主確認完成。",
        )

    db.commit()
    return {
        "shipped_count": len(orders),
        "skipped_pending_confirmation": pending_confirmation,
        "skipped_pending_payment": pending_payment,
    }


def complete_order(db: Session, profile: GroupLeaderProfile, order_id: uuid.UUID) -> GroupOrder:
    order = _transition(
        db, profile, order_id, from_status=OrderStatus.SHIPPED, to_status=OrderStatus.COMPLETED
    )
    db.commit()
    db.refresh(order)
    return order


def _load_owned_cancellation_request(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID
) -> tuple[CancellationRequest, GroupOrder]:
    request = cancellation_repository.get_by_id(db, request_id, for_update=True)
    if request is None:
        raise AppError(404, "CANCELLATION_REQUEST_NOT_FOUND", "找不到指定的取消申請。")
    order = order_repository.get_by_id(db, request.order_id, for_update=True)
    group_buy = group_buy_repository.get_by_id(db, order.group_buy_id)
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "CANCELLATION_REQUEST_NOT_FOUND", "找不到指定的取消申請。")
    return request, order


def approve_cancellation(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> CancellationRequestSummary:
    """依 Business Rules §22.6：核准前重新確認訂單仍可取消，並原子更新訂單狀態與通知。"""
    request, order = _load_owned_cancellation_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "CANCELLATION_REQUEST_ALREADY_PROCESSED", "此取消申請已被處理。")
    if order.status not in _CANCELLABLE_STATUSES:
        raise AppError(409, "CANCELLATION_NOT_ALLOWED", "訂單目前狀態已不可取消。")

    now = datetime.now(timezone.utc)
    request.status = CancellationStatus.APPROVED
    request.response_note = normalize_optional_text(response_note)
    request.processed_at = now
    order.status = OrderStatus.CANCELLED
    order_repository.create_status_history(
        db, order.id, OrderStatus.CANCELLED, request.response_note
    )

    notification_service.notify_order_event(
        db,
        user_id=order.user_id,
        order_id=order.id,
        title="取消申請已核准",
        message=f"你的訂單 {order.order_number} 取消申請已核准。",
    )
    db.commit()
    db.refresh(request)
    return _cancellation_to_summary(request)


def reject_cancellation(
    db: Session, profile: GroupLeaderProfile, request_id: uuid.UUID, response_note: str | None
) -> CancellationRequestSummary:
    """依 Business Rules §22.7：拒絕後訂單狀態維持原狀，會員可再次申請。"""
    request, _order = _load_owned_cancellation_request(db, profile, request_id)
    if request.status != CancellationStatus.PENDING:
        raise AppError(409, "CANCELLATION_REQUEST_ALREADY_PROCESSED", "此取消申請已被處理。")

    request.status = CancellationStatus.REJECTED
    request.response_note = normalize_optional_text(response_note)
    request.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)
    return _cancellation_to_summary(request)
