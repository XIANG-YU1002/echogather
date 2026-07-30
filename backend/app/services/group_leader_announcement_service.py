import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.announcement import Announcement
from app.models.enums import AnnouncementAudienceScope, AnnouncementType
from app.models.group_leader import GroupLeaderProfile
from app.repositories import activity_repository, announcement_repository, group_buy_repository
from app.schemas.group_leader_announcement import (
    AnnouncementOwnerResponse,
    CreateAnnouncementRequest,
    RecipientPreviewResponse,
    UpdateAnnouncementRequest,
)
from app.services import notification_service


def _load_owned_announcement(
    db: Session, profile: GroupLeaderProfile, announcement_id: uuid.UUID
) -> Announcement:
    announcement = announcement_repository.get_by_id(db, announcement_id)
    if (
        announcement is None
        or announcement.announcement_type != AnnouncementType.GROUP_LEADER
        or announcement.group_leader_profile_id != profile.id
    ):
        raise AppError(404, "ANNOUNCEMENT_NOT_FOUND", "找不到指定的公告。")
    return announcement


def _group_buy_label(db: Session, group_buy_id: uuid.UUID | None) -> tuple[str | None, int | None]:
    """指定開團的活動名稱與輪次，供圖 27「目標與對象」欄顯示。"""
    if group_buy_id is None:
        return None, None
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None:
        return None, None
    activity = activity_repository.get_by_id(db, group_buy.activity_id)
    round_number = group_buy_repository.get_round_number(db, group_buy)
    return (activity.name if activity is not None else None), round_number


def _to_response(db: Session, announcement: Announcement) -> AnnouncementOwnerResponse:
    activity_name, round_number = _group_buy_label(db, announcement.group_buy_id)
    return AnnouncementOwnerResponse(
        id=announcement.id,
        audience_scope=announcement.audience_scope,
        group_buy_id=announcement.group_buy_id,
        group_buy_activity_name=activity_name,
        group_buy_round_number=round_number,
        title=announcement.title,
        content=announcement.content,
        is_public=announcement.is_public,
        recipient_count=announcement_repository.count_recipients(db, announcement.id),
        published_at=announcement.published_at,
        updated_at=announcement.updated_at,
    )


def preview_recipients(
    db: Session,
    profile: GroupLeaderProfile,
    *,
    audience_scope: AnnouncementAudienceScope,
    group_buy_id: uuid.UUID | None,
) -> RecipientPreviewResponse:
    """圖 27 表單的通知對象預覽：發布前算出收件人數與對象描述。

    刻意沿用 create_announcement 的同一組收件人查詢，避免預覽與實際發送不一致。
    """
    if audience_scope == AnnouncementAudienceScope.LEADER_UNFINISHED:
        recipient_ids = announcement_repository.get_leader_unfinished_recipient_user_ids(
            db, profile.id
        )
        return RecipientPreviewResponse(
            audience_scope=audience_scope,
            recipient_count=len(recipient_ids),
            audience_label="所有未完成訂單會員",
        )

    if group_buy_id is None:
        raise AppError(422, "VALIDATION_ERROR", "特定開團公告必須指定開團。")
    group_buy = group_buy_repository.get_by_id(db, group_buy_id)
    if group_buy is None:
        raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")
    if group_buy.group_leader_profile_id != profile.id:
        raise AppError(404, "GROUP_BUY_NOT_OWNED", "此開團不屬於你。")

    recipient_ids = announcement_repository.get_group_buy_unfinished_recipient_user_ids(
        db, group_buy.id
    )
    activity_name, _round_number = _group_buy_label(db, group_buy.id)
    return RecipientPreviewResponse(
        audience_scope=audience_scope,
        group_buy_id=group_buy.id,
        group_buy_activity_name=activity_name,
        recipient_count=len(recipient_ids),
        audience_label=f"{activity_name or '此開團'}未完成訂單會員",
    )


def create_announcement(
    db: Session, profile: GroupLeaderProfile, payload: CreateAnnouncementRequest
) -> AnnouncementOwnerResponse:
    """依 Business Rules §24：零收件人時僅公開公告允許發布，發布與通知同一 Transaction。"""
    if payload.audience_scope == AnnouncementAudienceScope.LEADER_UNFINISHED:
        recipient_ids = announcement_repository.get_leader_unfinished_recipient_user_ids(
            db, profile.id
        )
        group_buy_id = None
    else:
        group_buy = group_buy_repository.get_by_id(db, payload.group_buy_id)
        if group_buy is None:
            raise AppError(404, "GROUP_BUY_NOT_FOUND", "找不到指定的開團。")
        if group_buy.group_leader_profile_id != profile.id:
            raise AppError(404, "GROUP_BUY_NOT_OWNED", "此開團不屬於你。")
        recipient_ids = announcement_repository.get_group_buy_unfinished_recipient_user_ids(
            db, group_buy.id
        )
        group_buy_id = group_buy.id

    if not recipient_ids and not payload.is_public:
        raise AppError(
            409, "ANNOUNCEMENT_NO_RECIPIENTS", "沒有收件人時，公告必須設為公開才能發布。"
        )

    announcement = announcement_repository.create(
        db,
        announcement_type=AnnouncementType.GROUP_LEADER,
        audience_scope=payload.audience_scope,
        group_leader_profile_id=profile.id,
        group_buy_id=group_buy_id,
        created_by_user_id=profile.user_id,
        title=payload.title,
        content=payload.content,
        is_public=payload.is_public,
    )

    notification_service.notify_announcement_recipients(
        db,
        user_ids=recipient_ids,
        announcement_id=announcement.id,
        title=announcement.title,
        message=announcement.content,
    )

    db.commit()
    db.refresh(announcement)
    return _to_response(db, announcement)


def get_my_announcements(
    db: Session,
    profile: GroupLeaderProfile,
    *,
    audience_scope: AnnouncementAudienceScope | None,
    group_buy_id: uuid.UUID | None,
    is_public: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[AnnouncementOwnerResponse], int]:
    announcements, total = announcement_repository.list_by_leader(
        db,
        profile.id,
        audience_scope=audience_scope,
        group_buy_id=group_buy_id,
        is_public=is_public,
        page=page,
        page_size=page_size,
    )
    return [_to_response(db, a) for a in announcements], total


def get_my_announcement_detail(
    db: Session, profile: GroupLeaderProfile, announcement_id: uuid.UUID
) -> AnnouncementOwnerResponse:
    announcement = _load_owned_announcement(db, profile, announcement_id)
    return _to_response(db, announcement)


def update_announcement(
    db: Session,
    profile: GroupLeaderProfile,
    announcement_id: uuid.UUID,
    payload: UpdateAnnouncementRequest,
) -> AnnouncementOwnerResponse:
    """依 Business Rules §24.9：只能改標題/內容/是否公開，同步更新既有通知，不重建通知。"""
    announcement = _load_owned_announcement(db, profile, announcement_id)
    provided = payload.model_fields_set

    recipient_count = announcement_repository.count_recipients(db, announcement.id)
    new_is_public = payload.is_public if "is_public" in provided else announcement.is_public
    if recipient_count == 0 and not new_is_public:
        raise AppError(
            409, "ANNOUNCEMENT_NO_RECIPIENTS", "沒有收件人時，公告必須設為公開才能發布。"
        )

    if "title" in provided:
        announcement.title = payload.title
    if "content" in provided:
        announcement.content = payload.content
    if "is_public" in provided:
        announcement.is_public = payload.is_public

    if "title" in provided or "content" in provided:
        announcement_repository.sync_notifications_content(
            db, announcement.id, announcement.title, announcement.content
        )

    db.commit()
    db.refresh(announcement)
    return _to_response(db, announcement)


def delete_announcement(db: Session, profile: GroupLeaderProfile, announcement_id: uuid.UUID) -> None:
    """依 Business Rules §24.10：刪除公告時一併刪除其通知（由 FK CASCADE 保證），不影響其他通知。"""
    announcement = _load_owned_announcement(db, profile, announcement_id)
    announcement_repository.delete(db, announcement)
    db.commit()
