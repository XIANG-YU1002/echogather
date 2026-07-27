import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.announcement import Announcement
from app.models.enums import AnnouncementAudienceScope, AnnouncementType, NotificationType
from app.models.group_leader import GroupLeaderProfile
from app.models.notification import Notification
from app.models.order import GroupOrder
from app.models.user import AppUser
from app.repositories import notification_repository
from app.schemas.notification import (
    NotificationItem,
    NotificationSource,
    NotificationSummaryResponse,
    UnreadCountResponse,
)


def notify_order_event(
    db: Session, *, user_id: uuid.UUID, order_id: uuid.UUID, title: str, message: str
) -> Notification:
    """建立系統通知（訂單狀態變更／取消申請結果），呼叫端需與相關狀態變更同一次 commit。"""
    notification = Notification(
        user_id=user_id,
        notification_type=NotificationType.SYSTEM,
        title=title,
        message=message,
        order_id=order_id,
    )
    db.add(notification)
    return notification


def notify_application_result(
    db: Session, *, user_id: uuid.UUID, application_id: uuid.UUID, title: str, message: str
) -> None:
    """依 Business Rules §8.6/§8.7/§26.2：團主申請審核結果使用系統通知。"""
    db.add(
        Notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM,
            title=title,
            message=message,
            group_leader_application_id=application_id,
        )
    )


def notify_announcement_recipients(
    db: Session,
    *,
    user_ids: list[uuid.UUID],
    announcement_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.GROUP_LEADER,
) -> None:
    """依 Business Rules §24.4/§25.2：同一會員同一公告只建立一則通知（呼叫端需先去重 user_ids）。"""
    for user_id in user_ids:
        db.add(
            Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                announcement_id=announcement_id,
            )
        )


def _source_and_target_url(db: Session, notification: Notification) -> tuple[NotificationSource, str | None]:
    """依 Business Rules §26.5：依通知來源決定導向頁面。"""
    if notification.order_id is not None:
        source = NotificationSource(type="order", id=str(notification.order_id))
        # 同一筆訂單的通知可能寄給下單會員或該團團主，兩者的訂單頁不同。
        # 收件人不是下單者時視為團主，導向團主端訂單詳情。
        order = db.get(GroupOrder, notification.order_id)
        if order is not None and order.user_id != notification.user_id:
            return source, f"/group-leader/orders/{notification.order_id}"
        return source, f"/orders/{notification.order_id}"

    if notification.announcement_id is not None:
        source = NotificationSource(type="announcement", id=str(notification.announcement_id))
        announcement = db.get(Announcement, notification.announcement_id)
        if (
            announcement is not None
            and announcement.is_public
            and announcement.announcement_type == AnnouncementType.GROUP_LEADER
        ):
            if announcement.audience_scope == AnnouncementAudienceScope.LEADER_UNFINISHED:
                return source, f"/group-leaders/{announcement.group_leader_profile_id}"
            if announcement.audience_scope == AnnouncementAudienceScope.GROUP_BUY_UNFINISHED:
                return source, f"/group-buys/{announcement.group_buy_id}"
        return source, None

    if notification.group_leader_application_id is not None:
        return (
            NotificationSource(
                type="group_leader_application", id=str(notification.group_leader_application_id)
            ),
            "/profile",
        )

    return NotificationSource(type="unknown", id=None), None


def _announcement_actor(db: Session, notification: Notification) -> tuple[str | None, str | None]:
    """團主公告的發布者名稱與頭像（依圖 10 於通知列表顯示團主頭像）。

    平台公告與系統通知沒有發布者頭像，回傳 (None, None)。
    """
    if notification.announcement_id is None:
        return None, None
    announcement = db.get(Announcement, notification.announcement_id)
    if announcement is None or announcement.group_leader_profile_id is None:
        return None, None
    profile = db.get(GroupLeaderProfile, announcement.group_leader_profile_id)
    if profile is None:
        return None, None
    user = db.get(AppUser, profile.user_id)
    return profile.display_name, (user.avatar_url if user is not None else None)


def _to_item(db: Session, notification: Notification) -> NotificationItem:
    source, target_url = _source_and_target_url(db, notification)
    actor_name, actor_avatar_url = _announcement_actor(db, notification)
    return NotificationItem(
        id=notification.id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        read_at=notification.read_at,
        source=source,
        target_url=target_url,
        actor_name=actor_name,
        actor_avatar_url=actor_avatar_url,
        created_at=notification.created_at,
    )


def list_notifications(
    db: Session,
    user_id: uuid.UUID,
    *,
    notification_type: NotificationType | None,
    is_read: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[NotificationItem], int]:
    notifications, total = notification_repository.list_by_user(
        db,
        user_id,
        notification_type=notification_type,
        is_read=is_read,
        page=page,
        page_size=page_size,
    )
    return [_to_item(db, n) for n in notifications], total


def get_unread_count(db: Session, user_id: uuid.UUID) -> UnreadCountResponse:
    return UnreadCountResponse(unread_count=notification_repository.get_unread_count(db, user_id))


def get_summary(db: Session, user_id: uuid.UUID) -> NotificationSummaryResponse:
    """圖 10 右側「通知摘要」：未讀總數，加上各類型的總筆數（含已讀）。"""
    counts = notification_repository.count_by_type(db, user_id)
    return NotificationSummaryResponse(
        unread_count=notification_repository.get_unread_count(db, user_id),
        system_count=counts.get(NotificationType.SYSTEM.value, 0),
        group_leader_count=counts.get(NotificationType.GROUP_LEADER.value, 0),
    )


def mark_notification_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    notification = notification_repository.get_by_id(db, notification_id)
    if notification is None or notification.user_id != user_id:
        raise AppError(404, "RESOURCE_NOT_FOUND", "找不到指定的通知。")
    notification_repository.mark_read(db, notification)


def mark_all_notifications_read(db: Session, user_id: uuid.UUID) -> None:
    notification_repository.mark_all_read(db, user_id)
