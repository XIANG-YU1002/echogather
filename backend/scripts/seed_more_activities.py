"""新增 5 個活動、每個活動 6 項商品（含無角色／單角色／多角色），
並為團主 demo-leader1 各建立一筆開團與多筆訂單，另清除測試殘留的活動「4343」。

依使用者 2026-07-29 要求：
- 5 筆活動，每筆至少 5 項商品
- 商品要涵蓋單角色與多角色（另加無角色，讓三種庫存情境都能測）
- 每項商品都要有訂單，狀態分佈由腳本決定
- 清除活動「4343」及其相關資料

與 seed_demo_data.py 的差別：本腳本只「新增」，不清除任何帳號資料，
可在既有示範資料之上重複執行（活動名稱已存在時會跳過該活動）。

寫入真實 Supabase 資料庫。執行方式：
  cd backend && venv\\Scripts\\python.exe scripts\\seed_more_activities.py
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.enums import (
    ActivityStatus,
    ContactPlatform,
    Currency,
    GroupBuyStatus,
    OrderStatus,
    PaymentMethod,
)
from app.models.activity import Activity
from app.models.group_buy import GroupBuy, GroupBuyProduct, GroupBuyProductCharacter
from app.models.order import GroupOrder, OrderItem, OrderStatusHistory
from app.models.product import Product, ProductCharacter

LEADER_EMAIL = "demo-leader1@example.com"
MEMBER_EMAILS = [f"demo-member{i}@example.com" for i in range(1, 6)]

# 圖片沿用既有示範資料的做法（placehold.co 帶文字，方便辨識是哪一項）
def _activity_image(label: str) -> str:
    return f"https://placehold.co/960x540?text={label}"


def _product_image(label: str) -> str:
    return f"https://placehold.co/600x600?text={label}"


# 每個活動：名稱、六項商品（kind: none／single／multi）
ACTIVITY_BLUEPRINTS = [
    {
        "name": "5.0 星穹紀行主題周邊",
        "description": "5.0 版本主線紀念，官方同步開賣。",
        "products": [
            ("星穹紀行・托特包", "none", 890),
            ("星穹紀行・馬克杯", "none", 520),
            ("今汐・壓克力立牌", "single", 480),
            ("長離・壓克力立牌", "single", 480),
            ("角色徽章組", "multi", 320),
            ("角色明信片套組", "multi", 260),
        ],
    },
    {
        "name": "夏日祭典・浴衣系列",
        "description": "夏日祭典限定浴衣造型，附特典小卡。",
        "products": [
            ("浴衣祭典・提袋", "none", 690),
            ("浴衣祭典・團扇", "none", 350),
            ("吟霖・浴衣立牌", "single", 520),
            ("安可・浴衣立牌", "single", 520),
            ("浴衣造型亞克力吊飾", "multi", 380),
            ("浴衣造型色紙組", "multi", 300),
        ],
    },
    {
        "name": "聲之遺跡・考古筆記",
        "description": "以聲骸考古為主題的文具系列。",
        "products": [
            ("考古筆記・精裝筆記本", "none", 450),
            ("考古筆記・金屬書籤", "none", 280),
            ("忌炎・遺跡插畫掛軸", "single", 1280),
            ("維里奈・遺跡插畫掛軸", "single", 1280),
            ("遺跡調查員・角色資料夾", "multi", 240),
            ("遺跡調查員・貼紙包", "multi", 180),
        ],
    },
    {
        "name": "共鳴者生日會 2026",
        "description": "年度生日會限定，含生日蛋糕造型周邊。",
        "products": [
            ("生日會・蛋糕造型抱枕", "none", 1180),
            ("生日會・派對小旗組", "none", 220),
            ("卡卡羅・生日立牌", "single", 500),
            ("折枝・生日立牌", "single", 500),
            ("生日會・角色亞克力站台", "multi", 620),
            ("生日會・角色生日卡", "multi", 200),
        ],
    },
    {
        "name": "潮汐圖鑑・海洋特輯",
        "description": "海洋主題聯名，數量有限。",
        "products": [
            ("潮汐圖鑑・海洋玻璃杯", "none", 640),
            ("潮汐圖鑑・貝殼收納盒", "none", 580),
            ("今汐・潮汐插畫布巾", "single", 760),
            ("吟霖・潮汐插畫布巾", "single", 760),
            ("潮汐圖鑑・角色亞克力鑰匙圈", "multi", 340),
            ("潮汐圖鑑・角色透卡", "multi", 260),
        ],
    },
]

# 訂單狀態分佈：每個開團五位會員各一張，涵蓋團主端會看到的各種狀態。
# 待處理（待確認＋待付款）刻意各留一張，讓儀表板與訂購總覽都有數字可看。
ORDER_PLAN = [
    OrderStatus.PENDING_CONFIRMATION,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
    OrderStatus.SHIPPED,
    OrderStatus.COMPLETED,
]

# 狀態歷程：訂單詳情頁的「狀態紀錄」需要完整路徑
STATUS_PATHS = {
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
}


def delete_activity_4343(db) -> None:
    """清除測試殘留的活動「4343」及其相關資料。

    刪除順序依外鍵：先訂單明細與訂單，再跟團清單、開團商品的每角色庫存、
    開團商品、開團，最後商品與活動。事前已確認該活動沒有訂單／跟團／收藏／公告，
    但仍保留這些語句，讓腳本在資料變動後重跑仍安全。
    """
    activity_ids = [
        row.id for row in db.execute(text("SELECT id FROM activity WHERE name = '4343'")).all()
    ]
    if not activity_ids:
        print("活動 4343：不存在，略過")
        return

    for activity_id in activity_ids:
        params = {"aid": activity_id}
        for label, sql in [
            (
                "order_item",
                """DELETE FROM order_item WHERE order_id IN (
                       SELECT o.id FROM group_order o JOIN group_buy g ON g.id = o.group_buy_id
                       WHERE g.activity_id = :aid)""",
            ),
            (
                "order_status_history",
                """DELETE FROM order_status_history WHERE order_id IN (
                       SELECT o.id FROM group_order o JOIN group_buy g ON g.id = o.group_buy_id
                       WHERE g.activity_id = :aid)""",
            ),
            (
                "cancellation_request",
                """DELETE FROM cancellation_request WHERE order_id IN (
                       SELECT o.id FROM group_order o JOIN group_buy g ON g.id = o.group_buy_id
                       WHERE g.activity_id = :aid)""",
            ),
            (
                "group_order",
                """DELETE FROM group_order WHERE group_buy_id IN (
                       SELECT id FROM group_buy WHERE activity_id = :aid)""",
            ),
            (
                "follow_list_item",
                """DELETE FROM follow_list_item WHERE group_buy_product_id IN (
                       SELECT gbp.id FROM group_buy_product gbp
                       JOIN group_buy g ON g.id = gbp.group_buy_id WHERE g.activity_id = :aid)""",
            ),
            (
                "group_buy_product_character",
                """DELETE FROM group_buy_product_character WHERE group_buy_product_id IN (
                       SELECT gbp.id FROM group_buy_product gbp
                       JOIN group_buy g ON g.id = gbp.group_buy_id WHERE g.activity_id = :aid)""",
            ),
            (
                "group_buy_product",
                """DELETE FROM group_buy_product WHERE group_buy_id IN (
                       SELECT id FROM group_buy WHERE activity_id = :aid)""",
            ),
            (
                "announcement",
                """DELETE FROM announcement WHERE group_buy_id IN (
                       SELECT id FROM group_buy WHERE activity_id = :aid)""",
            ),
            ("group_buy", "DELETE FROM group_buy WHERE activity_id = :aid"),
            (
                "product_favorite",
                """DELETE FROM product_favorite WHERE product_id IN (
                       SELECT id FROM product WHERE activity_id = :aid)""",
            ),
            (
                "product_character",
                """DELETE FROM product_character WHERE product_id IN (
                       SELECT id FROM product WHERE activity_id = :aid)""",
            ),
            (
                "product_image",
                """DELETE FROM product_image WHERE product_id IN (
                       SELECT id FROM product WHERE activity_id = :aid)""",
            ),
            ("product", "DELETE FROM product WHERE activity_id = :aid"),
            ("activity", "DELETE FROM activity WHERE id = :aid"),
        ]:
            deleted = db.execute(text(sql), params).rowcount
            if deleted:
                print(f"活動 4343：刪除 {label} {deleted} 筆")
    db.commit()
    print("活動 4343：已清除")


def main() -> None:
    db = SessionLocal()
    try:
        delete_activity_4343(db)

        leader = db.execute(
            text(
                """SELECT glp.id, glp.display_name, glp.default_rules, glp.discord_contact
                   FROM group_leader_profile glp JOIN app_user u ON u.id = glp.user_id
                   WHERE u.email = :email"""
            ),
            {"email": LEADER_EMAIL},
        ).one()

        members = db.execute(
            text(
                """SELECT id, nickname, facebook_contact, discord_contact, line_contact
                   FROM app_user WHERE email = ANY(:emails) ORDER BY email"""
            ),
            {"emails": MEMBER_EMAILS},
        ).all()
        if len(members) != len(MEMBER_EMAILS):
            raise SystemExit("找不到全部 demo-member 帳號，請先執行 seed_demo_data.py")

        characters = db.execute(
            text("SELECT id, name FROM character WHERE name <> '測試新角色XYZ' ORDER BY name")
        ).all()
        if len(characters) < 3:
            raise SystemExit("角色資料不足，無法建立多角色商品")

        now = datetime.now(timezone.utc)
        created_activities = 0

        for index, blueprint in enumerate(ACTIVITY_BLUEPRINTS):
            existing = db.execute(
                text("SELECT id FROM activity WHERE name = :name"), {"name": blueprint["name"]}
            ).scalar_one_or_none()
            if existing is not None:
                print(f"活動 {blueprint['name']!r}：已存在，略過")
                continue

            activity = Activity(
                name=blueprint["name"],
                description=blueprint["description"],
                image_url=_activity_image(f"Activity+{index + 1}"),
                status=ActivityStatus.OPEN,
                has_full_gift=index % 2 == 0,
            )
            db.add(activity)
            db.flush()

            group_buy = GroupBuy(
                group_leader_profile_id=leader.id,
                activity_id=activity.id,
                payment_method=PaymentMethod.BANK_TRANSFER
                if index % 2 == 0
                else PaymentMethod.CASH_ON_DELIVERY,
                payment_method_note="收單後統一提供匯款帳號" if index % 2 == 0 else None,
                requires_second_payment=index % 3 == 0,
                includes_full_gift=index % 2 == 0,
                # 第一團刻意設在 2 天後，讓儀表板「即將截止（3 天內）」有資料
                deadline_at=now + timedelta(days=2 if index == 0 else 10 + index * 3),
                rules=leader.default_rules or "跟團前請詳閱團規，恕不接受無故棄單。",
                contact_platform=ContactPlatform.DISCORD,
                contact_value=leader.discord_contact or "leader_discord",
                status=GroupBuyStatus.OPEN,
            )
            db.add(group_buy)
            db.flush()

            group_buy_products = []
            for product_index, (product_name, kind, price) in enumerate(blueprint["products"]):
                product = Product(
                    activity_id=activity.id,
                    name=product_name,
                    official_price=Decimal(price),
                    official_currency=Currency.TWD,
                    primary_image_url=_product_image(f"P{index + 1}-{product_index + 1}"),
                    is_active=True,
                )
                db.add(product)
                db.flush()

                # 角色關聯：single 綁 1 個、multi 綁 3 個（依商品序位輪流取，讓角色分佈不重複）
                linked_characters = []
                if kind == "single":
                    linked_characters = [characters[(index + product_index) % len(characters)]]
                elif kind == "multi":
                    start = (index * 2 + product_index) % len(characters)
                    linked_characters = [
                        characters[(start + offset) % len(characters)] for offset in range(3)
                    ]
                for character in linked_characters:
                    db.add(
                        ProductCharacter(product_id=product.id, character_id=character.id)
                    )

                # 團主售價設為官方價的 1.1 倍取整，避免與官方價相同看不出差異
                unit_price = (Decimal(price) * Decimal("1.1")).quantize(Decimal("1"))
                group_buy_product = GroupBuyProduct(
                    group_buy_id=group_buy.id,
                    product_id=product.id,
                    unit_price=unit_price,
                    max_quantity=30,
                )
                db.add(group_buy_product)
                db.flush()

                # 有角色商品的庫存分角色記錄；max_quantity 同步為各角色總和（與 service 同規則）
                if linked_characters:
                    per_character = 20
                    for character in linked_characters:
                        db.add(
                            GroupBuyProductCharacter(
                                group_buy_product_id=group_buy_product.id,
                                character_id=character.id,
                                max_quantity=per_character,
                            )
                        )
                    group_buy_product.max_quantity = per_character * len(linked_characters)

                group_buy_products.append(
                    {
                        "group_buy_product": group_buy_product,
                        "product": product,
                        "characters": linked_characters,
                        "unit_price": unit_price,
                    }
                )

            # 每位會員一張訂單，輪轉選商品，確保每項商品都被訂到數次
            for member_index, member in enumerate(members):
                status = ORDER_PLAN[member_index % len(ORDER_PLAN)]
                # 每張訂單取 4 項商品，起點隨會員位移 → 6 項商品各被訂 3~4 次
                chosen = [
                    group_buy_products[(member_index * 2 + offset) % len(group_buy_products)]
                    for offset in range(4)
                ]
                # 去重（位移可能重覆取到同一項），保留順序
                seen_ids = set()
                unique_chosen = []
                for entry in chosen:
                    key = entry["group_buy_product"].id
                    if key not in seen_ids:
                        seen_ids.add(key)
                        unique_chosen.append(entry)

                items = []
                for entry_index, entry in enumerate(unique_chosen):
                    characters_for_item = entry["characters"]
                    if not characters_for_item:
                        selections = [(None, None)]
                    elif len(characters_for_item) >= 3 and entry_index % 2 == 0:
                        # 多角色商品刻意有一筆訂單同時訂兩個角色，測試明細不合併
                        selections = [
                            (characters_for_item[0].id, characters_for_item[0].name),
                            (characters_for_item[1].id, characters_for_item[1].name),
                        ]
                    else:
                        picked = characters_for_item[member_index % len(characters_for_item)]
                        selections = [(picked.id, picked.name)]

                    for selection_index, (character_id, character_name) in enumerate(selections):
                        quantity = 1 + (member_index + entry_index + selection_index) % 3
                        items.append(
                            {
                                "group_buy_product_id": entry["group_buy_product"].id,
                                "character_id": character_id,
                                "character_name": character_name,
                                "product_name": entry["product"].name,
                                "image_url": entry["product"].primary_image_url,
                                "unit_price": entry["unit_price"],
                                "quantity": quantity,
                            }
                        )

                total = sum(item["unit_price"] * item["quantity"] for item in items)
                serial = db.execute(
                    text(
                        """INSERT INTO order_number_counter (date_key, last_value)
                           VALUES (:date_key, 1)
                           ON CONFLICT (date_key)
                           DO UPDATE SET last_value = order_number_counter.last_value + 1
                           RETURNING last_value"""
                    ),
                    {"date_key": now.strftime("%y%m%d")},
                ).scalar_one()

                order = GroupOrder(
                    order_number=f"WG{now.strftime('%y%m%d')}-{serial:06d}",
                    user_id=member.id,
                    group_buy_id=group_buy.id,
                    status=status,
                    product_total_amount=total,
                    group_leader_name_snapshot=leader.display_name,
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
                    # 明細依提交時間排序，同一活動內錯開時間才看得出先喊先得
                    created_at=now - timedelta(hours=(len(members) - member_index) * 3),
                )
                db.add(order)
                db.flush()

                for item in items:
                    db.add(
                        OrderItem(
                            order_id=order.id,
                            group_buy_product_id=item["group_buy_product_id"],
                            chosen_character_id=item["character_id"],
                            chosen_character_name_snapshot=item["character_name"],
                            product_name_snapshot=item["product_name"],
                            image_url_snapshot=item["image_url"],
                            unit_price=item["unit_price"],
                            quantity=item["quantity"],
                            subtotal=item["unit_price"] * item["quantity"],
                        )
                    )

                for step, history_status in enumerate(STATUS_PATHS[status]):
                    db.add(
                        OrderStatusHistory(
                            order_id=order.id,
                            status=history_status,
                            created_at=order.created_at + timedelta(minutes=step * 30),
                        )
                    )

            created_activities += 1
            print(
                f"活動 {blueprint['name']!r}：已建立 6 項商品、1 筆開團、{len(members)} 筆訂單"
            )

        db.commit()
        print(f"\n完成：新增 {created_activities} 個活動")
    finally:
        db.close()


if __name__ == "__main__":
    main()
