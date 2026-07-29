"""為「訂單合併」功能建立可測資料：同一會員在同一開團的多筆訂單。

依使用者 2026-07-29 需求，為團主 demo-leader1 的**其中一個開團**建立三張訂單，
涵蓋可合併的三種狀態（待確認／待付款／已付款）。

每張訂單都同時包含無角色、單角色、多角色三種商品，並刻意安排成能一次驗證
合併的各種情況：

- 無角色與單角色商品三張訂單都選同一項 → 合併後數量相加成一列
- 多角色商品：待確認與待付款選**不同角色** → 合併後必須維持兩列（不可相加）；
  已付款選的角色與待確認相同 → 那一列會相加
- 已付款那張的金額會記入 paid_amount，與待收金額分開顯示

訂購人固定用 demo-member2，避免與既有示範訂單混在一起難以辨識。

可重複執行：每次執行都會新增一組（訂單編號由計數器保證唯一）。
執行方式：於 backend/ 啟用 venv 後 `python scripts/seed_mergeable_orders.py`
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.enums import OrderStatus
from app.models.order import GroupOrder, OrderItem, OrderStatusHistory

LEADER_EMAIL = "demo-leader1@example.com"
MEMBER_EMAIL = "demo-member2@example.com"

# (狀態, 幾小時前建立, 多角色商品要選第幾個角色, 各商品數量)
# 多角色的角色索引刻意讓待確認與待付款不同，合併後才能看出「不同角色不相加」。
ORDER_PLAN = [
    (OrderStatus.PENDING_CONFIRMATION, 6, 0, 2),
    (OrderStatus.PENDING_PAYMENT, 4, 1, 1),
    (OrderStatus.PAID, 2, 0, 1),
]


def main() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        group_buys = db.execute(
            text(
                """SELECT gb.id, gb.payment_method, gb.payment_method_note,
                          gb.requires_second_payment, gb.includes_full_gift, gb.rules,
                          gb.contact_platform, gb.contact_value,
                          a.name AS activity_name, glp.display_name AS leader_name
                   FROM group_buy gb
                   JOIN activity a ON a.id = gb.activity_id
                   JOIN group_leader_profile glp ON glp.id = gb.group_leader_profile_id
                   JOIN app_user u ON u.id = glp.user_id
                   WHERE u.email = :email
                   ORDER BY gb.created_at"""
            ),
            {"email": LEADER_EMAIL},
        ).all()
        if not group_buys:
            raise SystemExit(f"找不到 {LEADER_EMAIL} 的開團，請先執行 seed_more_activities.py")

        member = db.execute(
            text(
                """SELECT id, nickname, facebook_contact, discord_contact, line_contact
                   FROM app_user WHERE email = :email"""
            ),
            {"email": MEMBER_EMAIL},
        ).one_or_none()
        if member is None:
            raise SystemExit(f"找不到 {MEMBER_EMAIL}，請先執行 seed_demo_data.py")

        created = 0
        # 只處理第一個同時具備三種商品類型的開團（依使用者要求，不必每個團都建）
        for group_buy in group_buys:
            rows = db.execute(
                text(
                    """SELECT gbp.id, gbp.unit_price, p.id AS product_id, p.name,
                              p.primary_image_url,
                              (SELECT count(*) FROM product_character pc
                               WHERE pc.product_id = p.id) AS character_count
                       FROM group_buy_product gbp JOIN product p ON p.id = gbp.product_id
                       WHERE gbp.group_buy_id = :gid
                       ORDER BY gbp.created_at"""
                ),
                {"gid": group_buy.id},
            ).all()

            no_character = next((r for r in rows if r.character_count == 0), None)
            single_character = next((r for r in rows if r.character_count == 1), None)
            multi_character = next((r for r in rows if r.character_count >= 2), None)
            if not (no_character and single_character and multi_character):
                print(f"開團 {group_buy.activity_name!r}：缺少三種商品類型，略過")
                continue

            def characters_of(product_id):
                return db.execute(
                    text(
                        """SELECT c.id, c.name FROM character c
                           JOIN product_character pc ON pc.character_id = c.id
                           WHERE pc.product_id = :pid ORDER BY c.name"""
                    ),
                    {"pid": product_id},
                ).all()

            single_characters = characters_of(single_character.product_id)
            multi_characters = characters_of(multi_character.product_id)

            for status, hours_ago, multi_character_index, quantity in ORDER_PLAN:
                # 一張訂單三個明細：無角色、單角色、多角色
                line_items = [
                    (no_character, None, None),
                    (
                        single_character,
                        single_characters[0].id,
                        single_characters[0].name,
                    ),
                    (
                        multi_character,
                        multi_characters[multi_character_index % len(multi_characters)].id,
                        multi_characters[multi_character_index % len(multi_characters)].name,
                    ),
                ]
                total = sum(item[0].unit_price * quantity for item in line_items)

                serial = db.execute(
                    text(
                        """INSERT INTO order_number_counter (date_key, last_value)
                           VALUES (:date_key, 1)
                           ON CONFLICT (date_key) DO UPDATE
                           SET last_value = order_number_counter.last_value + 1
                           RETURNING last_value"""
                    ),
                    {"date_key": now.strftime("%y%m%d")},
                ).scalar_one()

                created_at = now - timedelta(hours=hours_ago)
                order = GroupOrder(
                    order_number=f"WG{now.strftime('%y%m%d')}-{serial:06d}",
                    user_id=member.id,
                    group_buy_id=group_buy.id,
                    status=status,
                    product_total_amount=total,
                    group_leader_name_snapshot=group_buy.leader_name,
                    activity_name_snapshot=group_buy.activity_name,
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
                )
                db.add(order)
                db.flush()

                for product, character_id, character_name in line_items:
                    db.add(
                        OrderItem(
                            order_id=order.id,
                            group_buy_product_id=product.id,
                            chosen_character_id=character_id,
                            chosen_character_name_snapshot=character_name,
                            product_name_snapshot=product.name,
                            image_url_snapshot=product.primary_image_url,
                            unit_price=product.unit_price,
                            quantity=quantity,
                            subtotal=product.unit_price * quantity,
                        )
                    )
                # 狀態歷史補完整路徑，訂單詳情的狀態紀錄才不會只有一筆
                path = {
                    OrderStatus.PENDING_CONFIRMATION: [OrderStatus.PENDING_CONFIRMATION],
                    OrderStatus.PENDING_PAYMENT: [
                        OrderStatus.PENDING_CONFIRMATION,
                        OrderStatus.PENDING_PAYMENT,
                    ],
                    OrderStatus.PAID: [
                        OrderStatus.PENDING_CONFIRMATION,
                        OrderStatus.PENDING_PAYMENT,
                        OrderStatus.PAID,
                    ],
                }[status]
                for step, history_status in enumerate(path):
                    db.add(
                        OrderStatusHistory(
                            order_id=order.id,
                            status=history_status,
                            created_at=created_at + timedelta(minutes=step * 20),
                        )
                    )
                created += 1

            print(
                f"開團 {group_buy.activity_name!r}：已為 {member.nickname} 建立 "
                f"{len(ORDER_PLAN)} 張訂單（待確認／待付款／已付款），"
                f"每張含無角色「{no_character.name}」、單角色「{single_character.name}」、"
                f"多角色「{multi_character.name}」"
            )
            break

        db.commit()
        print(f"\n完成：共新增 {created} 張訂單")
    finally:
        db.close()


if __name__ == "__main__":
    main()
