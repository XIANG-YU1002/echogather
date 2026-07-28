import uuid

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class EmailVerificationCode(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """註冊用的 Email 驗證碼。

    驗證碼以 SHA-256 雜湊儲存，資料庫外洩時不會直接暴露可用的驗證碼。
    每筆只能使用一次（`consumed_at`），並限制錯誤嘗試次數（`attempt_count`）。
    這裡不外鍵到 app_user——驗證發生在帳號建立之前。
    """

    __tablename__ = "email_verification_code"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("length(trim(email)) > 0", name="ck_email_verification_code_email_not_blank"),
        CheckConstraint("attempt_count >= 0", name="ck_email_verification_code_attempt_non_negative"),
        Index("ix_email_verification_code_email_created", "email", "created_at"),
    )
