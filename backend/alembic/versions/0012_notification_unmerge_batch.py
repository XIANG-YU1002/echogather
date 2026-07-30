"""notification unmerge batch reference

Revision ID: 0012_notification_unmerge_batch
Revises: 0011_order_merge_and_unmerge
Create Date: 2026-07-30

圖 10 通知中心要在「訂單已合併」那一則通知底下顯示「取消合併訂單」按鈕
（使用者 2026-07-30 需求）。通知本身必須知道自己對應哪一次合併，否則只能靠
標題文字去猜，或讓同一張訂單的其他通知（已確認、已出貨…）也長出按鈕。

刻意不設外鍵到 order_merge：批次被拆掉後 order_merge 的紀錄仍保留，
而通知只需要記住批次編號用來比對，不需要參照完整性連動刪除。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_notification_unmerge_batch"
down_revision: Union[str, None] = "0011_order_merge_and_unmerge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification",
        sa.Column("unmerge_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # 批次只在訂單通知上有意義（拆單按鈕要導向該訂單）
    op.create_check_constraint(
        "ck_notification_unmerge_batch_requires_order",
        "notification",
        "unmerge_batch_id IS NULL OR order_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_notification_unmerge_batch_requires_order", "notification", type_="check"
    )
    op.drop_column("notification", "unmerge_batch_id")
