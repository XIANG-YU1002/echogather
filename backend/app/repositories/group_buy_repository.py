import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.enums import (
    PENDING_ORDER_STATUSES,
    ActivityStatus,
    GroupBuyListSort,
    GroupBuyStatus,
    PaymentMethod,
)
from app.models.follow_list import FollowListItem
from app.models.group_buy import GroupBuy, GroupBuyProduct, GroupBuyProductCharacter
from app.models.group_leader import GroupLeaderProfile
from app.models.order import GroupOrder, OrderItem
from app.models.product import Character, Product
from app.models.user import AppUser
from app.repositories.order_repository import NON_OCCUPYING_STATUSES

# 圖 20 儀表板「即將截止」卡與開團列表的即將截止標記共用同一門檻。
UPCOMING_DEADLINE_DAYS = 3


def get_by_id(db: Session, group_buy_id: uuid.UUID) -> GroupBuy | None:
    return db.get(GroupBuy, group_buy_id)


def get_group_buy_product_by_id(db: Session, group_buy_product_id: uuid.UUID) -> GroupBuyProduct | None:
    return db.get(GroupBuyProduct, group_buy_product_id)


def get_group_buy_products_for_update(
    db: Session, group_buy_product_ids: list[uuid.UUID]
) -> list[GroupBuyProduct]:
    """依 API Design §33.2：多筆 group_buy_product 依 UUID 排序鎖定，降低 Deadlock 風險。"""
    stmt = (
        select(GroupBuyProduct)
        .where(GroupBuyProduct.id.in_(group_buy_product_ids))
        .order_by(GroupBuyProduct.id.asc())
        .with_for_update()
    )
    return db.execute(stmt).scalars().all()


def get_products_for_group_buy(
    db: Session, group_buy_id: uuid.UUID
) -> list[tuple[GroupBuyProduct, Product]]:
    stmt = (
        select(GroupBuyProduct, Product)
        .join(Product, Product.id == GroupBuyProduct.product_id)
        .where(GroupBuyProduct.group_buy_id == group_buy_id)
        .order_by(GroupBuyProduct.created_at.asc())
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def list_group_buy_products_for_product(
    db: Session,
    product_id: uuid.UUID,
    *,
    payment_method: PaymentMethod | None,
    requires_second_payment: bool | None,
    includes_full_gift: bool | None,
) -> list[tuple[GroupBuyProduct, GroupBuy, Activity, GroupLeaderProfile]]:
    """依 Business Rules §17.3：取得可套用 SQL 篩選的候選集合，可用性篩選於 Service 層計算。"""
    stmt = (
        select(GroupBuyProduct, GroupBuy, Activity, GroupLeaderProfile)
        .join(GroupBuy, GroupBuy.id == GroupBuyProduct.group_buy_id)
        .join(Activity, Activity.id == GroupBuy.activity_id)
        .join(GroupLeaderProfile, GroupLeaderProfile.id == GroupBuy.group_leader_profile_id)
        .where(GroupBuyProduct.product_id == product_id)
    )
    if payment_method is not None:
        stmt = stmt.where(GroupBuy.payment_method == payment_method)
    if requires_second_payment is not None:
        stmt = stmt.where(GroupBuy.requires_second_payment.is_(requires_second_payment))
    if includes_full_gift is not None:
        stmt = stmt.where(GroupBuy.includes_full_gift.is_(includes_full_gift))

    return [(row[0], row[1], row[2], row[3]) for row in db.execute(stmt).all()]


def get_open_group_buy_for_activity(
    db: Session, group_leader_profile_id: uuid.UUID, activity_id: uuid.UUID
) -> GroupBuy | None:
    """取得該團主對該活動目前進行中的開團（同時只允許一個）。"""
    stmt = select(GroupBuy).where(
        GroupBuy.group_leader_profile_id == group_leader_profile_id,
        GroupBuy.activity_id == activity_id,
        GroupBuy.status == GroupBuyStatus.OPEN,
    )
    return db.execute(stmt).scalars().first()


def list_by_group_leader(
    db: Session, group_leader_profile_id: uuid.UUID, status: GroupBuyStatus | None
) -> list[GroupBuy]:
    stmt = select(GroupBuy).where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    if status is not None:
        stmt = stmt.where(GroupBuy.status == status)
    stmt = stmt.order_by(GroupBuy.created_at.desc())
    return db.execute(stmt).scalars().all()


def count_group_buys_by_group_leader(db: Session, group_leader_profile_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(GroupBuy).where(
        GroupBuy.group_leader_profile_id == group_leader_profile_id
    )
    return db.execute(stmt).scalar_one()


def count_by_group_leader_and_status(
    db: Session, group_leader_profile_id: uuid.UUID, status: GroupBuyStatus
) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupBuy)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupBuy.status == status,
        )
    )
    return db.execute(stmt).scalar_one()


def count_formal_orders(db: Session, group_buy_id: uuid.UUID) -> int:
    """依 Business Rules §16.1：只要存在任何 group_order 紀錄就視為已有正式訂單。"""
    stmt = select(func.count()).select_from(GroupOrder).where(GroupOrder.group_buy_id == group_buy_id)
    return db.execute(stmt).scalar_one()


def create_group_buy(db: Session, **fields) -> GroupBuy:
    group_buy = GroupBuy(**fields)
    db.add(group_buy)
    db.flush()
    return group_buy


def create_group_buy_product(db: Session, **fields) -> GroupBuyProduct:
    group_buy_product = GroupBuyProduct(**fields)
    db.add(group_buy_product)
    db.flush()
    return group_buy_product


def set_product_character_stock(
    db: Session, group_buy_product_id: uuid.UUID, quantities: list[tuple[uuid.UUID, int]]
) -> None:
    """覆寫某開團商品的每角色庫存（先清空再寫入）。傳入空清單等同清空（無角色商品）。"""
    db.execute(
        delete(GroupBuyProductCharacter).where(
            GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id
        )
    )
    for character_id, max_quantity in quantities:
        db.add(
            GroupBuyProductCharacter(
                group_buy_product_id=group_buy_product_id,
                character_id=character_id,
                max_quantity=max_quantity,
            )
        )
    db.flush()


def get_product_character_stock(
    db: Session, group_buy_product_id: uuid.UUID
) -> list[tuple[Character, int]]:
    """回傳（角色, 每角色接單上限）清單，依角色名稱排序。無角色商品回傳空清單。"""
    stmt = (
        select(Character, GroupBuyProductCharacter.max_quantity)
        .join(
            GroupBuyProductCharacter,
            GroupBuyProductCharacter.character_id == Character.id,
        )
        .where(GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id)
        .order_by(Character.name.asc())
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_character_max_quantity(
    db: Session, group_buy_product_id: uuid.UUID, character_id: uuid.UUID
) -> int | None:
    stmt = select(GroupBuyProductCharacter.max_quantity).where(
        GroupBuyProductCharacter.group_buy_product_id == group_buy_product_id,
        GroupBuyProductCharacter.character_id == character_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def count_products_in_group_buy(db: Session, group_buy_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(GroupBuyProduct)
        .where(GroupBuyProduct.group_buy_id == group_buy_id)
    )
    return db.execute(stmt).scalar_one()


def product_exists_in_group_buy(db: Session, group_buy_id: uuid.UUID, product_id: uuid.UUID) -> bool:
    stmt = select(GroupBuyProduct.id).where(
        GroupBuyProduct.group_buy_id == group_buy_id, GroupBuyProduct.product_id == product_id
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def delete_group_buy_product(db: Session, group_buy_product: GroupBuyProduct) -> None:
    db.delete(group_buy_product)
    db.flush()


def has_follow_list_items_for_product(db: Session, group_buy_product_id: uuid.UUID) -> bool:
    stmt = select(FollowListItem.id).where(
        FollowListItem.group_buy_product_id == group_buy_product_id
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def _current_group_buys_base_stmt():
    return (
        select(GroupBuy, Activity, GroupLeaderProfile)
        .join(Activity, Activity.id == GroupBuy.activity_id)
        .join(GroupLeaderProfile, GroupLeaderProfile.id == GroupBuy.group_leader_profile_id)
        .where(
            GroupBuy.status == GroupBuyStatus.OPEN,
            GroupBuy.deadline_at > datetime.now(timezone.utc),
            Activity.status == ActivityStatus.OPEN,
        )
    )


def count_current_group_buys(db: Session) -> int:
    """依 API Design §26.2：目前開團需同時符合 open／deadline 未到／活動 open。"""
    stmt = _current_group_buys_base_stmt()
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()


def list_current_group_buys(
    db: Session, page: int, page_size: int
) -> tuple[list[tuple[GroupBuy, Activity, GroupLeaderProfile]], int]:
    stmt = _current_group_buys_base_stmt()
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(GroupBuy.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows], total


def count_orders_for_group_buy(db: Session, group_buy_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(GroupOrder).where(GroupOrder.group_buy_id == group_buy_id)
    return db.execute(stmt).scalar_one()


def _round_number_cte(group_leader_profile_id: uuid.UUID):
    """輪次編號（第 N 團）CTE：在「同一團主、同一活動」範圍內依建立時間排名。

    資料庫沒有開團名稱欄位（使用者裁決不新增），輪次一律由此算出。
    視窗函式在 WHERE 之後才計算，若把 status 篩選寫在同一層，已截止的團會被排除在
    排名之外而使編號跳號；因此先在 CTE 內算完編號，再由外層套用其餘篩選。
    只篩團主不影響排名，因為 partition 已包含 group_leader_profile_id。
    """
    return (
        select(
            GroupBuy.id.label("group_buy_id"),
            func.row_number()
            .over(
                partition_by=(GroupBuy.group_leader_profile_id, GroupBuy.activity_id),
                order_by=(GroupBuy.created_at.asc(), GroupBuy.id.asc()),
            )
            .label("round_number"),
        )
        .where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
        .cte("group_buy_rounds")
    )


def _stats_columns() -> tuple:
    """開團統計的關聯純量子查詢，讓一次查詢就取回全部統計，避免每列再打一次 DB。

    訂單數與訂購件數排除 cancelled／rejected（與庫存佔用量同一基準，依使用者裁決）；
    待確認數為單一狀態計數，本身即不含這兩種狀態。
    """
    order_count = (
        select(func.count())
        .select_from(GroupOrder)
        .where(
            GroupOrder.group_buy_id == GroupBuy.id,
            GroupOrder.status.notin_(NON_OCCUPYING_STATUSES),
        )
        .correlate(GroupBuy)
        .scalar_subquery()
        .label("order_count")
    )
    ordered_quantity = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(GroupOrder, GroupOrder.id == OrderItem.order_id)
        .where(
            GroupOrder.group_buy_id == GroupBuy.id,
            GroupOrder.status.notin_(NON_OCCUPYING_STATUSES),
        )
        .correlate(GroupBuy)
        .scalar_subquery()
        .label("ordered_quantity")
    )
    # 「待處理」＝待確認＋待付款，兩者都要團主處理（使用者 2026-07-29 說明），
    # 與儀表板統計卡同一定義。
    pending_order_count = (
        select(func.count())
        .select_from(GroupOrder)
        .where(
            GroupOrder.group_buy_id == GroupBuy.id,
            GroupOrder.status.in_(PENDING_ORDER_STATUSES),
        )
        .correlate(GroupBuy)
        .scalar_subquery()
        .label("pending_order_count")
    )
    # 欄位凍結判斷（Business Rules §16.1）用的是「存在任何紀錄」，含已取消／已拒絕，
    # 與上面三項統計基準不同，因此另外算一欄，不可由 order_count 推導。
    total_order_count = (
        select(func.count())
        .select_from(GroupOrder)
        .where(GroupOrder.group_buy_id == GroupBuy.id)
        .correlate(GroupBuy)
        .scalar_subquery()
        .label("total_order_count")
    )
    return order_count, ordered_quantity, pending_order_count, total_order_count


def _group_buy_with_stats_stmt(group_leader_profile_id: uuid.UUID):
    rounds = _round_number_cte(group_leader_profile_id)
    order_count, ordered_quantity, pending_order_count, total_order_count = _stats_columns()
    return (
        select(
            GroupBuy,
            Activity,
            rounds.c.round_number,
            order_count,
            ordered_quantity,
            pending_order_count,
            total_order_count,
        )
        .join(Activity, Activity.id == GroupBuy.activity_id)
        .join(rounds, rounds.c.group_buy_id == GroupBuy.id)
        .where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
    )


def list_by_group_leader_with_stats(
    db: Session,
    group_leader_profile_id: uuid.UUID,
    status: GroupBuyStatus | None,
    page: int,
    page_size: int,
    *,
    keyword: str | None = None,
    sort: GroupBuyListSort = GroupBuyListSort.CREATED_DESC,
) -> tuple[list[tuple], int]:
    """圖 21 我的開團：一次帶回輪次編號與各項統計。

    keyword 比對活動名稱（不分大小寫部分比對）——參考圖的搜尋框寫「搜尋開團名稱」，
    但開團沒有名稱欄位，實際可搜的就是活動名稱。
    """
    stmt = _group_buy_with_stats_stmt(group_leader_profile_id)
    if status is not None:
        stmt = stmt.where(GroupBuy.status == status)
    if keyword:
        stmt = stmt.where(Activity.name.ilike(f"%{keyword}%"))

    # id 為次要排序鍵：同一交易內建立的多筆 created_at 會相同，沒有它分頁順序會不穩定
    if sort is GroupBuyListSort.CREATED_ASC:
        order_by = (GroupBuy.created_at.asc(), GroupBuy.id.asc())
    else:
        order_by = (GroupBuy.created_at.desc(), GroupBuy.id.desc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(*order_by).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [tuple(row) for row in rows], total


def list_open_group_buys_with_stats(
    db: Session, group_leader_profile_id: uuid.UUID
) -> list[tuple]:
    """圖 20 儀表板「目前開團」：只列進行中、不分頁（依使用者裁決），最急的排前面。"""
    stmt = _group_buy_with_stats_stmt(group_leader_profile_id).where(
        GroupBuy.status == GroupBuyStatus.OPEN
    )
    rows = db.execute(stmt.order_by(GroupBuy.deadline_at.asc(), GroupBuy.id.asc())).all()
    return [tuple(row) for row in rows]


def get_round_number(db: Session, group_buy: GroupBuy) -> int:
    """單一開團的輪次編號。以「同團主同活動中建立時間更早的筆數 + 1」計算，
    與 _round_number_cte 的排序基準（created_at, id）一致。"""
    stmt = (
        select(func.count())
        .select_from(GroupBuy)
        .where(
            GroupBuy.group_leader_profile_id == group_buy.group_leader_profile_id,
            GroupBuy.activity_id == group_buy.activity_id,
            or_(
                GroupBuy.created_at < group_buy.created_at,
                and_(
                    GroupBuy.created_at == group_buy.created_at,
                    GroupBuy.id < group_buy.id,
                ),
            ),
        )
    )
    return int(db.execute(stmt).scalar_one()) + 1


def get_round_numbers(
    db: Session, group_buy_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """一次取回多個開團的輪次編號，供訂單列表這種每列都要顯示第 N 團的畫面使用。

    先在 CTE 內對全表算排名（partition 已限定同團主同活動），再取需要的那幾筆；
    不能先篩 id 再算，否則排名會只在被篩出的集合內計算而失真。
    """
    if not group_buy_ids:
        return {}
    ranked = select(
        GroupBuy.id.label("group_buy_id"),
        func.row_number()
        .over(
            partition_by=(GroupBuy.group_leader_profile_id, GroupBuy.activity_id),
            order_by=(GroupBuy.created_at.asc(), GroupBuy.id.asc()),
        )
        .label("round_number"),
    ).cte("all_group_buy_rounds")

    stmt = select(ranked.c.group_buy_id, ranked.c.round_number).where(
        ranked.c.group_buy_id.in_(group_buy_ids)
    )
    return {row.group_buy_id: row.round_number for row in db.execute(stmt).all()}


def count_status_summary(db: Session, group_leader_profile_id: uuid.UUID) -> dict[str, int]:
    """圖 21 上方三張卡：全部／進行中／已截止，一次查詢取回。"""
    stmt = (
        select(GroupBuy.status, func.count())
        .where(GroupBuy.group_leader_profile_id == group_leader_profile_id)
        .group_by(GroupBuy.status)
    )
    counts = {status: int(count) for status, count in db.execute(stmt).all()}
    open_count = counts.get(GroupBuyStatus.OPEN, 0)
    closed_count = counts.get(GroupBuyStatus.CLOSED, 0)
    return {
        "total": open_count + closed_count,
        "open": open_count,
        "closed": closed_count,
    }


def count_upcoming_deadline(
    db: Session, group_leader_profile_id: uuid.UUID, *, days: int = UPCOMING_DEADLINE_DAYS
) -> int:
    """圖 20「即將截止（3 天內）」：進行中且截止時間落在未來 N 天內。

    已過期但尚未結單的開團不算——那不是「即將」截止，而是團主已逾期未處理。
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(func.count())
        .select_from(GroupBuy)
        .where(
            GroupBuy.group_leader_profile_id == group_leader_profile_id,
            GroupBuy.status == GroupBuyStatus.OPEN,
            GroupBuy.deadline_at > now,
            GroupBuy.deadline_at <= now + timedelta(days=days),
        )
    )
    return int(db.execute(stmt).scalar_one())


def list_product_orders(db: Session, group_buy_id: uuid.UUID) -> list[tuple]:
    """圖 22 商品訂購總覽：該開團每個商品的訂購明細（含訂購成員）。

    排除 cancelled／rejected，與其他統計同一基準。回傳依商品建立順序、
    再依訂單建立時間（先喊先得）排序，供 Service 層彙總成每商品一組。
    """
    stmt = (
        select(GroupBuyProduct, Product, OrderItem, GroupOrder, AppUser)
        .join(Product, Product.id == GroupBuyProduct.product_id)
        .join(OrderItem, OrderItem.group_buy_product_id == GroupBuyProduct.id)
        .join(GroupOrder, GroupOrder.id == OrderItem.order_id)
        .join(AppUser, AppUser.id == GroupOrder.user_id)
        .where(
            GroupBuyProduct.group_buy_id == group_buy_id,
            GroupOrder.status.notin_(NON_OCCUPYING_STATUSES),
        )
        .order_by(
            GroupBuyProduct.created_at.asc(),
            GroupBuyProduct.id.asc(),
            GroupOrder.created_at.asc(),
            GroupOrder.id.asc(),
        )
    )
    return [tuple(row) for row in db.execute(stmt).all()]
