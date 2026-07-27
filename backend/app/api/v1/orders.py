import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_user, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.enums import OrderStatus
from app.models.user import AppUser
from app.schemas.order import CreateCancellationRequestRequest, CreateOrderRequest
from app.services import cancellation_service, order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: CreateOrderRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = order_service.create_order(db, current_user, payload.rules_accepted)
    return envelope(result.model_dump(mode="json"))


@router.get("")
def get_my_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    activity_name: str | None = Query(None, max_length=150),
    group_leader_name: str | None = Query(None, max_length=50),
    created_within_days: int | None = Query(None, ge=1, le=365),
    pagination: PaginationParams = Depends(),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = order_service.get_my_orders(
        db,
        current_user.id,
        status_filter,
        pagination.page,
        pagination.page_size,
        activity_name=activity_name,
        group_leader_name=group_leader_name,
        created_within_days=created_within_days,
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items], pagination.page, pagination.page_size, total
    )


@router.get("/{order_id}")
def get_my_order_detail(
    order_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = order_service.get_my_order_detail(db, current_user, order_id)
    return envelope(result.model_dump(mode="json"))


@router.post("/{order_id}/cancellation-requests", status_code=status.HTTP_201_CREATED)
def create_cancellation_request(
    order_id: uuid.UUID,
    payload: CreateCancellationRequestRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = cancellation_service.create_cancellation_request(
        db, current_user, order_id, payload.reason
    )
    return envelope(result.model_dump(mode="json"))
