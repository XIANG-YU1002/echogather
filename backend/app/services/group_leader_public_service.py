import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import GroupBuyStatus
from app.repositories import (
    activity_repository,
    announcement_repository,
    group_buy_repository,
    group_leader_repository,
    user_repository,
)
from app.schemas.announcement import PublicAnnouncementItem
from app.schemas.group_buy import GroupBuyActivitySummary, PublicGroupLeaderGroupBuyItem
from app.schemas.group_leader import (
    GroupLeaderSort,
    GroupLeaderStatistics,
    PublicContacts,
    PublicGroupLeaderProfileResponse,
)
from app.services import availability_service
from app.services.group_leader_service import is_profile_complete


def _load_complete_profile_or_404(db: Session, group_leader_profile_id: uuid.UUID):
    """依 Business Rules §14.6：只有完成公開資料的團主才有公開頁。"""
    profile = group_leader_repository.get_profile_by_id(db, group_leader_profile_id)
    if profile is None or not is_profile_complete(profile):
        raise AppError(404, "GROUP_LEADER_PROFILE_NOT_FOUND", "找不到指定的團主公開頁。")
    return profile


def list_public_profiles(
    db: Session,
    *,
    keyword: str | None,
    page: int,
    page_size: int,
    sort: GroupLeaderSort = GroupLeaderSort.CREATED_DESC,
) -> tuple[list[PublicGroupLeaderProfileResponse], int]:
    rows, total = group_leader_repository.list_public_profiles(
        db, keyword=keyword, page=page, page_size=page_size, sort=sort
    )
    items = []
    for profile, group_buy_count, completed_order_count in rows:
        user = user_repository.get_by_id(db, profile.user_id)
        items.append(
            PublicGroupLeaderProfileResponse(
                id=profile.id,
                display_name=profile.display_name,
                avatar_url=user.avatar_url if user is not None else None,
                introduction=profile.introduction,
                public_contacts=PublicContacts(
                    facebook=profile.facebook_url,
                    discord=profile.discord_contact,
                    line=profile.line_contact,
                ),
                created_at=profile.created_at,
                statistics=GroupLeaderStatistics(
                    group_buy_count=group_buy_count,
                    completed_order_count=completed_order_count,
                ),
                default_rules=profile.default_rules,
            )
        )
    return items, total


def get_public_profile(
    db: Session, group_leader_profile_id: uuid.UUID
) -> PublicGroupLeaderProfileResponse:
    profile = _load_complete_profile_or_404(db, group_leader_profile_id)
    user = user_repository.get_by_id(db, profile.user_id)
    statistics = group_leader_repository.get_public_statistics(db, profile.id)

    return PublicGroupLeaderProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=user.avatar_url if user is not None else None,
        introduction=profile.introduction,
        public_contacts=PublicContacts(
            facebook=profile.facebook_url,
            discord=profile.discord_contact,
            line=profile.line_contact,
        ),
        created_at=profile.created_at,
        statistics=GroupLeaderStatistics(**statistics),
        default_rules=profile.default_rules,
    )


def get_public_group_buys(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    status: GroupBuyStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[PublicGroupLeaderGroupBuyItem], int]:
    _load_complete_profile_or_404(db, group_leader_profile_id)
    group_buys = group_buy_repository.list_by_group_leader(db, group_leader_profile_id, status)

    total = len(group_buys)
    offset = (page - 1) * page_size
    page_rows = group_buys[offset : offset + page_size]

    items = []
    for group_buy in page_rows:
        activity = activity_repository.get_by_id(db, group_buy.activity_id)
        items.append(
            PublicGroupLeaderGroupBuyItem(
                id=group_buy.id,
                activity=GroupBuyActivitySummary.model_validate(activity, from_attributes=True),
                status=group_buy.status,
                effective_status=availability_service.compute_group_buy_level_status(
                    group_buy, activity
                ),
                deadline_at=group_buy.deadline_at,
                created_at=group_buy.created_at,
            )
        )
    return items, total


def get_public_announcements(
    db: Session, group_leader_profile_id: uuid.UUID
) -> list[PublicAnnouncementItem]:
    _load_complete_profile_or_404(db, group_leader_profile_id)
    announcements = announcement_repository.list_public_group_leader_announcements(
        db, group_leader_profile_id
    )
    return [PublicAnnouncementItem.model_validate(a, from_attributes=True) for a in announcements]
