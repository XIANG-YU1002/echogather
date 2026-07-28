"""password reset token

Revision ID: 0008_password_reset
Revises: 0007_email_verification
Create Date: 2026-07-28

依使用者需求新增忘記密碼流程（規格外擴充）：會員輸入 Email 後收到一封含
重設連結的信件，點擊後回到前端頁面設定新密碼。

token 以 SHA-256 雜湊儲存（不存明碼），單次使用（consumed_at），並有有效期限。
外鍵到 app_user 並 CASCADE：帳號刪除時未使用的重設 token 一併移除。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_password_reset"
down_revision: Union[str, None] = "0007_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_token",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_token"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_user.id"],
            name="fk_password_reset_token_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_token_hash"),
    )
    op.create_index(
        "ix_password_reset_token_user_created",
        "password_reset_token",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_token_user_created", table_name="password_reset_token")
    op.drop_table("password_reset_token")
