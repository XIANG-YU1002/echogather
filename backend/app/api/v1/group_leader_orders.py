import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_active_group_leader_profile, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.enums import GroupLeaderOrderStatusFilter
from app.models.group_leader import GroupLeaderProfile
from app.schemas.group_leader_order import ProcessCancellationRequest, RejectOrderRequest
from app.services import group_leader_order_service

router = APIRouter(prefix="/group-leader", tags=["group-leader-orders"])


@router.get("/orders")
def get_orders(
    group_buy_id: uuid.UUID | None = Query(None),
    activity_id: uuid.UUID | None = Query(None),
    status: GroupLeaderOrderStatusFilter | None = Query(
        None, description="單一訂單狀態，或複合值 pending＝待處理（待確認＋待付款）"
    ),
    has_pending_cancellation: bool | None = Query(None),
    keyword: str | None = Query(None),
    newest_first: bool = Query(
        False,
        description="改為最新提交在前；預設依 Business Rules §24.1 先喊先得（最早在前）",
    ),
    pagination: PaginationParams = Depends(),
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    items, total, summary = group_leader_order_service.get_orders(
        db,
        profile,
        group_buy_id=group_buy_id,
        activity_id=activity_id,
        status=status,
        has_pending_cancellation=has_pending_cancellation,
        keyword=keyword,
        page=pagination.page,
        page_size=pagination.page_size,
        newest_first=newest_first,
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items],
        pagination.page,
        pagination.page_size,
        total,
        summary=summary.model_dump(mode="json"),
    )


@router.get("/orders/{order_id}")
def get_order_detail(
    order_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = group_leader_order_service.get_order_detail(db, profile, order_id)
    return envelope(result.model_dump(mode="json"))


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    order = group_leader_order_service.accept_order(db, profile, order_id)
    return envelope({"id": str(order.id), "status": order.status.value})


@router.post("/orders/{order_id}/reject")
def reject_order(
    order_id: uuid.UUID,
    payload: RejectOrderRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    order = group_leader_order_service.reject_order(db, profile, order_id, payload.reason)
    return envelope(
        {
            "id": str(order.id),
            "status": order.status.value,
            "rejection_reason": order.rejection_reason,
        }
    )


@router.post("/orders/{order_id}/mark-paid")
def mark_paid(
    order_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    order = group_leader_order_service.mark_paid(db, profile, order_id)
    return envelope({"id": str(order.id), "status": order.status.value})


@router.post("/group-buys/{group_buy_id}/orders/mark-all-shipped")
def mark_all_shipped(
    group_buy_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    """一鍵將該開團所有「已付款」訂單標記為已出貨。"""
    result = group_leader_order_service.mark_all_shipped(db, profile, group_buy_id)
    return envelope(result)


@router.post("/orders/{order_id}/mark-shipped")
def mark_shipped(
    order_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    order = group_leader_order_service.mark_shipped(db, profile, order_id)
    return envelope({"id": str(order.id), "status": order.status.value})


@router.post("/orders/{order_id}/complete")
def complete_order(
    order_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    order = group_leader_order_service.complete_order(db, profile, order_id)
    return envelope({"id": str(order.id), "status": order.status.value})


@router.post("/cancellation-requests/{request_id}/approve")
def approve_cancellation(
    request_id: uuid.UUID,
    payload: ProcessCancellationRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = group_leader_order_service.approve_cancellation(
        db, profile, request_id, payload.response_note
    )
    return envelope(result.model_dump(mode="json"))


@router.post("/cancellation-requests/{request_id}/reject")
def reject_cancellation(
    request_id: uuid.UUID,
    payload: ProcessCancellationRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = group_leader_order_service.reject_cancellation(
        db, profile, request_id, payload.response_note
    )
    return envelope(result.model_dump(mode="json"))
