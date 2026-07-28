import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import GroupLeaderApplicationStatus, OrderStatus
from app.models.group_buy import GroupBuy
from app.models.group_leader import GroupLeaderApplication, GroupLeaderProfile
from app.models.order import GroupOrder
from app.models.user import AppUser
from app.schemas.group_leader import GroupLeaderSort


def get_profile_by_user_id(db: Session, user_id: uuid.UUID) -> GroupLeaderProfile | None:
    stmt = select(GroupLeaderProfile).where(GroupLeaderProfile.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_profile_by_id(db: Session, profile_id: uuid.UUID) -> GroupLeaderProfile | None:
    return db.get(GroupLeaderProfile, profile_id)


def display_name_taken(
    db: Session, display_name: str, exclude_profile_id: uuid.UUID | None = None
) -> bool:
    stmt = select(GroupLeaderProfile).where(
        func.lower(GroupLeaderProfile.display_name) == display_name.lower()
    )
    if exclude_profile_id is not None:
        stmt = stmt.where(GroupLeaderProfile.id != exclude_profile_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def get_pending_application_by_user_id(
    db: Session, user_id: uuid.UUID
) -> GroupLeaderApplication | None:
    stmt = select(GroupLeaderApplication).where(
        GroupLeaderApplication.user_id == user_id,
        GroupLeaderApplication.status == "pending",
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_application_by_user_id(
    db: Session, user_id: uuid.UUID
) -> GroupLeaderApplication | None:
    stmt = (
        select(GroupLeaderApplication)
        .where(GroupLeaderApplication.user_id == user_id)
        .order_by(GroupLeaderApplication.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_public_statistics(db: Session, group_leader_profile_id: uuid.UUID) -> dict:
    """依 API Design §21.1：公開頁顯示開團數與完成訂單數。"""
    group_buy_count = db.execute(
        select(func.count())
        .select_from(GroupBuy)
        .where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    ).scalar_one()

    completed_order_count = db.execute(
        select(func.count())
        .select_from(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupOrder.status == OrderStatus.COMPLETED,
        )
    ).scalar_one()

    return {"group_buy_count": group_buy_count, "completed_order_count": completed_order_count}


def get_application_by_id(db: Session, application_id: uuid.UUID) -> GroupLeaderApplication | None:
    return db.get(GroupLeaderApplication, application_id)


def count_pending_applications(db: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupLeaderApplication)
        .where(GroupLeaderApplication.status == GroupLeaderApplicationStatus.PENDING)
    )
    return db.execute(stmt).scalar_one()


def list_applications_admin(
    db: Session,
    *,
    status: GroupLeaderApplicationStatus | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[GroupLeaderApplication], int]:
    """依 Business Rules §27.2：待審核申請依較早申請優先顯示（created_at ASC）。"""
    stmt = select(GroupLeaderApplication)
    if status is not None:
        stmt = stmt.where(GroupLeaderApplication.status == status)
    if keyword:
        stmt = stmt.join(AppUser, AppUser.id == GroupLeaderApplication.user_id).where(
            AppUser.nickname.ilike(f"%{keyword}%") | AppUser.email.ilike(f"%{keyword}%")
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    order_column = (
        GroupLeaderApplication.created_at.asc()
        if status == GroupLeaderApplicationStatus.PENDING
        else GroupLeaderApplication.created_at.desc()
    )
    items = (
        db.execute(stmt.order_by(order_column).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return items, total


def create_profile(db: Session, user_id: uuid.UUID) -> GroupLeaderProfile:
    profile = GroupLeaderProfile(user_id=user_id)
    db.add(profile)
    db.flush()
    return profile


def list_public_profiles(
    db: Session,
    *,
    keyword: str | None,
    page: int,
    page_size: int,
    sort: GroupLeaderSort = GroupLeaderSort.CREATED_DESC,
) -> tuple[list[tuple[GroupLeaderProfile, int, int]], int]:
    """公開團主列表：僅列出已完成公開資料（display_name 已設定）的團主。

    統計值以相關子查詢一併取回（而非逐筆再查一次），除了讓「依開團數／完成訂單數」
    排序得以在資料庫端完成，也順帶消掉原本每頁一筆一查的 N+1。
    """
    group_buy_count = (
        select(func.count())
        .select_from(GroupBuy)
        .where(GroupBuy.group_leader_profile_id == GroupLeaderProfile.id)
        .correlate(GroupLeaderProfile)
        .scalar_subquery()
    )
    completed_order_count = (
        select(func.count())
        .select_from(GroupOrder)
        .join(GroupBuy, GroupBuy.id == GroupOrder.group_buy_id)
        .where(
            GroupBuy.group_leader_profile_id == GroupLeaderProfile.id,
            GroupOrder.status == OrderStatus.COMPLETED,
        )
        .correlate(GroupLeaderProfile)
        .scalar_subquery()
    )

    stmt = select(GroupLeaderProfile, group_buy_count, completed_order_count).where(
        GroupLeaderProfile.display_name.is_not(None)
    )
    if keyword:
        stmt = stmt.where(GroupLeaderProfile.display_name.ilike(f"%{keyword}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    if sort is GroupLeaderSort.CREATED_ASC:
        order_by = [GroupLeaderProfile.created_at.asc()]
    elif sort is GroupLeaderSort.GROUP_BUY_DESC:
        order_by = [group_buy_count.desc(), GroupLeaderProfile.created_at.desc()]
    elif sort is GroupLeaderSort.COMPLETED_ORDER_DESC:
        order_by = [completed_order_count.desc(), GroupLeaderProfile.created_at.desc()]
    else:
        order_by = [GroupLeaderProfile.created_at.desc()]

    rows = db.execute(
        # 加上 id 為次要排序鍵，避免同分項目在跨頁時順序飄移造成重複／遺漏
        stmt.order_by(*order_by, GroupLeaderProfile.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows], total
