import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import GroupLeaderApplicationStatus
from app.models.group_leader import GroupLeaderApplication
from app.models.user import AppUser
from app.repositories import group_leader_repository, user_repository
from app.schemas.admin_group_leader_application import (
    ApplicationAdminDetailResponse,
    ApplicationAdminListItem,
    ApplicationUserRef,
    ApproveApplicationResponse,
    RejectApplicationResponse,
    ReviewedApplicationSummary,
    ReviewedGroupLeaderProfileSummary,
)
from app.services import notification_service
from app.services.group_leader_service import is_profile_complete


def _load_application_or_404(db: Session, application_id: uuid.UUID) -> GroupLeaderApplication:
    application = group_leader_repository.get_application_by_id(db, application_id)
    if application is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "找不到指定的申請。")
    return application


def _to_list_item(db: Session, application: GroupLeaderApplication) -> ApplicationAdminListItem:
    user = user_repository.get_by_id(db, application.user_id)
    return ApplicationAdminListItem(
        id=application.id,
        user=ApplicationUserRef.model_validate(user, from_attributes=True),
        status=application.status,
        reason=application.reason,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
    )


def get_applications(
    db: Session,
    *,
    status: GroupLeaderApplicationStatus | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ApplicationAdminListItem], int]:
    applications, total = group_leader_repository.list_applications_admin(
        db, status=status, keyword=keyword, page=page, page_size=page_size
    )
    return [_to_list_item(db, a) for a in applications], total


def get_application_detail(
    db: Session, application_id: uuid.UUID
) -> ApplicationAdminDetailResponse:
    application = _load_application_or_404(db, application_id)
    user = user_repository.get_by_id(db, application.user_id)
    return ApplicationAdminDetailResponse(
        id=application.id,
        user=ApplicationUserRef.model_validate(user, from_attributes=True),
        status=application.status,
        reason=application.reason,
        reviewed_by=application.reviewed_by_user_id,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
    )


def approve_application(
    db: Session, admin_user: AppUser, application_id: uuid.UUID
) -> ApproveApplicationResponse:
    """依 Business Rules §8.6：同一 Transaction 內確認 pending、建立不完整團主資料並通知。"""
    application = _load_application_or_404(db, application_id)
    if application.status != GroupLeaderApplicationStatus.PENDING:
        raise AppError(409, "APPLICATION_ALREADY_REVIEWED", "此申請已經審核過。")
    if group_leader_repository.get_profile_by_user_id(db, application.user_id) is not None:
        raise AppError(409, "GROUP_LEADER_PROFILE_ALREADY_EXISTS", "此會員已經是團主。")

    now = datetime.now(timezone.utc)
    application.status = GroupLeaderApplicationStatus.APPROVED
    application.reviewed_by_user_id = admin_user.id
    application.reviewed_at = now

    profile = group_leader_repository.create_profile(db, application.user_id)

    notification_service.notify_application_result(
        db,
        user_id=application.user_id,
        application_id=application.id,
        title="團主申請已通過",
        message="你的團主申請已通過，請完成團主公開資料設定。",
    )

    db.commit()
    db.refresh(application)
    db.refresh(profile)

    return ApproveApplicationResponse(
        application=ReviewedApplicationSummary(
            id=application.id, status=application.status, reviewed_at=application.reviewed_at
        ),
        group_leader_profile=ReviewedGroupLeaderProfileSummary(
            id=profile.id,
            display_name=profile.display_name,
            is_profile_complete=is_profile_complete(profile),
        ),
    )


def reject_application(
    db: Session, admin_user: AppUser, application_id: uuid.UUID
) -> RejectApplicationResponse:
    """依 Business Rules §8.7：拒絕不建立團主資料，會員可再次申請。"""
    application = _load_application_or_404(db, application_id)
    if application.status != GroupLeaderApplicationStatus.PENDING:
        raise AppError(409, "APPLICATION_ALREADY_REVIEWED", "此申請已經審核過。")

    application.status = GroupLeaderApplicationStatus.REJECTED
    application.reviewed_by_user_id = admin_user.id
    application.reviewed_at = datetime.now(timezone.utc)

    notification_service.notify_application_result(
        db,
        user_id=application.user_id,
        application_id=application.id,
        title="團主申請未通過",
        message="很抱歉，你的團主申請未通過審核。",
    )

    db.commit()
    db.refresh(application)

    return RejectApplicationResponse(
        application=ReviewedApplicationSummary(
            id=application.id, status=application.status, reviewed_at=application.reviewed_at
        )
    )
