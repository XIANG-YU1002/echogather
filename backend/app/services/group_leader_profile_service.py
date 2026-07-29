import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import PENDING_ORDER_STATUSES, GroupBuyStatus
from app.models.group_leader import GroupLeaderProfile
from app.repositories import cancellation_repository, group_buy_repository, group_leader_repository, order_repository
from app.schemas.group_leader_group_buy import GroupBuyOwnerListItem
from app.schemas.group_leader_profile import (
    DashboardActivityGroup,
    DashboardCard,
    DashboardResponse,
    GroupLeaderProfileOwnerResponse,
    UpdateDefaultRulesRequest,
    UpdateGroupLeaderProfileRequest,
)
from app.services import group_leader_group_buy_service
from app.services.group_leader_service import is_profile_complete


def _to_response(profile: GroupLeaderProfile) -> GroupLeaderProfileOwnerResponse:
    return GroupLeaderProfileOwnerResponse(
        id=profile.id,
        display_name=profile.display_name,
        introduction=profile.introduction,
        default_rules=profile.default_rules,
        facebook_url=profile.facebook_url,
        discord_contact=profile.discord_contact,
        line_contact=profile.line_contact,
        is_profile_complete=is_profile_complete(profile),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def get_profile(profile: GroupLeaderProfile) -> GroupLeaderProfileOwnerResponse:
    return _to_response(profile)


def update_profile(
    db: Session, profile: GroupLeaderProfile, payload: UpdateGroupLeaderProfileRequest
) -> GroupLeaderProfileOwnerResponse:
    """依 Business Rules §9.2/§9.3：名稱設定後不可修改，聯絡方式至少保留一項。"""
    provided = payload.model_fields_set

    if "display_name" in provided and payload.display_name is not None:
        if profile.display_name is not None:
            raise AppError(409, "GROUP_LEADER_DISPLAY_NAME_IMMUTABLE", "團主名稱設定後不可修改。")
        if group_leader_repository.display_name_taken(db, payload.display_name, profile.id):
            raise AppError(
                409, "GROUP_LEADER_DISPLAY_NAME_UNAVAILABLE", "此團主名稱已被使用。"
            )
        profile.display_name = payload.display_name

    if "introduction" in provided:
        profile.introduction = payload.introduction

    facebook = payload.facebook_url if "facebook_url" in provided else profile.facebook_url
    discord = payload.discord_contact if "discord_contact" in provided else profile.discord_contact
    line = payload.line_contact if "line_contact" in provided else profile.line_contact

    if not (facebook or discord or line):
        raise AppError(422, "CONTACT_REQUIRED", "至少需要保留一項公開聯絡方式。")

    profile.facebook_url = facebook
    profile.discord_contact = discord
    profile.line_contact = line

    db.commit()
    db.refresh(profile)
    return _to_response(profile)


def update_default_rules(
    db: Session, profile: GroupLeaderProfile, payload: UpdateDefaultRulesRequest
) -> GroupLeaderProfileOwnerResponse:
    """依 Business Rules §9.4：只影響未來預填內容，不修改既有開團團規。"""
    profile.default_rules = payload.default_rules
    db.commit()
    db.refresh(profile)
    return _to_response(profile)


def get_dashboard(db: Session, profile: GroupLeaderProfile) -> DashboardResponse:
    """依 API Design §22.4 與圖 20：統計卡＋依活動分組的目前開團。

    圖 20 四張卡皆有「較昨日 +6 ↗」，但資料庫沒有每日統計快照，算不出昨天的數字，
    依使用者裁決不做該行（見 docs/目前進度.txt 第 6 批）。
    """
    open_group_buys = group_buy_repository.count_by_group_leader_and_status(
        db, profile.id, GroupBuyStatus.OPEN
    )
    # 依使用者 2026-07-29 說明：待確認與待付款都是團主要處理的，合計為一張「待處理訂單」卡。
    pending_orders = order_repository.count_for_leader_by_statuses(
        db, profile.id, PENDING_ORDER_STATUSES
    )
    pending_cancellation_requests = cancellation_repository.count_pending_for_leader(db, profile.id)
    upcoming_deadline = group_buy_repository.count_upcoming_deadline(db, profile.id)

    return DashboardResponse(
        cards=[
            DashboardCard(
                key="pending_orders",
                label="待處理訂單",
                count=pending_orders,
                target_url="/group-leader/orders?status=pending",
            ),
            DashboardCard(
                key="pending_cancellation_requests",
                label="待處理取消申請",
                count=pending_cancellation_requests,
                target_url="/group-leader/orders?has_pending_cancellation=true",
            ),
            DashboardCard(
                key="open_group_buys",
                label="進行中開團",
                count=open_group_buys,
                target_url="/group-leader/group-buys?status=open",
            ),
            DashboardCard(
                key="upcoming_deadline_group_buys",
                label=f"即將截止（{group_buy_repository.UPCOMING_DEADLINE_DAYS} 天內）",
                count=upcoming_deadline,
                target_url="/group-leader/group-buys?status=open",
            ),
        ],
        current_group_buys=_group_by_activity(
            group_leader_group_buy_service.get_my_open_group_buys(db, profile)
        ),
    )


def _group_by_activity(items: list[GroupBuyOwnerListItem]) -> list[DashboardActivityGroup]:
    """把開團清單依活動分組，活動順序沿用來源排序（最早截止的活動排前面）。"""
    groups: dict[uuid.UUID, DashboardActivityGroup] = {}
    for item in items:
        group = groups.get(item.activity.id)
        if group is None:
            group = DashboardActivityGroup(
                activity_id=item.activity.id,
                activity_name=item.activity.name,
                activity_image_url=item.activity.image_url,
                activity_status=item.activity.status,
                group_buys=[],
            )
            groups[item.activity.id] = group
        group.group_buys.append(item)
    return list(groups.values())
