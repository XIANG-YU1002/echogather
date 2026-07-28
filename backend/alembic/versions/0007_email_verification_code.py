"""email verification code for registration

Revision ID: 0007_email_verification
Revises: 0006_order_number_serial
Create Date: 2026-07-28

依使用者需求新增註冊 Email 驗證（規格外擴充）：註冊前需先取得寄到信箱的
6 位數驗證碼，註冊時一併送出驗證。

驗證碼以 SHA-256 雜湊儲存，不存明碼；每筆只能使用一次（consumed_at），
並記錄錯誤嘗試次數（attempt_count）以限制暴力嘗試。
本表不外鍵到 app_user——驗證發生在帳號建立之前。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_email_verification"
down_revision: Union[str, None] = "0006_order_number_serial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_verification_code",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_verification_code"),
        sa.CheckConstraint(
            "length(trim(email)) > 0", name="ck_email_verification_code_email_not_blank"
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_email_verification_code_attempt_non_negative"
        ),
    )
    op.create_index(
        "ix_email_verification_code_email_created",
        "email_verification_code",
        ["email", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_code_email_created", table_name="email_verification_code"
    )
    op.drop_table("email_verification_code")
