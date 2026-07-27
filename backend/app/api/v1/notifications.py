import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_user, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.enums import NotificationType
from app.models.user import AppUser
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def get_notifications(
    notification_type: NotificationType | None = Query(None),
    is_read: bool | None = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = notification_service.list_notifications(
        db,
        current_user.id,
        notification_type=notification_type,
        is_read=is_read,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items], pagination.page, pagination.page_size, total
    )


@router.get("/unread-count")
def get_unread_count(
    current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    result = notification_service.get_unread_count(db, current_user.id)
    return envelope(result.model_dump(mode="json"))


@router.get("/summary")
def get_summary(
    current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """圖 10 右側「通知摘要」：未讀總數與各類型總筆數。"""
    result = notification_service.get_summary(db, current_user.id)
    return envelope(result.model_dump(mode="json"))


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    notification_service.mark_notification_read(db, current_user.id, notification_id)
    return envelope({"id": str(notification_id), "is_read": True})


@router.patch("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    notification_service.mark_all_notifications_read(db, current_user.id)
    return envelope({"success": True})
