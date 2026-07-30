import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.activity import Activity
from app.models.enums import ActivityStatus
from app.repositories import activity_repository, product_repository
from app.schemas.admin_activity import (
    ActivityAdminDetailResponse,
    ActivityAdminListItem,
    CreateActivityRequest,
    UpdateActivityRequest,
)


def _load_activity_or_404(db: Session, activity_id: uuid.UUID) -> Activity:
    activity = activity_repository.get_by_id(db, activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "找不到指定的活動。")
    return activity


def _to_detail(db: Session, activity: Activity) -> ActivityAdminDetailResponse:
    return ActivityAdminDetailResponse(
        id=activity.id,
        name=activity.name,
        description=activity.description,
        image_url=activity.image_url,
        status=activity.status,
        has_full_gift=activity.has_full_gift,
        product_count=activity_repository.count_products_for_activity(db, activity.id),
        group_buy_count=activity_repository.count_group_buys_for_activity(db, activity.id),
        # 供前端鎖定商品幣別用（同一活動必須一致）
        product_currency=product_repository.get_activity_currency(db, activity.id),
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )


def create_activity(db: Session, payload: CreateActivityRequest) -> ActivityAdminDetailResponse:
    """依 Business Rules §10.3/§27.3：新增活動初始狀態固定為 open。"""
    activity = activity_repository.create_activity(
        db,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        has_full_gift=payload.has_full_gift,
        status=ActivityStatus.OPEN,
    )
    return _to_detail(db, activity)


def get_activities(
    db: Session, status: ActivityStatus | None, keyword: str | None, page: int, page_size: int
) -> tuple[list[ActivityAdminListItem], int]:
    activities, total = activity_repository.list_activities_admin(
        db, status=status, keyword=keyword, page=page, page_size=page_size
    )
    items = [
        ActivityAdminListItem(
            id=a.id,
            name=a.name,
            image_url=a.image_url,
            status=a.status,
            has_full_gift=a.has_full_gift,
            product_count=activity_repository.count_products_for_activity(db, a.id),
            created_at=a.created_at,
        )
        for a in activities
    ]
    return items, total


def get_activity_detail(db: Session, activity_id: uuid.UUID) -> ActivityAdminDetailResponse:
    activity = _load_activity_or_404(db, activity_id)
    return _to_detail(db, activity)


def update_activity(
    db: Session, activity_id: uuid.UUID, payload: UpdateActivityRequest
) -> ActivityAdminDetailResponse:
    activity = _load_activity_or_404(db, activity_id)
    provided = payload.model_fields_set

    if "name" in provided:
        activity.name = payload.name
    if "description" in provided:
        activity.description = payload.description
    if "image_url" in provided:
        activity.image_url = payload.image_url
    if "has_full_gift" in provided:
        activity.has_full_gift = payload.has_full_gift

    db.commit()
    return _to_detail(db, activity)


def end_activity(db: Session, activity_id: uuid.UUID) -> ActivityAdminDetailResponse:
    """依 Business Rules §10.3/§10.4：結束後不可建立新開團，既有開團繼續依原規則進行。"""
    activity = _load_activity_or_404(db, activity_id)
    if activity.status == ActivityStatus.ENDED:
        raise AppError(409, "ACTIVITY_ALREADY_ENDED", "活動已經結束。")
    activity.status = ActivityStatus.ENDED
    db.commit()
    return _to_detail(db, activity)


def reopen_activity(db: Session, activity_id: uuid.UUID) -> ActivityAdminDetailResponse:
    """依 Business Rules §10.4：重新開啟不影響已提前結單開團或已過期開團。"""
    activity = _load_activity_or_404(db, activity_id)
    if activity.status == ActivityStatus.OPEN:
        raise AppError(409, "ACTIVITY_ALREADY_OPEN", "活動目前已經是進行中狀態。")
    activity.status = ActivityStatus.OPEN
    db.commit()
    return _to_detail(db, activity)
