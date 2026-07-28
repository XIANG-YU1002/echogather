from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import GroupLeaderApplicationStatus
from app.models.group_leader import GroupLeaderApplication
from app.models.user import AppUser
from app.repositories import group_leader_repository
from app.schemas.group_leader_application import (
    ApplicationResponse,
    MyApplicationResponse,
    SubmitApplicationRequest,
)


def submit_application(
    db: Session, user: AppUser, payload: SubmitApplicationRequest | None = None
) -> GroupLeaderApplication:
    """依 Business Rules §8.2/§8.3：已有團主資料或已有待審核申請時不可再次申請。"""
    if group_leader_repository.get_profile_by_user_id(db, user.id) is not None:
        raise AppError(
            409, "GROUP_LEADER_PROFILE_ALREADY_EXISTS", "你已經是團主，無法再次申請。"
        )
    if group_leader_repository.get_pending_application_by_user_id(db, user.id) is not None:
        raise AppError(
            409, "GROUP_LEADER_APPLICATION_PENDING", "已有待審核的申請，請等待審核結果。"
        )

    application = GroupLeaderApplication(
        user_id=user.id,
        status=GroupLeaderApplicationStatus.PENDING,
        reason=payload.reason if payload is not None else None,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def get_my_application(db: Session, user: AppUser) -> MyApplicationResponse | None:
    latest = group_leader_repository.get_latest_application_by_user_id(db, user.id)
    if latest is None:
        return None

    has_profile = group_leader_repository.get_profile_by_user_id(db, user.id) is not None
    has_pending = latest.status == GroupLeaderApplicationStatus.PENDING
    can_reapply = not has_profile and not has_pending

    return MyApplicationResponse(
        id=latest.id,
        status=latest.status,
        reason=latest.reason,
        reviewed_at=latest.reviewed_at,
        created_at=latest.created_at,
        can_reapply=can_reapply,
    )


def application_to_response(application: GroupLeaderApplication) -> ApplicationResponse:
    return ApplicationResponse(
        id=application.id,
        status=application.status,
        reason=application.reason,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
    )
