"""drop 'other' payment method, relax payment_method_note, one open group buy per leader+activity

Revision ID: 0004_payment_and_group_buy_rules
Revises: 0003_per_character_stock
Create Date: 2026-07-27

依使用者決議：
1. 移除 payment_method 的 'other' 值，只保留 bank_transfer 與 cash_on_delivery。
2. payment_method_note 由「僅 other 必填、其餘必須為 NULL」改為任意付款方式皆可選填；
   有值時不得為空白字串。
3. 同一團主對同一活動同時只能有一個進行中（status='open'）的開團，
   結單後可再開新的一輪 —— 以 partial unique index 實作。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_payment_and_group_buy_rules"
down_revision: Union[str, None] = "0003_per_character_stock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. 先鬆綁引用 'other' 的成對約束 -------------------------------------
    op.drop_constraint(
        "ck_group_buy_payment_method_note_pair", "group_buy", type_="check"
    )
    op.drop_constraint(
        "ck_group_order_payment_method_note_snapshot_pair", "group_order", type_="check"
    )

    # --- 2. 重建 payment_method enum（PostgreSQL 無法直接移除 enum 值）---------
    # 保險起見先把殘留的 'other' 資料轉為 bank_transfer（正常情況下為 0 筆）。
    op.execute(
        "UPDATE group_buy SET payment_method = 'bank_transfer' "
        "WHERE payment_method = 'other'"
    )
    op.execute(
        "UPDATE group_order SET payment_method_snapshot = 'bank_transfer' "
        "WHERE payment_method_snapshot = 'other'"
    )

    op.execute("ALTER TYPE payment_method RENAME TO payment_method_old")
    op.execute("CREATE TYPE payment_method AS ENUM ('bank_transfer', 'cash_on_delivery')")
    op.execute(
        "ALTER TABLE group_buy ALTER COLUMN payment_method "
        "TYPE payment_method USING payment_method::text::payment_method"
    )
    op.execute(
        "ALTER TABLE group_order ALTER COLUMN payment_method_snapshot "
        "TYPE payment_method USING payment_method_snapshot::text::payment_method"
    )
    op.execute("DROP TYPE payment_method_old")

    # --- 3. 新的備註約束：選填，但有值就不得為空白 ----------------------------
    op.create_check_constraint(
        "ck_group_buy_payment_method_note_not_blank",
        "group_buy",
        "payment_method_note IS NULL OR length(trim(payment_method_note)) > 0",
    )
    op.create_check_constraint(
        "ck_group_order_payment_method_note_snapshot_not_blank",
        "group_order",
        "payment_method_note_snapshot IS NULL "
        "OR length(trim(payment_method_note_snapshot)) > 0",
    )

    # --- 4. 一團主一活動只能有一個進行中的開團 --------------------------------
    op.create_index(
        "uq_group_buy_leader_activity_open",
        "group_buy",
        ["group_leader_profile_id", "activity_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_group_buy_leader_activity_open", table_name="group_buy")

    op.drop_constraint(
        "ck_group_order_payment_method_note_snapshot_not_blank", "group_order", type_="check"
    )
    op.drop_constraint(
        "ck_group_buy_payment_method_note_not_blank", "group_buy", type_="check"
    )

    # 還原 enum（加回 'other'）
    op.execute("ALTER TYPE payment_method RENAME TO payment_method_new")
    op.execute(
        "CREATE TYPE payment_method AS ENUM ('bank_transfer', 'cash_on_delivery', 'other')"
    )
    op.execute(
        "ALTER TABLE group_buy ALTER COLUMN payment_method "
        "TYPE payment_method USING payment_method::text::payment_method"
    )
    op.execute(
        "ALTER TABLE group_order ALTER COLUMN payment_method_snapshot "
        "TYPE payment_method USING payment_method_snapshot::text::payment_method"
    )
    op.execute("DROP TYPE payment_method_new")

    # 還原成對約束前，先把不符合舊規則的備註清成 NULL
    op.execute(
        "UPDATE group_buy SET payment_method_note = NULL WHERE payment_method <> 'other'"
    )
    op.execute(
        "UPDATE group_order SET payment_method_note_snapshot = NULL "
        "WHERE payment_method_snapshot <> 'other'"
    )
    op.create_check_constraint(
        "ck_group_buy_payment_method_note_pair",
        "group_buy",
        """
        (
            payment_method = 'other'
            AND payment_method_note IS NOT NULL
            AND length(trim(payment_method_note)) > 0
        )
        OR
        (
            payment_method <> 'other'
            AND payment_method_note IS NULL
        )
        """,
    )
    op.create_check_constraint(
        "ck_group_order_payment_method_note_snapshot_pair",
        "group_order",
        """
        (
            payment_method_snapshot = 'other'
            AND payment_method_note_snapshot IS NOT NULL
            AND length(trim(payment_method_note_snapshot)) > 0
        )
        OR
        (
            payment_method_snapshot <> 'other'
            AND payment_method_note_snapshot IS NULL
        )
        """,
    )
