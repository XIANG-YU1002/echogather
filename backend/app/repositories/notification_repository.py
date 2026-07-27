import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.notification import Notification


def get_by_id(db: Session, notification_id: uuid.UUID) -> Notification | None:
    return db.get(Notification, notification_id)


def list_by_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    notification_type: NotificationType | None,
    is_read: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if notification_type is not None:
        stmt = stmt.where(Notification.notification_type == notification_type)
    if is_read is not None:
        stmt = stmt.where(Notification.is_read.is_(is_read))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total


def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return db.execute(stmt).scalar_one()


def count_by_type(db: Session, user_id: uuid.UUID) -> dict[str, int]:
    """回傳各通知類型的總筆數（圖 10 右側「通知摘要」用）。"""
    stmt = (
        select(Notification.notification_type, func.count())
        .where(Notification.user_id == user_id)
        .group_by(Notification.notification_type)
    )
    return {row[0].value: row[1] for row in db.execute(stmt).all()}


def mark_read(db: Session, notification: Notification) -> None:
    """依 Business Rules §26.3：重複標記已讀不更新原 read_at。"""
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()


def mark_all_read(db: Session, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    stmt = select(Notification).where(
        Notification.user_id == user_id, Notification.is_read.is_(False)
    )
    for notification in db.execute(stmt).scalars().all():
        notification.is_read = True
        notification.read_at = now
    db.commit()
