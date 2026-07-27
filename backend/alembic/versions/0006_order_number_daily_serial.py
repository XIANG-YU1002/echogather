"""daily serial order numbers

Revision ID: 0006_order_number_serial
Revises: 0005_order_status_history
Create Date: 2026-07-27

依使用者決議，訂單編號由隨機碼改為每日流水號：

    舊：WG-20260727-6A5E55   （WG-西元年月日-6 碼隨機十六進位）
    新：WG260727-000001      （WG + YYMMDD + 連字號 + 6 位流水，每日重新從 1 開始）

以 order_number_counter 表保存每日已發出的最後號碼，取號時用單一原子語句
`INSERT ... ON CONFLICT DO UPDATE ... RETURNING`，避免併發下單搶到相同號碼。

既有訂單的編號不追溯修改（訂單編號是對外識別碼，改動會造成對帳困難）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_order_number_serial"
down_revision: Union[str, None] = "0005_order_status_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_number_counter",
        sa.Column("date_key", sa.String(length=6), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("date_key", name="pk_order_number_counter"),
        sa.CheckConstraint("last_value > 0", name="ck_order_number_counter_last_value_positive"),
    )


def downgrade() -> None:
    op.drop_table("order_number_counter")
