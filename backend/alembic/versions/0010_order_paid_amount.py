"""order paid amount for merged orders

Revision ID: 0010_order_paid_amount
Revises: 0009_application_reason
Create Date: 2026-07-29

依使用者需求新增「訂單合併」功能：同一會員在同一開團的多筆訂單可由團主合併。
合併後若含已付款的訂單，那部分的錢已經收過，不能與待收金額混在一起，
因此新增 paid_amount 記錄「合併時已收的金額」。

語意刻意限定在合併情境：一般訂單的付款狀態由 status 表達（paid 即全額已付），
所以既有資料不回填、預設為 0，前端只在 paid_amount > 0 時顯示已付／待收的拆分。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_order_paid_amount"
down_revision: Union[str, None] = "0009_application_reason"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_order",
        sa.Column(
            "paid_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_group_order_paid_amount_range",
        "group_order",
        "paid_amount >= 0 AND paid_amount <= product_total_amount",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_group_order_paid_amount_range", "group_order", type_="check"
    )
    op.drop_column("group_order", "paid_amount")
