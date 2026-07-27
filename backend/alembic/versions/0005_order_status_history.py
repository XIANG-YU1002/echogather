"""order status history table

Revision ID: 0005_order_status_history
Revises: 0004_payment_and_group_buy_rules
Create Date: 2026-07-27

依圖 08 右側「狀態紀錄」需求，新增訂單狀態異動歷史表。
訂單每次狀態變更（含建立時的 pending_confirmation）寫入一筆，
供會員訂單詳情頁顯示各狀態的實際發生時間。

既有訂單以其 created_at 補寫一筆建立紀錄；若目前狀態已非 pending_confirmation，
再以 updated_at 補寫一筆目前狀態，避免舊資料的時間軸整片空白。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0005_order_status_history"
down_revision: Union[str, None] = "0004_payment_and_group_buy_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 型別已於 0001 建立，此處只引用不重建
order_status_enum = ENUM(
    "pending_confirmation",
    "pending_payment",
    "paid",
    "shipped",
    "completed",
    "rejected",
    "cancelled",
    name="order_status",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "order_status_history",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", order_status_enum, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_status_history"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["group_order.id"],
            name="fk_order_status_history_order",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "note IS NULL OR length(trim(note)) > 0",
            name="ck_order_status_history_note_not_blank",
        ),
    )
    op.create_index(
        "ix_order_status_history_order_created",
        "order_status_history",
        ["order_id", "created_at"],
    )

    # 既有訂單補寫「訂單建立」紀錄
    op.execute(
        """
        INSERT INTO order_status_history (id, order_id, status, note, created_at)
        SELECT gen_random_uuid(), id, 'pending_confirmation', NULL, created_at
        FROM group_order
        """
    )
    # 目前狀態已推進的訂單，再補一筆目前狀態
    op.execute(
        """
        INSERT INTO order_status_history (id, order_id, status, note, created_at)
        SELECT gen_random_uuid(), id, status, rejection_reason, updated_at
        FROM group_order
        WHERE status <> 'pending_confirmation'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_order_status_history_order_created", table_name="order_status_history")
    op.drop_table("order_status_history")
