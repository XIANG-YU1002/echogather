"""重置帳號相關資料並建立三個乾淨的示範帳號。

只清除「帳號範疇」資料（app_user 及其關聯的團主資料/申請、跟團清單、訂單、
收藏、公告、通知），保留現有的活動／商品／角色（目錄資料，不屬於帳號範疇），
並在既有的開放活動與商品下重新建立一筆開團，讓前台頁面仍有內容可預覽。

寫入真實 Supabase 資料庫（非自動 rollback 的測試資料庫）。
執行方式：於 backend/ 目錄啟用 venv 後執行 `python scripts/seed_demo_data.py`。

帳號密碼皆為 Passw0rd1，僅供本機開發測試使用。
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import ContactPlatform, GroupBuyStatus, PaymentMethod, UserRole
from app.models.group_buy import GroupBuy, GroupBuyProduct, GroupBuyProductCharacter
from app.models.group_leader import GroupLeaderProfile
from app.models.user import AppUser

PASSWORD = "Passw0rd1"

# 清除順序：先子表後父表，避免違反外鍵限制。活動／商品／角色刻意不在此列。
ACCOUNT_SCOPED_TABLES = [
    "notification",
    "cancellation_request",
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


def main() -> None:
    db = SessionLocal()
    try:
        for table in ACCOUNT_SCOPED_TABLES:
            db.execute(text(f'DELETE FROM "{table}"'))

        open_activity_id = db.execute(
            text("SELECT id FROM activity WHERE status = 'open' ORDER BY created_at LIMIT 1")
        ).scalar()
        product_rows = db.execute(
            text(
                "SELECT id FROM product WHERE activity_id = :activity_id ORDER BY created_at"
            ),
            {"activity_id": open_activity_id},
        ).fetchall()
        product_ids = [row[0] for row in product_rows]

        if open_activity_id is None or len(product_ids) < 2:
            raise RuntimeError(
                "找不到既有的開放活動或商品，無法重建示範開團；"
                "請確認 activity/product 資料表仍保留原有目錄資料。"
            )

        member = AppUser(
            email="demo-member@example.com",
            password_hash=hash_password(PASSWORD),
            nickname="示範會員",
            discord_contact="demo_member",
            role=UserRole.MEMBER,
        )
        leader_user = AppUser(
            email="demo-leader@example.com",
            password_hash=hash_password(PASSWORD),
            nickname="示範團主帳號",
            discord_contact="demo_leader",
            role=UserRole.MEMBER,
        )
        admin = AppUser(
            email="demo-admin@example.com",
            password_hash=hash_password(PASSWORD),
            nickname="示範管理員",
            discord_contact="demo_admin",
            role=UserRole.ADMIN,
        )
        db.add_all([member, leader_user, admin])
        db.flush()

        leader_profile = GroupLeaderProfile(
            user_id=leader_user.id,
            display_name="月影團（示範）",
            introduction="主要協助官方周邊開團，示範資料。",
            default_rules="1. 團規僅供示範。\n2. 請勿正式下單。",
            discord_contact="moon_group_demo",
        )
        db.add(leader_profile)
        db.flush()

        group_buy = GroupBuy(
            group_leader_profile_id=leader_profile.id,
            activity_id=open_activity_id,
            payment_method=PaymentMethod.CASH_ON_DELIVERY,
            requires_second_payment=False,
            includes_full_gift=True,
            deadline_at=datetime.now(timezone.utc) + timedelta(days=14),
            rules="1. 團規僅供示範。\n2. 請勿正式下單。\n3. 逾期未付款視為放棄。",
            contact_platform=ContactPlatform.DISCORD,
            contact_value="moon_group_demo",
            status=GroupBuyStatus.OPEN,
        )
        db.add(group_buy)
        db.flush()

        # 商品清單：前兩個目錄商品，外加一個「多角色」商品（若活動中存在），
        # 以便示範多角色選擇器與分角色庫存。(product_id, 單價, 每角色基準數量)
        product_plan = [
            (product_ids[0], "65.00", 20),
            (product_ids[1], "45.00", 15),
        ]
        multi_character_product_id = db.execute(
            text(
                """
                SELECT p.id
                FROM product p
                JOIN product_character pc ON pc.product_id = p.id
                WHERE p.activity_id = :activity_id AND p.is_active = true
                GROUP BY p.id
                HAVING count(pc.character_id) >= 2
                ORDER BY count(pc.character_id) DESC
                LIMIT 1
                """
            ),
            {"activity_id": open_activity_id},
        ).scalar()
        if multi_character_product_id is not None and multi_character_product_id not in product_ids[:2]:
            product_plan.append((multi_character_product_id, "88.00", 8))

        for product_id, unit_price, base_quantity in product_plan:
            group_buy_product = GroupBuyProduct(
                group_buy_id=group_buy.id,
                product_id=product_id,
                unit_price=unit_price,
                max_quantity=base_quantity,
            )
            db.add(group_buy_product)
            db.flush()

            character_ids = (
                db.execute(
                    text("SELECT character_id FROM product_character WHERE product_id = :pid"),
                    {"pid": product_id},
                )
                .scalars()
                .all()
            )
            if character_ids:
                # 每角色給不同數量（base、base+2、base+4…），凸顯分角色庫存；
                # max_quantity 同步為各角色總和。無角色商品則維持單一 max_quantity。
                total = 0
                for index, character_id in enumerate(character_ids):
                    per_character = base_quantity + index * 2
                    db.add(
                        GroupBuyProductCharacter(
                            group_buy_product_id=group_buy_product.id,
                            character_id=character_id,
                            max_quantity=per_character,
                        )
                    )
                    total += per_character
                group_buy_product.max_quantity = total

        db.commit()

        print("帳號資料已重置，示範資料建立完成：")
        print(f"  一般會員帳號：{member.email} / {PASSWORD}")
        print(f"  團主帳號：    {leader_user.email} / {PASSWORD}")
        print(f"  管理員帳號：  {admin.email} / {PASSWORD}")
        print(f"  團主 profile id：{leader_profile.id}")
        print(f"  開團 id：       {group_buy.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
