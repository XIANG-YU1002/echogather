"""merged order status, merge records and unmerge requests

Revision ID: 0011_order_merge_and_unmerge
Revises: 0010_order_paid_amount
Create Date: 2026-07-30

依使用者 2026-07-30 裁決調整訂單合併的行為：

1. 被合併的來源訂單原本標記為 cancelled，會被算進「已取消」的頁籤數字、語意也不對。
   改為新增專屬狀態 merged：前台會員端與團主端都不顯示這種訂單，資料完整保留。
   merged 與 cancelled／rejected 同樣不佔用庫存（見 order_repository 的
   NON_OCCUPYING_STATUSES）——合併時明細是複製到目標訂單，若來源仍佔用會重複計算。

2. 新增 order_merge：記錄每次合併中來源與目標「合併前」的狀態與金額，
   讓拆單能還原成合併前各自的狀態。

3. 新增 order_unmerge_request：會員提出的拆單申請，團主可核准或附原因拒絕，
   流程與 cancellation_request 相同，因此沿用 cancellation_status 型別。

（通知上標示合併批次的欄位見 0012。）
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_order_merge_and_unmerge"
down_revision: Union[str, None] = "0010_order_paid_amount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 既有型別，僅引用不重建
order_status = postgresql.ENUM(name="order_status", create_type=False)
cancellation_status = postgresql.ENUM(name="cancellation_status", create_type=False)


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE 需在 autocommit 下執行（同 0002）
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'merged'")

    op.create_table(
        "order_merge",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_status_before", order_status, nullable=False),
        sa.Column("source_paid_amount_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_status_before", order_status, nullable=False),
        sa.Column("target_product_total_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_paid_amount_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("unmerged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["target_order_id"], ["group_order.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_order_id"], ["group_order.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_order_id", "batch_id", name="uq_order_merge_source_batch"),
        sa.CheckConstraint(
            "target_order_id <> source_order_id", name="ck_order_merge_target_not_source"
        ),
        sa.CheckConstraint(
            "source_paid_amount_before >= 0 AND target_paid_amount_before >= 0 "
            "AND target_product_total_before >= 0",
            name="ck_order_merge_amounts_non_negative",
        ),
    )
    op.create_index(
        "ix_order_merge_target_unmerged", "order_merge", ["target_order_id", "unmerged_at"]
    )
    op.create_index("ix_order_merge_batch", "order_merge", ["batch_id"])

    op.create_table(
        "order_unmerge_request",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", cancellation_status, nullable=False, server_default="pending"),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["order_id"], ["group_order.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "reason IS NULL OR length(trim(reason)) > 0",
            name="ck_order_unmerge_request_reason_not_blank",
        ),
        sa.CheckConstraint(
            "response_note IS NULL OR length(trim(response_note)) > 0",
            name="ck_order_unmerge_request_response_note_not_blank",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND response_note IS NULL AND processed_at IS NULL) "
            "OR (status IN ('approved', 'rejected') AND processed_at IS NOT NULL)",
            name="ck_order_unmerge_request_status_processed_pair",
        ),
    )
    op.create_index(
        "ix_order_unmerge_request_order_status", "order_unmerge_request", ["order_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_order_unmerge_request_order_status", table_name="order_unmerge_request")
    op.drop_table("order_unmerge_request")
    op.drop_index("ix_order_merge_batch", table_name="order_merge")
    op.drop_index("ix_order_merge_target_unmerged", table_name="order_merge")
    op.drop_table("order_merge")
    # 先把 merged 訂單還原成 cancelled（0010 之前的行為），否則移除 enum 值會失敗
    op.execute("UPDATE group_order SET status = 'cancelled' WHERE status = 'merged'")
    # PostgreSQL 不支援從 enum 移除值（同 0002），保留 'merged' 不影響資料
