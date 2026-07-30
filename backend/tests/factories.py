import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.activity import Activity
from app.models.enums import (
    ActivityStatus,
    ContactPlatform,
    GroupBuyStatus,
    OrderStatus,
    PaymentMethod,
    UserRole,
)
from app.models.group_buy import GroupBuy, GroupBuyProduct
from app.models.group_leader import GroupLeaderProfile
from app.models.order import GroupOrder, OrderItem
from app.models.product import Character, Product, ProductCharacter
from app.models.user import AppUser


def create_user(db: Session, **overrides) -> AppUser:
    defaults = dict(
        email=f"user-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("Passw0rd1"),
        nickname="測試使用者",
        discord_contact="tester_discord",
        role=UserRole.MEMBER,
    )
    defaults.update(overrides)
    user = AppUser(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_group_leader_profile(
    db: Session, user: AppUser | None = None, *, complete: bool = True, **overrides
) -> GroupLeaderProfile:
    if user is None:
        user = create_user(db)

    defaults = dict(user_id=user.id)
    if complete:
        defaults["display_name"] = f"團主-{uuid.uuid4().hex[:8]}"
        defaults["discord_contact"] = "leader_discord"
    defaults.update(overrides)

    profile = GroupLeaderProfile(**defaults)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def create_activity(db: Session, **overrides) -> Activity:
    defaults = dict(
        name=f"活動-{uuid.uuid4().hex[:8]}",
        image_url="/uploads/activity/sample.webp",
        status=ActivityStatus.OPEN,
        has_full_gift=False,
    )
    defaults.update(overrides)
    activity = Activity(**defaults)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def create_product(db: Session, activity: Activity | None = None, **overrides) -> Product:
    if activity is None:
        activity = create_activity(db)

    defaults = dict(
        activity_id=activity.id,
        name=f"商品-{uuid.uuid4().hex[:8]}",
        primary_image_url="/uploads/product/sample.webp",
        is_active=True,
    )
    defaults.update(overrides)
    product = Product(**defaults)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_character(db: Session, **overrides) -> Character:
    defaults = dict(name=f"角色-{uuid.uuid4().hex[:8]}")
    defaults.update(overrides)
    character = Character(**defaults)
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


def link_product_character(db: Session, product: Product, character: Character) -> None:
    db.add(ProductCharacter(product_id=product.id, character_id=character.id))
    db.commit()


def create_group_buy(
    db: Session,
    group_leader_profile: GroupLeaderProfile | None = None,
    activity: Activity | None = None,
    **overrides,
) -> GroupBuy:
    if activity is None:
        activity = create_activity(db)
    if group_leader_profile is None:
        group_leader_profile = create_group_leader_profile(db)

    defaults = dict(
        group_leader_profile_id=group_leader_profile.id,
        activity_id=activity.id,
        payment_method=PaymentMethod.CASH_ON_DELIVERY,
        requires_second_payment=False,
        includes_full_gift=False,
        deadline_at=datetime.now(timezone.utc) + timedelta(days=7),
        rules="團規內容",
        contact_platform=ContactPlatform.DISCORD,
        contact_value="leader_discord",
        status=GroupBuyStatus.OPEN,
    )
    defaults.update(overrides)
    group_buy = GroupBuy(**defaults)
    db.add(group_buy)
    db.commit()
    db.refresh(group_buy)
    return group_buy


def create_group_buy_product(
    db: Session, group_buy: GroupBuy, product: Product, **overrides
) -> GroupBuyProduct:
    defaults = dict(
        group_buy_id=group_buy.id,
        product_id=product.id,
        unit_price="100.00",
        max_quantity=10,
    )
    defaults.update(overrides)
    group_buy_product = GroupBuyProduct(**defaults)
    db.add(group_buy_product)
    db.commit()
    db.refresh(group_buy_product)
    return group_buy_product


def create_order_with_item(
    db: Session,
    user: AppUser,
    group_buy: GroupBuy,
    group_buy_product: GroupBuyProduct,
    quantity: int,
    *,
    status: OrderStatus = OrderStatus.PAID,
    created_at: datetime | None = None,
    chosen_character: Character | None = None,
) -> GroupOrder:
    """建立一張含單一商品的訂單。

    測試若會斷言訂單的先後順序（先喊先得），務必指定 created_at：它平常由
    server_default now() 產生，而 PostgreSQL 的 now() 在同一交易內是固定值，
    同一個測試裡建立的多張訂單時間會完全相同，排序就落到 UUID tie-break 而變隨機。
    """
    order = GroupOrder(
        order_number=f"ORD{uuid.uuid4().hex[:12].upper()}",
        user_id=user.id,
        group_buy_id=group_buy.id,
        status=status,
        **({"created_at": created_at} if created_at is not None else {}),
        product_total_amount=str(group_buy_product.unit_price * quantity),
        group_leader_name_snapshot="團主快照",
        activity_name_snapshot="活動快照",
        payment_method_snapshot=group_buy.payment_method,
        requires_second_payment_snapshot=group_buy.requires_second_payment,
        includes_full_gift_snapshot=group_buy.includes_full_gift,
        rules_snapshot=group_buy.rules,
        leader_contact_platform_snapshot=group_buy.contact_platform,
        leader_contact_value_snapshot=group_buy.contact_value,
        member_discord_contact_snapshot="member_discord",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    order_item = OrderItem(
        order_id=order.id,
        group_buy_product_id=group_buy_product.id,
        product_name_snapshot="商品快照",
        image_url_snapshot="/uploads/product/sample.webp",
        unit_price=group_buy_product.unit_price,
        quantity=quantity,
        subtotal=group_buy_product.unit_price * quantity,
        # 多角色商品要指定角色，否則分角色佔用量查不到這筆
        chosen_character_id=chosen_character.id if chosen_character else None,
        chosen_character_name_snapshot=chosen_character.name if chosen_character else None,
    )
    db.add(order_item)
    db.commit()
    return order
