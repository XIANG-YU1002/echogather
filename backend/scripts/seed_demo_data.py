"""重置帳號範疇資料並建立完整的示範帳號、開團與訂單。

只清除「帳號範疇」資料（app_user 及其關聯的團主資料/申請、跟團清單、訂單、
訂單狀態歷史、收藏、公告、通知），保留現有的活動／商品／角色（目錄資料，
不屬於帳號範疇）。

建立內容：
- 1 位管理員
- 5 位團主，各自對同一個開放活動建立 1 筆進行中的開團，且開團設定各不相同
  （付款方式／備註／二補／滿贈／收單期限／團規／聯絡平台／商品組合與售價皆不同）。
  註：資料庫有 uq_group_buy_leader_activity_open（同一團主對同一活動同時只能有
  一個進行中的開團），5 位不同團主各開一團不違反此限制。
- 5 位一般會員，其中 1 位刻意不下任何訂單（保留空帳號情境），
  另 1 位持有一張未送出的跟團清單，讓購物車／確認訂單頁仍可預覽，
  並收藏該活動底下全部商品（含下架與未定價），讓收藏頁有滿版網格與分頁可看。
  其餘會員各有至少一筆訂單，涵蓋所有訂單狀態與取消申請情境。

寫入真實 Supabase 資料庫（非自動 rollback 的測試資料庫）。
執行方式：於 backend/ 目錄啟用 venv 後執行 `python scripts/seed_demo_data.py`。

帳號密碼皆為 Passw0rd1，僅供本機開發測試使用。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.announcement import Announcement
from app.models.enums import (
    AnnouncementAudienceScope,
    AnnouncementType,
    CancellationStatus,
    ContactPlatform,
    GroupBuyStatus,
    NotificationType,
    OrderStatus,
    PaymentMethod,
    UserRole,
)
from app.models.favorite import ProductFavorite
from app.models.notification import Notification
from app.models.follow_list import FollowList, FollowListItem
from app.models.group_buy import GroupBuy, GroupBuyProduct, GroupBuyProductCharacter
from app.models.group_leader import GroupLeaderProfile
from app.models.order import CancellationRequest, GroupOrder, OrderItem, OrderStatusHistory
from app.models.user import AppUser
from app.repositories import order_repository

PASSWORD = "Passw0rd1"

# 清除順序：先子表後父表，避免違反外鍵限制。活動／商品／角色刻意不在此列。
ACCOUNT_SCOPED_TABLES = [
    "notification",
    "cancellation_request",
    "order_status_history",
    "order_item",
    "group_order",
    "follow_list_item",
    "follow_list",
    "product_favorite",
    "announcement",
    "group_buy_product_character",
    "group_buy_product",
    "group_buy",
    "group_leader_application",
    "group_leader_profile",
    "app_user",
]

# 5 位團主：顯示名稱、聯絡平台與開團設定各不相同
LEADER_PLAN = [
    {
        "email": "demo-leader1@example.com",
        "nickname": "團主・月影",
        "display_name": "月影團",
        "introduction": "專接官方周邊，固定每月開一團，出貨速度快。",
        "contact_platform": ContactPlatform.DISCORD,
        "contact_value": "moon_shadow",
        # 主要聯絡平台以外，團主公開資料可額外填寫的聯絡方式（圖 12 卡片三欄）。
        # 刻意只讓部分團主填滿三欄，另一部分維持單一，兩種情境都看得到。
        "extra_profile_contacts": {
            "facebook_url": "https://www.facebook.com/moonshadow.wuwa",
            "line_contact": "@moonshadow",
        },
        "payment_method": PaymentMethod.BANK_TRANSFER,
        "payment_method_note": "團費確認後再私訊告知匯款帳號",
        "requires_second_payment": True,
        "includes_full_gift": True,
        "deadline_days": 14,
        "rules": (
            "1. 下單後請留意通知與外部聯絡訊息。\n"
            "2. 本團付款方式為匯款，帳號將於團費確認後私訊告知。\n"
            "3. 本團需二補，實際運費依到貨時計算多退少補。\n"
            "4. 下單後不得擅自取消，如需取消請於平台提出申請。\n"
            "5. 滿贈依官方實際發送情況處理。"
        ),
        # (商品序位, 單價, 每角色基準數量)
        "products": [(0, "390.00", 20), (1, "250.00", 15)],
    },
    {
        "email": "demo-leader2@example.com",
        "nickname": "團主・星辰",
        "display_name": "星辰大海",
        "introduction": "新手團主，以面交取貨為主，歡迎詢問。",
        "contact_platform": ContactPlatform.LINE,
        "contact_value": "@starry_sea",
        "extra_profile_contacts": {
            "facebook_url": "https://www.facebook.com/starrysea.group",
            "discord_contact": "starrysea#0721",
        },
        "payment_method": PaymentMethod.CASH_ON_DELIVERY,
        "payment_method_note": None,
        "requires_second_payment": False,
        "includes_full_gift": False,
        "deadline_days": 7,
        "rules": (
            "1. 本團為取貨付款，面交地點與時間另行約定。\n"
            "2. 免二補，售價即為最終金額。\n"
            "3. 商品到貨後三日內完成面交。\n"
            "4. 逾期未取貨視為放棄，恕不保留。"
        ),
        "products": [(1, "260.00", 12)],
    },
    {
        "email": "demo-leader3@example.com",
        "nickname": "團主・風鈴",
        "display_name": "風鈴草",
        "introduction": "長期經營，配合國際運送，接受大量訂購。",
        "contact_platform": ContactPlatform.FACEBOOK,
        "contact_value": "https://www.facebook.com/windbell.group",
        "extra_profile_contacts": {
            "discord_contact": "windbell#1122",
            "line_contact": "@windbell",
        },
        "payment_method": PaymentMethod.BANK_TRANSFER,
        "payment_method_note": "可分兩次付款，細節請私訊",
        "requires_second_payment": False,
        "includes_full_gift": True,
        "deadline_days": 21,
        "rules": (
            "1. 本團走國際運送，到貨時間約 30～45 個工作天。\n"
            "2. 免二補，運費已含於售價中。\n"
            "3. 商品外盒可能因運送有輕微壓損，介意者請勿下單。\n"
            "4. 滿額贈品依官方配額發放，送完為止。"
        ),
        "products": [(2, "880.00", 8), (0, "400.00", 10)],
    },
    {
        "email": "demo-leader4@example.com",
        "nickname": "團主・月見",
        "display_name": "月見團子",
        "introduction": "小量精緻團，重視包裝品質。",
        "contact_platform": ContactPlatform.DISCORD,
        "contact_value": "tsukimi_dango",
        "payment_method": PaymentMethod.CASH_ON_DELIVERY,
        "payment_method_note": "可於指定超商取貨付款",
        "requires_second_payment": True,
        "includes_full_gift": False,
        "deadline_days": 10,
        "rules": (
            "1. 本團採超商取貨付款，取貨門市於出貨前確認。\n"
            "2. 需二補，二補金額於到貨後另行公告。\n"
            "3. 每人限購兩件，超出恕不受理。\n"
            "4. 未取貨者將列入黑名單。"
        ),
        "products": [(1, "245.00", 25)],
    },
    {
        "email": "demo-leader5@example.com",
        "nickname": "團主・小明",
        "display_name": "小明不想上班",
        "introduction": "佛系開團，隨緣出貨，但一定會出。",
        "contact_platform": ContactPlatform.LINE,
        "contact_value": "@ming_nowork",
        "payment_method": PaymentMethod.BANK_TRANSFER,
        "payment_method_note": None,
        "requires_second_payment": False,
        "includes_full_gift": True,
        "deadline_days": 30,
        "rules": (
            "1. 佛系開團，收單期限較長，請耐心等候。\n"
            "2. 匯款後請主動告知後五碼以利對帳。\n"
            "3. 免二補。\n"
            "4. 有任何問題請透過 LINE 聯繫。"
        ),
        "products": [(2, "860.00", 16), (1, "255.00", 20)],
    },
]

# 5 位一般會員；序位 0（demo-member1）刻意完全沒有訂單
MEMBER_PLAN = [
    {"email": "demo-member1@example.com", "nickname": "小新の周邊倉庫", "discord": "shin_goods"},
    {"email": "demo-member2@example.com", "nickname": "抹茶控", "line": "@matcha_lover"},
    {"email": "demo-member3@example.com", "nickname": "夜貓子玩家", "discord": "night_owl"},
    {
        "email": "demo-member4@example.com",
        "nickname": "收藏成癮",
        "facebook": "facebook.com/collector",
    },
    {"email": "demo-member5@example.com", "nickname": "路過的旅人", "line": "@passerby"},
]

# 訂單規劃：(會員序位, 團主序位, 狀態, [(該團商品序位, 數量)], 幾天前建立, 額外設定)
# 會員序位 0 刻意不出現 —— 保留「沒有下單」的帳號。
ORDER_PLAN = [
    (1, 0, OrderStatus.PENDING_CONFIRMATION, [(0, 2)], 0, {}),
    (2, 1, OrderStatus.PENDING_PAYMENT, [(0, 1)], 1, {}),
    (3, 2, OrderStatus.PAID, [(0, 1), (1, 2)], 3, {}),
    (3, 3, OrderStatus.SHIPPED, [(0, 3)], 6, {}),
    (4, 4, OrderStatus.COMPLETED, [(0, 1), (1, 1)], 12, {}),
    (
        4,
        0,
        OrderStatus.REJECTED,
        [(1, 5)],
        9,
        {"rejection_reason": "本次可接受數量不足，請改跟下一團。"},
    ),
    # 供圖 09 取消訂單申請頁預覽：已付款且有一筆待團主處理的取消申請
    (2, 2, OrderStatus.PAID, [(0, 1)], 4, {"pending_cancellation": "臨時有事無法接收，抱歉。"}),
    # 已被核准取消的歷史訂單
    (1, 4, OrderStatus.CANCELLED, [(1, 1)], 15, {"approved_cancellation": "重複下單，已協助取消。"}),
]

# 各終點狀態的完整推進路徑，用來補寫狀態歷史
STATUS_PATH = {
    OrderStatus.PENDING_CONFIRMATION: [OrderStatus.PENDING_CONFIRMATION],
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PENDING_CONFIRMATION, OrderStatus.PENDING_PAYMENT],
    OrderStatus.PAID: [
        OrderStatus.PENDING_CONFIRMATION,
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.PAID,
    ],
    OrderStatus.SHIPPED: [
        OrderStatus.PENDING_CONFIRMATION,
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
    ],
    OrderStatus.COMPLETED: [
        OrderStatus.PENDING_CONFIRMATION,
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
        OrderStatus.COMPLETED,
    ],
    OrderStatus.REJECTED: [OrderStatus.PENDING_CONFIRMATION, OrderStatus.REJECTED],
    OrderStatus.CANCELLED: [
        OrderStatus.PENDING_CONFIRMATION,
        OrderStatus.PENDING_PAYMENT,
        OrderStatus.CANCELLED,
    ],
}


def _contact_fields(platform, value):
    """app_user 的聯絡欄位：依平台放到對應欄位，其餘為 None。"""
    return {
        "facebook_contact": value if platform == ContactPlatform.FACEBOOK else None,
        "discord_contact": value if platform == ContactPlatform.DISCORD else None,
        "line_contact": value if platform == ContactPlatform.LINE else None,
    }


def _profile_contact_fields(platform, value, extra=None):
    """group_leader_profile 的聯絡欄位（Facebook 存的是網址欄位 facebook_url）。

    `extra` 為主要平台以外額外填寫的聯絡方式，讓部分團主三個平台都有值。
    """
    fields = {
        "facebook_url": value if platform == ContactPlatform.FACEBOOK else None,
        "discord_contact": value if platform == ContactPlatform.DISCORD else None,
        "line_contact": value if platform == ContactPlatform.LINE else None,
    }
    fields.update(extra or {})
    return fields


def _load_catalog(db):
    activity = db.execute(
        text(
            "SELECT id, name, has_full_gift FROM activity"
            " WHERE status = 'open'"
            "   AND EXISTS (SELECT 1 FROM product p WHERE p.activity_id = activity.id"
            "               AND p.is_active = true)"
            " ORDER BY created_at LIMIT 1"
        )
    ).one_or_none()
    if activity is None:
        raise RuntimeError("找不到底下有上架商品的開放活動，無法建立示範開團。")

    products = db.execute(
        text(
            "SELECT id, name, primary_image_url FROM product"
            " WHERE activity_id = :aid AND is_active = true ORDER BY created_at"
        ),
        {"aid": activity.id},
    ).all()
    if len(products) < 2:
        raise RuntimeError("開放活動底下的上架商品少於 2 項，無法建立多樣化的示範開團。")

    characters = {
        row.id: db.execute(
            text("SELECT character_id FROM product_character WHERE product_id = :pid"),
            {"pid": row.id},
        )
        .scalars()
        .all()
        for row in products
    }
    character_names = dict(db.execute(text("SELECT id, name FROM character")).all())
    return activity, products, characters, character_names


def _create_users(db):
    admin = AppUser(
        email="demo-admin@example.com",
        password_hash=hash_password(PASSWORD),
        nickname="示範管理員",
        discord_contact="demo_admin",
        role=UserRole.ADMIN,
    )
    db.add(admin)

    leader_users = []
    for plan in LEADER_PLAN:
        user = AppUser(
            email=plan["email"],
            password_hash=hash_password(PASSWORD),
            nickname=plan["nickname"],
            role=UserRole.MEMBER,
            **_contact_fields(plan["contact_platform"], plan["contact_value"]),
        )
        db.add(user)
        leader_users.append(user)

    member_users = []
    for plan in MEMBER_PLAN:
        user = AppUser(
            email=plan["email"],
            password_hash=hash_password(PASSWORD),
            nickname=plan["nickname"],
            discord_contact=plan.get("discord"),
            line_contact=plan.get("line"),
            facebook_contact=plan.get("facebook"),
            role=UserRole.MEMBER,
        )
        db.add(user)
        member_users.append(user)

    db.flush()
    return admin, leader_users, member_users


def _create_group_buys(db, activity, products, characters, leader_users):
    """為每位團主建立一筆設定各異的開團，回傳 [(profile, group_buy, [(gbp, product, char_ids)])]。"""
    now = datetime.now(timezone.utc)
    results = []

    for index, (plan, user) in enumerate(zip(LEADER_PLAN, leader_users)):
        profile = GroupLeaderProfile(
            user_id=user.id,
            display_name=plan["display_name"],
            introduction=plan["introduction"],
            default_rules=plan["rules"],
            # created_at 的 server default 是 PostgreSQL now()，它回傳「交易開始時間」，
            # 整份 seed 跑在同一交易內會讓所有團主的加入時間完全相同，
            # 團主列表「依加入時間」排序就看不出差異。這裡明確錯開。
            created_at=now - timedelta(days=(len(LEADER_PLAN) - index) * 30),
            **_profile_contact_fields(
                plan["contact_platform"],
                plan["contact_value"],
                plan.get("extra_profile_contacts"),
            ),
        )
        db.add(profile)
        db.flush()

        # 活動不支援滿贈時，開團的 includes_full_gift 必須為 False
        includes_full_gift = plan["includes_full_gift"] and activity.has_full_gift

        group_buy = GroupBuy(
            group_leader_profile_id=profile.id,
            activity_id=activity.id,
            payment_method=plan["payment_method"],
            payment_method_note=plan["payment_method_note"],
            requires_second_payment=plan["requires_second_payment"],
            includes_full_gift=includes_full_gift,
            deadline_at=now + timedelta(days=plan["deadline_days"]),
            rules=plan["rules"],
            contact_platform=plan["contact_platform"],
            contact_value=plan["contact_value"],
            status=GroupBuyStatus.OPEN,
        )
        db.add(group_buy)
        db.flush()

        group_buy_products = []
        for product_index, unit_price, base_quantity in plan["products"]:
            product = products[product_index % len(products)]
            gbp = GroupBuyProduct(
                group_buy_id=group_buy.id,
                product_id=product.id,
                unit_price=unit_price,
                max_quantity=base_quantity,
            )
            db.add(gbp)
            db.flush()

            character_ids = characters.get(product.id) or []
            if character_ids:
                # 每角色不同數量，凸顯分角色庫存；max_quantity 同步為各角色總和
                total = 0
                for index, character_id in enumerate(character_ids):
                    per_character = base_quantity + index * 2
                    db.add(
                        GroupBuyProductCharacter(
                            group_buy_product_id=gbp.id,
                            character_id=character_id,
                            max_quantity=per_character,
                        )
                    )
                    total += per_character
                gbp.max_quantity = total

            group_buy_products.append((gbp, product, character_ids))

        results.append((profile, group_buy, group_buy_products))

    return results


def _create_orders(db, member_users, bundles, activity, character_names):
    now = datetime.now(timezone.utc)
    created = []

    for member_index, leader_index, status, item_plan, days_ago, extra in ORDER_PLAN:
        member = member_users[member_index]
        profile, group_buy, group_buy_products = bundles[leader_index]
        created_at = now - timedelta(days=days_ago, hours=2)

        total = Decimal("0.00")
        resolved_items = []
        for gbp_index, quantity in item_plan:
            gbp, product, character_ids = group_buy_products[gbp_index % len(group_buy_products)]
            unit_price = Decimal(str(gbp.unit_price))
            subtotal = unit_price * quantity
            total += subtotal
            resolved_items.append(
                {
                    "gbp": gbp,
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                    "chosen_character_id": character_ids[0] if character_ids else None,
                }
            )

        order = GroupOrder(
            order_number=order_repository.generate_unique_order_number(db),
            user_id=member.id,
            group_buy_id=group_buy.id,
            status=status,
            rejection_reason=extra.get("rejection_reason"),
            product_total_amount=total,
            group_leader_name_snapshot=profile.display_name,
            activity_name_snapshot=activity.name,
            payment_method_snapshot=group_buy.payment_method,
            payment_method_note_snapshot=group_buy.payment_method_note,
            requires_second_payment_snapshot=group_buy.requires_second_payment,
            includes_full_gift_snapshot=group_buy.includes_full_gift,
            rules_snapshot=group_buy.rules,
            leader_contact_platform_snapshot=group_buy.contact_platform,
            leader_contact_value_snapshot=group_buy.contact_value,
            member_facebook_contact_snapshot=member.facebook_contact,
            member_discord_contact_snapshot=member.discord_contact,
            member_line_contact_snapshot=member.line_contact,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(order)
        db.flush()

        for item in resolved_items:
            db.add(
                OrderItem(
                    order_id=order.id,
                    group_buy_product_id=item["gbp"].id,
                    chosen_character_id=item["chosen_character_id"],
                    chosen_character_name_snapshot=(
                        character_names.get(item["chosen_character_id"])
                        if item["chosen_character_id"]
                        else None
                    ),
                    product_name_snapshot=item["product"].name,
                    image_url_snapshot=item["product"].primary_image_url,
                    unit_price=item["unit_price"],
                    quantity=item["quantity"],
                    subtotal=item["subtotal"],
                    created_at=created_at,
                )
            )

        # 狀態歷史：依終點狀態的完整路徑補寫，每步間隔數小時
        for step_index, step_status in enumerate(STATUS_PATH[status]):
            if step_status == OrderStatus.REJECTED:
                note = extra.get("rejection_reason")
            elif step_status == OrderStatus.CANCELLED:
                note = extra.get("approved_cancellation")
            else:
                note = None
            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    status=step_status,
                    note=note,
                    created_at=created_at + timedelta(hours=step_index * 5),
                )
            )

        if "pending_cancellation" in extra:
            requested_at = created_at + timedelta(hours=20)
            db.add(
                CancellationRequest(
                    order_id=order.id,
                    reason=extra["pending_cancellation"],
                    status=CancellationStatus.PENDING,
                    created_at=requested_at,
                    updated_at=requested_at,
                )
            )
        if "approved_cancellation" in extra:
            requested_at = created_at + timedelta(hours=8)
            processed_at = created_at + timedelta(hours=12)
            db.add(
                CancellationRequest(
                    order_id=order.id,
                    reason="重複下單，想取消其中一筆。",
                    status=CancellationStatus.APPROVED,
                    response_note=extra["approved_cancellation"],
                    processed_at=processed_at,
                    created_at=requested_at,
                    updated_at=processed_at,
                )
            )

        created.append((order, member, profile))

    return created


def _create_announcements(db, admin, member_users, bundles, orders):
    """建立平台公告（管理員）與團主公告，並產生對應通知。

    依圖 10 需求，通知中心要同時看得到「系統通知」與「團主公告」兩類：
    - 平台公告：管理員發布，通知全部使用者，notification_type = system
    - 團主公告：團主發布，通知該團未完成訂單的會員，notification_type = group_leader
    """
    now = datetime.now(timezone.utc)
    # 平台公告發給所有使用者（含管理員與團主帳號）
    all_user_ids = [admin.id] + [u.id for u in member_users] + [p.user_id for p, _g, _x in bundles]
    created = []

    # --- 平台公告（管理員）---
    platform_plan = [
        (
            "平台維護通知",
            "本平台將於 8/15（五）02:00～04:00 進行系統維護，期間可能無法下單，敬請提前安排。",
            2,
        ),
        (
            "新增付款方式說明",
            "付款方式已調整為「匯款」與「取貨付款」兩種，實際方式請依各團團主公告為準。",
            26,
        ),
    ]
    for title, content, hours_ago in platform_plan:
        published_at = now - timedelta(hours=hours_ago)
        announcement = Announcement(
            announcement_type=AnnouncementType.PLATFORM,
            created_by_user_id=admin.id,
            title=title,
            content=content,
            # 依 ck_announcement_type_scope_pair：平台公告一律 is_public = false
            # （只以通知形式送達，不另設公開頁）
            is_public=False,
            published_at=published_at,
            created_at=published_at,
            updated_at=published_at,
        )
        db.add(announcement)
        db.flush()
        for user_id in all_user_ids:
            db.add(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.SYSTEM,
                    title=title,
                    message=content,
                    announcement_id=announcement.id,
                    created_at=published_at,
                )
            )
        created.append(("平台公告", title))

    # --- 團主公告 ---
    # 對每個開團，取該團「未完成訂單」的會員作為收件人（與正式邏輯一致）
    unfinished = {"pending_confirmation", "pending_payment", "paid", "shipped"}
    leader_plan = [
        (0, "3.4 官方周邊團務更新，預計到貨時間延後", "因原廠生產進度影響，預計到貨時間將延後 1-2 週，造成不便敬請見諒。", 3),
        (2, "今汐壓克力立牌 已達接單上限", "感謝大家支持！「今汐壓克力立牌」已達本團接單上限，將提前關閉下單，謝謝！", 27),
        (4, "3.4 官方周邊提早收單通知", "因部分商品數量有限，本團將於 8/7（四）23:59 提早收單，請把握時間下單！", 30),
    ]
    for leader_index, title, content, hours_ago in leader_plan:
        profile, group_buy, _gbps = bundles[leader_index]
        published_at = now - timedelta(hours=hours_ago)
        announcement = Announcement(
            announcement_type=AnnouncementType.GROUP_LEADER,
            audience_scope=AnnouncementAudienceScope.LEADER_UNFINISHED,
            group_leader_profile_id=profile.id,
            created_by_user_id=profile.user_id,
            title=title,
            content=content,
            is_public=True,
            published_at=published_at,
            created_at=published_at,
            updated_at=published_at,
        )
        db.add(announcement)
        db.flush()

        recipient_ids = {
            order.user_id
            for order, _member, order_profile in orders
            if order_profile.id == profile.id and order.status.value in unfinished
        }
        # 若該團目前沒有未完成訂單，仍發給所有示範會員，確保通知中心有內容可看
        if not recipient_ids:
            recipient_ids = {u.id for u in member_users}

        for user_id in recipient_ids:
            db.add(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.GROUP_LEADER,
                    title=title,
                    message=content,
                    announcement_id=announcement.id,
                    created_at=published_at,
                )
            )
        created.append((f"團主公告（{profile.display_name}）", title))

    return created


def _create_follow_list(db, member_users, bundles):
    """給 demo-member2 一張未送出的跟團清單，讓購物車／確認訂單頁可預覽。"""
    member = member_users[1]
    profile, group_buy, group_buy_products = bundles[4]

    follow_list = FollowList(user_id=member.id, group_buy_id=group_buy.id)
    db.add(follow_list)
    db.flush()

    for gbp, _product, character_ids in group_buy_products:
        db.add(
            FollowListItem(
                follow_list_id=follow_list.id,
                group_buy_product_id=gbp.id,
                chosen_character_id=character_ids[0] if character_ids else None,
                quantity=1,
            )
        )
    return member, profile


def _create_favorites(db, member_users, activity):
    """給 demo-member2 收藏該活動底下所有商品（依圖 11 我的收藏頁）。

    刻意含下架與未定價商品，讓收藏頁的灰化樣式、「未提供官方原價」與分頁
    都有資料可看。商品目錄本身不由本腳本建立（見檔頭說明），這裡只挑現有商品。
    """
    member = member_users[1]
    product_ids = (
        db.execute(
            text("SELECT id FROM product WHERE activity_id = :aid ORDER BY created_at"),
            {"aid": activity.id},
        )
        .scalars()
        .all()
    )

    # 明確給遞增的 created_at，收藏頁「依收藏時間」排序才有穩定且合理的順序
    base_time = datetime.now(timezone.utc) - timedelta(days=len(product_ids))
    for index, product_id in enumerate(product_ids):
        db.add(
            ProductFavorite(
                user_id=member.id,
                product_id=product_id,
                created_at=base_time + timedelta(days=index),
            )
        )
    return member, len(product_ids)


def main() -> None:
    db = SessionLocal()
    try:
        for table in ACCOUNT_SCOPED_TABLES:
            db.execute(text(f'DELETE FROM "{table}"'))

        activity, products, characters, character_names = _load_catalog(db)
        admin, leader_users, member_users = _create_users(db)
        bundles = _create_group_buys(db, activity, products, characters, leader_users)
        orders = _create_orders(db, member_users, bundles, activity, character_names)
        announcements = _create_announcements(db, admin, member_users, bundles, orders)
        cart_member, cart_profile = _create_follow_list(db, member_users, bundles)
        favorite_member, favorite_count = _create_favorites(db, member_users, activity)

        db.commit()

        print(f"帳號資料已重置，示範資料建立完成。密碼一律為 {PASSWORD}")
        print(f"\n活動：{activity.name}")
        print(f"管理員：{admin.email}")

        print(f"\n團主（{len(bundles)} 位，各一筆進行中開團，設定皆不同）：")
        for plan, (profile, group_buy, gbps) in zip(LEADER_PLAN, bundles):
            print(
                f"  {plan['email']:28} {profile.display_name:8}"
                f" 付款={group_buy.payment_method.value:17}"
                f" 二補={'是' if group_buy.requires_second_payment else '否'}"
                f" 滿贈={'是' if group_buy.includes_full_gift else '否'}"
                f" 期限={plan['deadline_days']:>2}天"
                f" 商品={len(gbps)}項"
            )

        order_count = {}
        for order, member, _profile in orders:
            order_count[member.email] = order_count.get(member.email, 0) + 1

        print(f"\n團員（{len(member_users)} 位）：")
        for plan in MEMBER_PLAN:
            count = order_count.get(plan["email"], 0)
            tags = []
            if count == 0:
                tags.append("刻意無訂單")
            if plan["email"] == cart_member.email:
                tags.append(f"持有未送出購物車（{cart_profile.display_name}）")
            if plan["email"] == favorite_member.email:
                tags.append(f"收藏 {favorite_count} 項商品")
            suffix = f"  ← {'、'.join(tags)}" if tags else ""
            print(f"  {plan['email']:28} 訂單 {count} 筆{suffix}")

        print(f"\n訂單（{len(orders)} 筆，涵蓋全部狀態）：")
        for order, member, profile in orders:
            print(
                f"  {order.order_number}  {order.status.value:20}"
                f" {member.nickname:14} → {profile.display_name}"
            )

        print(f"\n公告（{len(announcements)} 則，已產生對應通知）：")
        for kind, title in announcements:
            print(f"  {kind:22} {title}")

        counts = dict(
            db.execute(
                text(
                    "select notification_type::text, count(*) from notification group by 1"
                )
            ).all()
        )
        print(f"\n通知總數：系統通知 {counts.get('system', 0)} 則、團主公告 {counts.get('group_leader', 0)} 則")
    finally:
        db.close()


if __name__ == "__main__":
    main()
