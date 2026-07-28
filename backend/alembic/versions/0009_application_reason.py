"""group leader application reason

Revision ID: 0009_application_reason
Revises: 0008_password_reset
Create Date: 2026-07-28

依使用者需求為團主申請新增「申請原因」欄位（選填），供管理員審核時參考。
既有申請資料的 reason 為 NULL，前端顯示為「未填寫」。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_application_reason"
down_revision: Union[str, None] = "0008_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("group_leader_application", sa.Column("reason", sa.Text(), nullable=True))
    # 有填就不得為空白字串（與專案其他選填文字欄位一致的處理）
    op.create_check_constraint(
        "ck_group_leader_application_reason_not_blank",
        "group_leader_application",
        "reason IS NULL OR length(trim(reason)) > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_group_leader_application_reason_not_blank",
        "group_leader_application",
        type_="check",
    )
    op.drop_column("group_leader_application", "reason")
